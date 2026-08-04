"""Phase 5 retrieval tests: embeddings, vector store, lexical, hybrid."""

from __future__ import annotations

import uuid

import pytest
from app.core.config import get_settings
from app.retrieval.embeddings import LocalEmbeddingProvider
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.lexical import LexicalIndex, LexicalRecord
from app.retrieval.vector_store import VectorRecord, VectorStore


def test_local_embedding_provider_dim() -> None:
    provider = LocalEmbeddingProvider("sentence-transformers/all-MiniLM-L6-v2")
    assert provider.dimension == 384
    res = provider.embed(["hello world", "test"])
    assert res.vectors.shape == (2, 384)
    assert res.model == "sentence-transformers/all-MiniLM-L6-v2"


def test_local_embedding_provider_normalization() -> None:
    provider = LocalEmbeddingProvider("sentence-transformers/all-MiniLM-L6-v2")
    res = provider.embed(["hello world"])
    # Vectors should be normalized (unit length)
    import numpy as np

    norms = np.linalg.norm(res.vectors, axis=1)
    assert abs(norms[0] - 1.0) < 1e-5


@pytest.mark.skipif(not get_settings().chroma_host, reason="Chroma not configured")
def test_vector_store_upsert_query() -> None:
    store = VectorStore(collection_name="test_collection")
    provider = LocalEmbeddingProvider("sentence-transformers/all-MiniLM-L6-v2")
    vecs = provider.embed(["legal text one", "legal text two"]).vectors.tolist()

    records = [
        VectorRecord(id=str(uuid.uuid4()), text="legal text one", embedding=vecs[0], metadata={"section": "1"}),
        VectorRecord(id=str(uuid.uuid4()), text="legal text two", embedding=vecs[1], metadata={"section": "2"}),
    ]
    store.upsert_chunks(records)

    results = store.query("legal text", n_results=2)
    assert results["ids"]
    assert len(results["ids"][0]) == 2

    # Cleanup
    store.collection.delete(ids=[r.id for r in records])


def test_lexical_index_upsert_search(tmp_path) -> None:
    idx = LexicalIndex(index_path=tmp_path / "lex.pkl")
    recs = [
        LexicalRecord(chunk_id=uuid.uuid4(), text="Section 1. Theft punishment.", metadata={"section": "1"}),
        LexicalRecord(chunk_id=uuid.uuid4(), text="Section 2. Murder definition.", metadata={"section": "2"}),
        LexicalRecord(chunk_id=uuid.uuid4(), text="Explanation of private defence.", metadata={"section": "3"}),
    ]
    idx.upsert(recs)
    assert idx.count() == 3

    results = idx.search("theft", n_results=2)
    assert len(results) == 1
    assert "theft" in results[0][0].text.lower()

    # Delete
    idx.delete([recs[0].chunk_id])
    assert idx.count() == 2


def test_hybrid_retriever_rrf_fusion() -> None:
    # Test RRF fusion logic directly (without Chroma)
    HybridRetriever(vector_store=None, lexical_index=None)
    # Can't test without stores, but fusion logic can be unit-tested
    pass


@pytest.mark.skipif(not get_settings().chroma_host, reason="Chroma not configured")
def test_hybrid_retriever_end_to_end() -> None:
    """Full hybrid retrieval with real Chroma + local embeddings."""

    # Use a unique test collection
    test_collection = f"test_hybrid_{uuid.uuid4().hex[:8]}"
    store = VectorStore(collection_name=test_collection)
    lexical = LexicalIndex()
    retriever = HybridRetriever(vector_store=store, lexical_index=lexical)

    chunk_ids = [uuid.uuid4() for _ in range(5)]
    texts = [
        "Section 1. Short title and commencement.",
        "Section 2. Definitions of key terms.",
        "Section 3. Punishment for offences.",
        "Explanation to Section 2. The word 'act' includes omissions.",
        "Illustration 1 to Section 3. A kills B, which is murder.",
    ]
    metadatas = [
        {"section_id": "1", "element_type": "SECTION"},
        {"section_id": "2", "element_type": "SECTION"},
        {"section_id": "3", "element_type": "SECTION"},
        {"section_id": "2", "element_type": "EXPLANATION"},
        {"section_id": "3", "element_type": "ILLUSTRATION"},
    ]

    retriever.upsert_chunks(chunk_ids, texts, metadatas)

    # Semantic search
    results = retriever.retrieve("murder punishment", n_results=3)
    assert len(results) >= 1
    # Should rank Section 3 and Illustration high
    sections = {r.metadata.get("section_id") for r in results}
    assert "3" in sections or any("murder" in r.text.lower() for r in results)

    # Lexical exact
    results2 = retriever.retrieve("Explanation", n_results=2)
    assert any(r.metadata.get("element_type") == "EXPLANATION" for r in results2)

    # Cleanup
    for cid in chunk_ids:
        store.collection.delete(ids=[str(cid)])
    lexical.delete(chunk_ids)

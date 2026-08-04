"""ChromaDB vector store wrapper for legal chunks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List, Optional, Sequence

import chromadb
from app.core.config import get_settings
from app.retrieval.embeddings import EmbeddingProvider, get_embedding_provider
from chromadb.api.models.Collection import Collection

COLLECTION_NAME = "bns_chunks"


@dataclass
class VectorRecord:
    id: str
    text: str
    embedding: List[float]
    metadata: dict


class VectorStore:
    """Thin wrapper around ChromaDB for legal chunk vectors."""

    def __init__(
        self,
        provider: Optional[EmbeddingProvider] = None,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        settings = get_settings()
        self._client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        self._collection: Collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )
        self._provider = provider or get_embedding_provider()

    @property
    def provider(self) -> EmbeddingProvider:
        return self._provider

    @property
    def collection(self) -> Collection:
        return self._collection

    def upsert_chunks(self, records: Sequence[VectorRecord]) -> None:
        """Insert or update chunk vectors with metadata."""
        if not records:
            return

        # Chroma requires metadata values to be str, int, float, or bool (no None)
        def clean_meta(m: dict) -> dict:
            return {k: v for k, v in m.items() if v is not None}

        self._collection.upsert(
            ids=[r.id for r in records],
            embeddings=[r.embedding for r in records],  # type: ignore[arg-type]
            documents=[r.text for r in records],
            metadatas=[clean_meta(r.metadata) for r in records],
        )

    def query(
        self,
        query_text: str,
        n_results: int = 20,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
    ) -> dict:
        """Semantic search by query text."""
        q_vec = self._provider.embed([query_text]).vectors[0].tolist()
        return self._collection.query(
            query_embeddings=[q_vec],  # type: ignore[arg-type]
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )  # type: ignore[return-value]

    def query_by_vector(
        self,
        vector: List[float],
        n_results: int = 20,
        where: Optional[dict] = None,
    ) -> dict:
        return self._collection.query(
            query_embeddings=[vector],  # type: ignore[arg-type]
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )  # type: ignore[return-value]

    def delete_by_source_version(self, source_version_id: uuid.UUID) -> None:
        """Remove all vectors for a source version (used when deactivating)."""
        self._collection.delete(where={"source_version_id": str(source_version_id)})

    def delete_by_document(self, document_id: uuid.UUID) -> None:
        self._collection.delete(where={"document_id": str(document_id)})

    def count(self, where: Optional[dict] = None) -> int:
        # Chroma's count() doesn't accept where in older versions
        return self._collection.count()  # type: ignore[call-arg]

    def get_chunk(self, chunk_id: uuid.UUID) -> Optional[dict]:
        res = self._collection.get(ids=[str(chunk_id)], include=["documents", "metadatas"])
        ids = res.get("ids")
        if not ids:
            return None
        # res["documents"] and res["metadatas"] are guaranteed non-None when ids exists
        docs = res["documents"]
        metas = res["metadatas"]
        if not docs or not metas:
            return None
        return {
            "id": ids[0],
            "text": docs[0],
            "metadata": metas[0],
        }

    def get_chunks_by_sections(self, section_numbers: Sequence[int], limit_per_section: int = 1) -> list[dict]:
        """Return chunk records for the given section numbers (for graph expansion).

        Chroma metadata equality is scalar; we fetch per section and cap the
        number of returned chunks so the graph boost does not flood results.
        """
        out: list[dict] = []
        for num in section_numbers:
            try:
                res = self._collection.get(
                    where={"section_id": str(num)},
                    include=["documents", "metadatas"],
                    limit=limit_per_section,
                )
            except Exception:  # noqa: BLE001
                continue
            ids = res.get("ids") or []
            docs = res.get("documents") or []
            metas = res.get("metadatas") or []
            for i, cid in enumerate(ids):
                if i >= len(docs) or i >= len(metas):
                    continue
                out.append({"id": cid, "text": docs[i], "metadata": metas[i]})
        return out

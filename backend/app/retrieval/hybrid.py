"""Hybrid retriever: combines vector (semantic) + lexical (BM25) search via RRF."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.core.config import get_settings
from app.retrieval.embeddings import get_embedding_provider
from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.lexical import LexicalIndex, LexicalRecord
from app.retrieval.vector_store import VectorRecord, VectorStore


@dataclass
class RetrievalResult:
    chunk_id: uuid.UUID
    text: str
    metadata: dict
    score: float  # fused score
    vector_score: Optional[float] = None
    lexical_score: Optional[float] = None


class HybridRetriever:
    """RRF-fused hybrid retrieval over Chroma vectors + BM25 lexical index."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        lexical_index: Optional[LexicalIndex] = None,
        graph_retriever: Optional[GraphRetriever] = None,
        vector_weight: float = 0.6,
        lexical_weight: float = 0.4,
        rrf_k: int = 60,
    ) -> None:
        settings = get_settings()
        self._vector_store = vector_store or VectorStore()
        self._lexical = lexical_index or LexicalIndex()
        self._graph = graph_retriever or GraphRetriever()
        self._vector_weight = vector_weight
        self._lexical_weight = lexical_weight
        self._rrf_k = rrf_k
        self._enabled_vector = settings.rag_semantic_enabled
        self._enabled_lexical = settings.rag_lexical_enabled

    def upsert_chunks(
        self,
        chunk_ids: Sequence[uuid.UUID],
        texts: Sequence[str],
        metadatas: Sequence[dict],
    ) -> None:
        """Embed texts and upsert to both vector and lexical stores."""
        if not chunk_ids:
            return
        # Generate embeddings
        provider = get_embedding_provider()
        embeddings = provider.embed(list(texts)).vectors.tolist()

        # Vector upsert
        if self._enabled_vector:
            vec_records = [
                VectorRecord(
                    id=str(cid),
                    text=t,
                    embedding=e,
                    metadata=m,
                )
                for cid, t, e, m in zip(chunk_ids, texts, embeddings, metadatas)
            ]
            self._vector_store.upsert_chunks(vec_records)

        # Lexical upsert
        if self._enabled_lexical:
            lex_records = [
                LexicalRecord(chunk_id=cid, text=t, metadata=m) for cid, t, m in zip(chunk_ids, texts, metadatas)
            ]
            self._lexical.upsert(lex_records)

    def delete_chunks(self, chunk_ids: Sequence[uuid.UUID]) -> None:
        if self._enabled_vector:
            for cid in chunk_ids:
                self._vector_store.collection.delete(ids=[str(cid)])
        if self._enabled_lexical:
            self._lexical.delete(chunk_ids)

    def retrieve(
        self,
        query: str,
        n_results: int = 20,
        where: Optional[dict] = None,
    ) -> List[RetrievalResult]:
        """Hybrid search: RRF fusion of vector + lexical results."""
        vec_results: List[RetrievalResult] = []
        lex_results: List[RetrievalResult] = []

        # Vector search
        if self._enabled_vector:
            raw = self._vector_store.query(query, n_results=n_results * 2, where=where)
            if raw["ids"]:
                for i, cid in enumerate(raw["ids"][0]):
                    vec_results.append(
                        RetrievalResult(
                            chunk_id=uuid.UUID(cid),
                            text=raw["documents"][0][i],
                            metadata=raw["metadatas"][0][i],
                            score=0.0,
                            vector_score=1.0 - raw["distances"][0][i],  # cosine similarity
                        )
                    )

        # Lexical search
        if self._enabled_lexical:
            for rec, score in self._lexical.search(query, n_results=n_results * 2):
                # Filter by where clause if provided
                if where and not all(rec.metadata.get(k) == v for k, v in where.items()):
                    continue
                lex_results.append(
                    RetrievalResult(
                        chunk_id=rec.chunk_id,
                        text=rec.text,
                        metadata=rec.metadata,
                        score=0.0,
                        lexical_score=score,
                    )
                )

        # Graph expansion: surface closely-related sections via REF edge hops.
        graph_results = self._graph_expand(vec_results, lex_results, n_results)

        # RRF fusion
        return self._rrf_fuse([*vec_results, *graph_results], lex_results, n_results)

    def _rrf_fuse(
        self,
        vec: List[RetrievalResult],
        lex: List[RetrievalResult],
        n: int,
    ) -> List[RetrievalResult]:
        """Reciprocal Rank Fusion with weights."""
        # Rank by position in each list
        vec_rank = {r.chunk_id: i + 1 for i, r in enumerate(vec)}
        lex_rank = {r.chunk_id: i + 1 for i, r in enumerate(lex)}

        all_ids = set(vec_rank) | set(lex_rank)
        fused: List[RetrievalResult] = []

        # Normalization factor: the maximum possible RRF score (rank 1 in both
        # lists) = (vector_weight + lexical_weight) / (k + 1) = 1 / (k + 1).
        # Dividing by it maps the fused score to ~[0, 1] so a stable minimum
        # score threshold can be applied downstream.
        norm = self._rrf_k + 1

        for cid in all_ids:
            vr = vec_rank.get(cid)
            lr = lex_rank.get(cid)
            raw = 0.0
            if vr is not None:
                raw += self._vector_weight * (1.0 / (self._rrf_k + vr))
            if lr is not None:
                raw += self._lexical_weight * (1.0 / (self._rrf_k + lr))
            score = raw * norm

            vec_src = next((r for r in vec if r.chunk_id == cid), None)
            lex_src = next((r for r in lex if r.chunk_id == cid), None)
            src = vec_src or lex_src
            if src:
                fused.append(
                    RetrievalResult(
                        chunk_id=cid,
                        text=src.text,
                        metadata=src.metadata,
                        score=score,
                        vector_score=vec_src.vector_score if vec_src else None,
                        lexical_score=lex_src.lexical_score if lex_src else None,
                    )
                )

        fused.sort(key=lambda r: r.score, reverse=True)
        return fused[:n]

    def retrieve_by_section(self, section_num: str, n_results: int = 10) -> List[RetrievalResult]:
        """Exact section filter (uses vector store metadata)."""
        if not self._enabled_vector:
            return []
        raw = self._vector_store.query("", n_results=n_results, where={"section_id": section_num})
        results: List[RetrievalResult] = []
        if raw["ids"]:
            for i, cid in enumerate(raw["ids"][0]):
                results.append(
                    RetrievalResult(
                        chunk_id=uuid.UUID(cid),
                        text=raw["documents"][0][i],
                        metadata=raw["metadatas"][0][i],
                        score=1.0,
                    )
                )
        return results

    def _graph_expand(self, vec: List[RetrievalResult], lex: List[RetrievalResult], n: int) -> List[RetrievalResult]:
        """Expand the top matched sections via Neo4j reference edges.

        Returns the related sections' chunks as vector-backed results with a
        modest graph boost so they rank below direct semantic/lexical hits but
        above an unanswered query. Mirroring the reference-hit mapping in
        ``VectorStore.get_chunks_by_sections`` keeps this dependency-light.
        """
        if not self._graph.enabled:
            return []
        section_numbers = {int(r.metadata.get("section_id", 0)) for r in [*vec, *lex] if r.metadata.get("section_id")}
        section_numbers = {s for s in section_numbers if s >= 1}
        if not section_numbers:
            return []

        expanded = self._graph.expand(sorted(section_numbers), n_results=n)
        if not expanded:
            return []

        out: List[RetrievalResult] = []
        for item in expanded:
            number = item.get("number")
            if not number:
                continue
            chunks = self._vector_store.get_chunks_by_sections([int(number)], limit_per_section=1)
            for chunk in chunks:
                out.append(
                    RetrievalResult(
                        chunk_id=uuid.UUID(chunk["id"]),
                        text=chunk["text"],
                        metadata=chunk["metadata"],
                        score=0.0,
                        vector_score=None,
                        lexical_score=None,
                    )
                )
        return out

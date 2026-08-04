"""Retrieval service: query processing, hybrid search, reranking, score gating.

Coordinates the Phase 5 hybrid retriever into a higher-level service that:
- validates queries and rejects empty / prompt-injection patterns
- runs vector + lexical hybrid search
- reranks candidates (score-based, deterministic)
- applies a minimum-score gate that fails closed (no unverifiable evidence)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.core.config import get_settings
from app.core.exceptions import (
    InsufficientBNSEvidenceError,
    InvalidRequestError,
    RetrievalFailedError,
)
from app.retrieval.hybrid import HybridRetriever, RetrievalResult
from app.retrieval.lexical import _STOPWORDS

# Reject attempts to escape the retrieval boundary / inject instructions.
_INJECTION_PATTERNS = (
    re.compile(r"ignore (all )?(previous|above|prior) (instructions|prompts)", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"\bdo not follow\b", re.I),
    re.compile(r"\bdisregard\b", re.I),
)


@dataclass
class RetrievalOutcome:
    results: list[RetrievalResult]
    query: str
    top_k: int
    gated: bool  # True when results survived the minimum-score gate
    note: str | None = None


class RetrievalService:
    """High-level retrieval API over the hybrid index."""

    def __init__(self, retriever: Optional[HybridRetriever] = None) -> None:
        settings = get_settings()
        self._retriever = retriever or HybridRetriever()
        self._top_k = settings.rag_top_k
        self._rerank_top_k = settings.rag_rerank_top_k
        self._min_score = settings.rag_min_score

    # -- Query validation ---------------------------------------------------

    def validate_query(self, query: str) -> str:
        q = (query or "").strip()
        if len(q) < 3:
            raise InvalidRequestError("Query is too short.")
        if len(q) > 2000:
            raise InvalidRequestError("Query is too long.")
        if any(p.search(q) for p in _INJECTION_PATTERNS):
            raise InvalidRequestError("Query rejected by security validation.")
        return q

    # -- Retrieval ----------------------------------------------------------

    def retrieve(
        self,
        query: str,
        *,
        top_k: Optional[int] = None,
        where: Optional[dict] = None,
        fail_closed: bool = True,
    ) -> RetrievalOutcome:
        """Run validated hybrid retrieval with reranking and score gate."""
        q = self.validate_query(query)
        k = top_k or self._top_k

        try:
            candidates = self._retriever.retrieve(q, n_results=k * 2, where=where)
        except Exception as exc:  # noqa: BLE001
            raise RetrievalFailedError() from exc

        if not candidates:
            if fail_closed:
                raise InsufficientBNSEvidenceError()
            return RetrievalOutcome(results=[], query=q, top_k=k, gated=False)

        ranked = self._rerank(candidates, q)

        # Deduplicate by (section_id, element_type) keeping the highest score so
        # a section and its explanation are both represented but not repeated.
        seen: set[tuple[str, str]] = set()
        deduped: list[RetrievalResult] = []
        for r in ranked:
            key = (r.metadata.get("section_id", ""), r.metadata.get("element_type", ""))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(r)

        # Minimum-score gate (fail closed by default). The gate is applied to
        # the *semantic evidence* (cosine similarity), not the RRF-fused rank
        # score, because rank-based fusion is always high (~1.0) even for
        # unrelated queries. Lexical-only hits carry no cosine evidence; they
        # are gated by content-term overlap instead, so single coincidental
        # word matches (e.g. "best" appearing in a section) do not pass.
        q_terms = _tokenize(q)

        def _evidence(r: RetrievalResult) -> float:
            if r.vector_score is not None:
                return r.vector_score
            if r.lexical_score is not None and r.lexical_score > 0:
                text_terms = _tokenize(r.text)
                if q_terms and text_terms:
                    return len(q_terms & text_terms) / max(len(q_terms), 1)
                return 0.0
            return r.score

        passed = [r for r in deduped if _evidence(r) >= self._min_score] if fail_closed else deduped
        if fail_closed and not passed:
            top_evidence = max((_evidence(r) for r in deduped), default=0.0)
            raise InsufficientBNSEvidenceError(
                details={
                    "min_score": self._min_score,
                    "top_score": round(top_evidence, 4),
                }
            )

        return RetrievalOutcome(
            results=passed[: self._rerank_top_k],
            query=q,
            top_k=k,
            gated=fail_closed,
        )

    def retrieve_section(self, section_num: str) -> list[RetrievalResult]:
        """Exact section lookup by number (deterministic, no semantic gate)."""
        s = (section_num or "").strip()
        if not s.isdigit() or not (1 <= int(s) <= 358):
            raise InvalidRequestError("Section number must be between 1 and 358.")
        return self._retriever.retrieve_by_section(s, n_results=10)

    # -- Reranking ----------------------------------------------------------

    def _rerank(self, candidates: list[RetrievalResult], query: str) -> list[RetrievalResult]:
        """Score-based rerank: blend vector similarity + lexical + term overlap.

        Deterministic and dependency-free (no cross-encoder required).
        """
        q_terms = set(_tokenize(query))
        for r in candidates:
            text_terms = _tokenize(r.text)
            overlap = 0.0
            if q_terms and text_terms:
                overlap = len(q_terms & text_terms) / max(len(q_terms), 1)
            r.score += 0.15 * overlap  # boost exact term overlap
        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS}

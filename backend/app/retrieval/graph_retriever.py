"""Graph retriever: expands a query's matched sections via Neo4j relations.

Phase 7. After lexical/vector retrieval identifies a set of relevant sections,
the graph retriever follows ``REFERENCES`` edges so downstream fusion can
surface closely-related sections that a pure keyword or semantic search might
miss (e.g. an *exception* defined in another section).
"""

from __future__ import annotations

from typing import Optional, Sequence

from app.core.config import get_settings
from app.retrieval.graph_service import GraphService


class GraphRetriever:
    """Returns related-section hits from the knowledge graph."""

    def __init__(self, service: Optional[GraphService] = None) -> None:
        settings = get_settings()
        self._service = service or GraphService()
        self._enabled = settings.rag_graph_enabled
        self._max_hops = 1

    @property
    def enabled(self) -> bool:
        return self._enabled

    def expand(self, section_numbers: Sequence[int], n_results: int = 20) -> list[dict]:
        """Return related sections reachable via references; empty on failure."""
        if not self._enabled or not section_numbers:
            return []
        try:
            return self._service.neighbors(section_numbers, max_hops=self._max_hops)[slice(0, n_results)]
        except Exception:  # noqa: BLE001  (graph unavailable)
            return []

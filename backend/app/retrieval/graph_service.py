"""Graph persistence service: writes section nodes + reference edges to Neo4j.

Phase 7. Converts chunk metadata and extracted cross-references into a Cypher
graph so retrieval can expand a query across related sections. Idempotent: each
section node carries the owning source_version_id and its edges are refreshed on
every build so stale references from old versions are removed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from app.retrieval.graph_driver import Neo4jDriver, get_graph_driver
from app.retrieval.graph_extractor import extract_section_references


@dataclass
class SectionNode:
    """A BNS section to add to (or update in) the graph."""

    number: int
    title: str | None
    chapter_id: str | None
    chapter_title: str | None
    source_version_id: str
    section_chunk_id: str | None = None  # Chroma chunk id for the SECTION parent


class GraphService:
    """Writes BNS sections and cross-reference edges into Neo4j."""

    def __init__(self, driver: Optional[Neo4jDriver] = None) -> None:
        self._driver = driver or get_graph_driver()

    def index_section(
        self,
        section: SectionNode,
        full_text: str,
        *,
        replace_source_version: Optional[str] = None,
    ) -> int:
        """Upsert a Section node plus REFERENCES edges for the referring text.

        Returns the number of cross-references created.
        """
        refs = extract_section_references(full_text)

        self._driver.execute(
            (
                f"MERGE (s:{Neo4jDriver.LABEL_SECTION} {{number: $number}}) "
                f"ON CREATE SET s.chapter_id = $chapter_id, "
                f"s.chapter_title = $chapter_title, s.title = $title, "
                f"s.source_version_id = $source_version_id, s.chunk_id = $chunk_id "
                f"ON MATCH SET s.title = $title, s.chunk_id = $chunk_id "
            ),
            {
                "number": section.number,
                "chapter_id": section.chapter_id,
                "chapter_title": section.chapter_title,
                "title": section.title,
                "source_version_id": section.source_version_id,
                "chunk_id": section.section_chunk_id,
            },
        )

        # Create edges; UNWIND skips nothing but the self-reference is excluded.
        targets = sorted(t for t in refs["explicit"] if t != section.number)
        created = 0
        if targets:
            self._driver.execute(
                (
                    f"UNWIND $targets AS tgt "
                    f"MATCH (a:{Neo4jDriver.LABEL_SECTION} {{number: $src}}) "
                    f"MATCH (b:{Neo4jDriver.LABEL_SECTION} {{number: tgt}}) "
                    f"CREATE (a)-[:{Neo4jDriver.REL_REFERENCES}]->(b)"
                ),
                {"src": section.number, "targets": targets},
            )
            created = len(targets)
        return created

    def replace_source(self, source_version_id: str) -> None:
        """Remove all section nodes for a source version (idempotent)."""
        self._driver.execute(
            f"MATCH (s:{Neo4jDriver.LABEL_SECTION} {{source_version_id: $sid}}) DETACH DELETE s",
            {"sid": source_version_id},
        )

    def neighbors(self, numbers: Sequence[int], max_hops: int = 1) -> list[dict]:
        """Return sections reachable from the given numbers within max_hops."""
        if not numbers:
            return []
        records = self._driver.execute(
            (
                f"MATCH (a:{Neo4jDriver.LABEL_SECTION}) "
                f"WHERE a.number IN $numbers "
                f"MATCH (a)-[:{Neo4jDriver.REL_REFERENCES}*1..{int(max_hops)}]-(b:{Neo4jDriver.LABEL_SECTION}) "
                f"WHERE a.number <> b.number "
                f"RETURN DISTINCT b.number AS number, b.title AS title "
                f"ORDER BY number"
            ),
            {"numbers": [int(n) for n in numbers]},
        )
        out: list[dict] = []
        for record in records:
            out.append(
                {
                    "number": record["number"],
                    "title": record["title"],
                    "hops": max_hops,
                }
            )
        return out

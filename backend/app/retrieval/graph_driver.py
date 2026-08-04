"""Neo4j driver wrapper with schema/constraint initialization.

Wraps the official driver in a small abstraction so the rest of the graph layer
does not depend on a specific connection object and can be tested with a fake.
The schema (labels + uniqueness constraints) is created idempotently on first
use. This module is lazy: importing it does not open a connection.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, Optional

from app.core.config import get_settings


class Neo4jDriver:
    """Lazy Neo4j driver that creates the graph schema on first connect."""

    LABEL_SECTION = "Section"
    LABEL_CHAPTER = "Chapter"

    REL_REFERENCES = "REFERENCES"
    REL_BELONGS_TO = "BELONGS_TO"

    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None) -> None:
        from neo4j import GraphDatabase

        settings = get_settings()
        self._uri = uri or settings.neo4j_uri
        self._user = user or settings.neo4j_user
        self._password = password or settings.neo4j_password
        self._cls = GraphDatabase
        self._driver: Any | None = None

    def _get_driver(self) -> Any:
        if self._driver is None:
            self._driver = self._cls.driver(self._uri, auth=(self._user, self._password), connection_timeout=15)
            # Create constraints/schema idempotently.
            self._init_schema(self._driver)
        return self._driver

    def _init_schema(self, driver: Any) -> None:
        # Drop any pre-existing conflict-free index on the same label/property
        # so a uniqueness constraint can be created (a constraint and a plain
        # index cannot coexist on the same label+property).
        cleanup = [
            "DROP INDEX section_num IF EXISTS",
            "DROP INDEX chapter_id IF EXISTS",
        ]
        constraints = [
            f"CREATE CONSTRAINT section_num IF NOT EXISTS FOR (s:{self.LABEL_SECTION}) REQUIRE s.number IS UNIQUE",
            f"CREATE CONSTRAINT chapter_id IF NOT EXISTS FOR (c:{self.LABEL_CHAPTER}) REQUIRE c.id IS UNIQUE",
        ]
        with driver.session() as session:
            for cypher in [*cleanup, *constraints]:
                try:
                    session.run(cypher)
                except Exception:  # noqa: BLE001
                    pass

    def run(self, cypher: str, params: Optional[dict] = None) -> Any:
        """Execute Cypher and return a materialized list of records.

        Records are pulled inside the session so the caller may safely iterate
        them afterwards (Neo4j results are tied to the open session).
        """
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(cypher, parameters=params or {})
            records = list(result)
            return records

    # Backward-compatible alias.
    execute = run

    def ping(self) -> bool:
        try:
            self._get_driver().verify_connectivity()
            return True
        except Exception:  # noqa: BLE001
            return False

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None


@lru_cache(maxsize=None)
def get_graph_driver() -> Neo4jDriver:
    """Return a shared graph driver (model/schema created once)."""
    return Neo4jDriver()


async def ping_graph() -> bool:
    """Async-friendly connectivity probe for health checks."""

    def _probe() -> bool:
        return get_graph_driver().ping()

    return await asyncio.to_thread(_probe)

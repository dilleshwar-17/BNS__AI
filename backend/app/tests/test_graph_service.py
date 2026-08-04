"""Phase 7: graph service + retriever tests using a fake driver."""

from __future__ import annotations

import uuid

from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.graph_service import GraphService, SectionNode


class _FakeRecords:
    """Iterable of simple dict-like records."""

    def __init__(self, records: list[dict]) -> None:
        self._records = records

    def __iter__(self):
        return iter(self._records)


class _FakeDriver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._neighbors: list[dict] = []

    def set_neighbors(self, records: list[dict]) -> None:
        self._neighbors = records

    def execute(self, cypher: str, params: dict | None = None) -> list[dict]:
        self.calls.append((cypher, params or {}))
        if "neighbors" in cypher or "RETURN DISTINCT b.number" in cypher:
            return self._neighbors
        return []


def _section(num: int, ref: str = "") -> SectionNode:
    return SectionNode(
        number=num,
        title=f"Section {num}",
        chapter_id=None,
        chapter_title=None,
        source_version_id=str(uuid.uuid4()),
        section_chunk_id=str(uuid.uuid4()),
    )


def test_index_section_creates_node() -> None:
    fake = _FakeDriver()
    svc = GraphService(driver=fake)  # type: ignore[arg-type]
    svc.index_section(_section(37), "subject to section 38")
    assert fake.calls[0][0].startswith("MERGE")
    assert fake.calls[0][1]["number"] == 37


def test_index_section_creates_reference_edges() -> None:
    fake = _FakeDriver()
    svc = GraphService(driver=fake)  # type: ignore[arg-type]
    created = svc.index_section(_section(39), "as specified in sections 37 and 38")
    assert created == 2
    unwinder = next(c for c in fake.calls if "UNWIND" in c[0])
    assert unwinder[1]["targets"] == [37, 38]


def test_index_section_excludes_self_reference() -> None:
    fake = _FakeDriver()
    svc = GraphService(driver=fake)  # type: ignore[arg-type]
    created = svc.index_section(_section(37), "as per section 37")
    assert created == 0


def test_neighbors_returns_related_sections() -> None:
    fake = _FakeDriver()
    fake.set_neighbors([{"number": 37, "title": "defence", "hops": 1}, {"number": 40, "title": "defence", "hops": 1}])
    svc = GraphService(driver=fake)  # type: ignore[arg-type]
    got = svc.neighbors([39], max_hops=1)
    assert [g["number"] for g in got] == [37, 40]


def test_neighbors_empty_numbers() -> None:
    fake = _FakeDriver()
    svc = GraphService(driver=fake)  # type: ignore[arg-type]
    assert svc.neighbors([], max_hops=1) == []
    assert not fake.calls


def test_graph_retriever_disabled_returns_empty(monkeypatch) -> None:
    fake = _FakeDriver()
    service = GraphService(driver=fake)  # type: ignore[arg-type]
    retriever = GraphRetriever(service=service)  # type: ignore[arg-type]
    monkeypatch.setattr(retriever, "_enabled", False)
    assert retriever.expand([39]) == []
    assert not fake.calls


def test_graph_retriever_expand_uses_neighbors(monkeypatch) -> None:
    fake = _FakeDriver()
    fake.set_neighbors([{"number": 37, "title": "defence", "hops": 1}])
    service = GraphService(driver=fake)  # type: ignore[arg-type]
    retriever = GraphRetriever(service=service)  # type: ignore[arg-type]
    monkeypatch.setattr(retriever, "_enabled", True)
    got = retriever.expand([39])
    assert got and got[0]["number"] == 37


def test_graph_retriever_failure_fails_open() -> None:
    class _Boom:
        def neighbors(self, *a, **k):
            raise RuntimeError("neo4j down")

    retriever = GraphRetriever(service=_Boom())  # type: ignore[arg-type]
    retriever._enabled = True
    assert retriever.expand([1]) == []

"""Phase 13: conversation memory tests (coreference + persistence)."""

from __future__ import annotations

import uuid

from app.models.chat import Conversation
from app.models.user import User
from app.services.memory import MemoryService, _extract_sections


def test_extract_sections_single() -> None:
    assert _extract_sections("per section 44 the defence applies") == [44]


def test_extract_sections_plural_with_and() -> None:
    assert _extract_sections("see sections 44 and 45") == [44, 45]


def test_extract_sections_comma_list() -> None:
    assert _extract_sections("sections 112, 113 and 114") == [112, 113, 114]


def test_coreference_section_referent() -> None:
    svc = MemoryService()
    recall = svc.core_reference("is it an offence under that section?", ["section 44 covers private defence."])
    assert recall.referent == "section 44"
    assert "section 44" in recall.query
    assert recall.confidence > 0.5


def test_coreference_topic_referent() -> None:
    svc = MemoryService()
    recall = svc.core_reference("what is the punishment for it?", ["what about murder"])
    assert recall.referent == "murder"
    assert "murder" in recall.query


def test_coreference_no_pronoun_untouched() -> None:
    svc = MemoryService()
    recall = svc.core_reference("define theft", ["section 112 theft."])
    assert recall.referent is None
    assert recall.query == "define theft"


def test_coreference_empty_recent() -> None:
    svc = MemoryService()
    recall = svc.core_reference("what about it", [])
    assert recall.referent is None


def test_extract_entities_section() -> None:
    svc = MemoryService()
    entities = svc.extract_entities("Section 44 covers private defence")
    assert any(e["entity_type"] == "SECTION" and e["section_refs"] == [44] for e in entities)


def test_extract_entities_offence() -> None:
    svc = MemoryService()
    entities = svc.extract_entities("what is the punishment for theft")
    assert any(e["entity_type"] == "OFFENCE" and e["entity"] == "theft" for e in entities)


async def test_memory_persistence_and_window(db_session) -> None:
    svc = MemoryService(recent_window=2)
    cid = await _conversation(db_session)
    for i in range(1, 5):
        await svc.add_recent(db_session, conversation_id=cid, content=f"turn {i}")
    await db_session.commit()

    rows = await svc.recall(db_session, cid)
    active = [r for r in rows if not r.invalidated]
    assert len(active) == 2  # window trimmed to last 2
    contents = [r.content for r in active]
    assert "turn 3" in contents and "turn 4" in contents


async def test_recall_ordering_and_layers(db_session) -> None:
    svc = MemoryService()
    cid = await _conversation(db_session)
    await svc.upsert_summary(db_session, conversation_id=cid, content="summary", section_refs=[44])
    await svc.add_entity(
        db_session, conversation_id=cid, entity="murder", entity_type="OFFENCE", content="talked", confidence=0.7
    )
    await db_session.commit()
    rows = await svc.recall(db_session, cid)
    layers = {r.layer for r in rows}
    assert "SUMMARY" in layers and "ENTITY" in layers


async def test_invalidate_topics(db_session) -> None:
    svc = MemoryService()
    cid = await _conversation(db_session)
    await svc.add_entity(
        db_session, conversation_id=cid, entity="theft", entity_type="OFFENCE", content="x", confidence=0.7
    )
    await db_session.commit()
    await svc.invalidate_topics(db_session, cid, ["theft"])
    await db_session.commit()
    rows = await svc.recall(db_session, cid)
    assert not any(r.layer == "ENTITY" for r in rows)


async def _conversation(db_session) -> uuid.UUID:
    user = User(
        email=f"u{uuid.uuid4()}@test.dev",
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="x",
    )
    db_session.add(user)
    await db_session.commit()
    conv = Conversation(id=uuid.uuid4(), title="m", user_id=user.id)
    db_session.add(conv)
    await db_session.commit()
    return conv.id

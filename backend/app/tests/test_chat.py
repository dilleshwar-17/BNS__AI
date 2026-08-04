"""Phase 8: chat service persistence tests (in-memory DB)."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from app.agents.orchestrator import AgentOrchestrator, AgentOutcome, EvidenceItem
from app.chat.service import create_conversation, get_conversation_or_404, run_turn
from app.core.exceptions import NotFoundError
from app.models.chat import Message, MessageCitation
from app.models.user import User
from sqlalchemy import select


class _NoopOrchestrator(AgentOrchestrator):
    def run(self, query: str) -> AgentOutcome:
        cid = uuid.uuid4()
        ev = EvidenceItem(
            chunk_id=cid,
            section_id="112",
            section_title="Theft",
            element_type="SECTION",
            text="Section 112 text",
            score=0.9,
        )
        return AgentOutcome(
            answer="Under section 112 theft is punished.",
            intent="PUNISHMENT_LOOKUP",
            evidence=[ev],
            grounded=True,
            model="fake",
        )


@pytest_asyncio.fixture
async def noop() -> AgentOrchestrator:
    return _NoopOrchestrator()


async def test_create_and_get_conversation(db_session) -> None:
    user = await _make_user(db_session)
    conv = await create_conversation(db_session, user.id, title="test")
    await db_session.commit()

    got = await get_conversation_or_404(db_session, conv.id, user.id)
    assert got.id == conv.id
    assert got.title == "test"


async def test_get_conversation_not_found(db_session) -> None:
    user = await _make_user(db_session)
    with pytest.raises(NotFoundError):
        await get_conversation_or_404(db_session, uuid.uuid4(), user.id)


async def test_run_turn_persists_message_and_citations(db_session, noop) -> None:
    user = await _make_user(db_session)
    conv = await create_conversation(db_session, user.id)
    result = await run_turn(db_session, conversation=conv, user_content="punishment for theft", orchestrator=noop)
    await db_session.commit()

    assert result.grounded is True
    msgs = (await db_session.execute(select(Message).where(Message.conversation_id == conv.id))).scalars().all()
    assert len(msgs) == 2
    roles = {m.role for m in msgs}
    assert roles == {"USER", "ASSISTANT"}

    citations = (await db_session.execute(select(MessageCitation))).scalars().all()
    assert len(citations) == 1
    assert citations[0].section_id == "112"


async def _make_user(db_session) -> User:
    user = User(
        email=f"u{uuid.uuid4()}@test.dev",
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="x",
    )
    db_session.add(user)
    await db_session.commit()
    return user

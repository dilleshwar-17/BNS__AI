"""Chat service: orchestrates a turn and persists conversation/message/citations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.orchestrator import AgentOrchestrator
from app.core.exceptions import NotFoundError
from app.models.chat import Conversation, Message, MessageCitation
from app.services.memory import MemoryService


@dataclass
class TurnResult:
    message: Message
    conversation: Conversation
    grounded: bool
    intent: str | None


async def get_conversation_or_404(
    session: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation:
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages).selectinload(Message.citations))
        .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise NotFoundError("Conversation not found.")
    return conv


async def create_conversation(session: AsyncSession, user_id: uuid.UUID, title: str | None = None) -> Conversation:
    conv = Conversation(user_id=user_id, title=title)
    session.add(conv)
    await session.flush()
    return conv


async def run_turn(
    session: AsyncSession,
    *,
    conversation: Conversation,
    user_content: str,
    orchestrator: Optional[AgentOrchestrator] = None,
    memory: Optional[MemoryService] = None,
) -> TurnResult:
    """Persist user message, run the agentic pipeline, persist assistant response.

    Conversation memory is read before generation (coreference resolution) and
    written after (recent + entity layers) so follow-ups stay grounded.
    """
    memory = memory or MemoryService()
    query = user_content

    prior = [m.content for m in await memory.recall(session, conversation.id)]
    recall = memory.core_reference(query, prior)
    if recall.referent:
        query = recall.query

    user_msg = Message(conversation_id=conversation.id, role="USER", content=user_content)
    session.add(user_msg)
    await session.flush()

    orchestrator = orchestrator or AgentOrchestrator()
    outcome = orchestrator.run(query)

    assistant = Message(
        conversation_id=conversation.id,
        role="ASSISTANT",
        content=outcome.answer,
        intent=outcome.intent,
        model=outcome.model,
        grounded=outcome.grounded,
        trace={"note": outcome.note},
    )
    session.add(assistant)
    await session.flush()

    for ev in outcome.evidence:
        citation = MessageCitation(
            message_id=assistant.id,
            chunk_id=ev.chunk_id,
            section_id=ev.section_id,
            section_title=ev.section_title,
            element_type=ev.element_type,
            excerpt=ev.text[:400],
        )
        session.add(citation)

    # Write memory layers.
    await memory.add_recent(
        session,
        conversation_id=conversation.id,
        content=user_content,
        source_message_id=user_msg.id,
    )
    for ent in memory.extract_entities(user_content):
        await memory.add_entity(
            session,
            conversation_id=conversation.id,
            entity=ent["entity"],
            entity_type=ent["entity_type"],
            content=ent["content"],
            confidence=ent["confidence"],
            section_refs=ent["section_refs"],
            source_message_id=user_msg.id,
        )
    section_refs = sorted(
        {s for ev in outcome.evidence if ev.section_id and ev.section_id.isdigit() for s in [ev.section_id]}
    )
    await memory.upsert_summary(
        session,
        conversation_id=conversation.id,
        content=f"{outcome.intent}: {outcome.answer[:200]}",
        section_refs=[int(s) for s in section_refs],
        source_message_id=assistant.id,
    )

    return TurnResult(
        message=assistant,
        conversation=conversation,
        grounded=outcome.grounded,
        intent=outcome.intent,
    )

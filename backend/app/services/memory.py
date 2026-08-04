"""Conversation memory service (Phase 13).

Multi-layer, deterministic memory (RECENT / SUMMARY / ENTITY / CASE) plus
coreference resolution. Follow-up pronouns are rewritten to their most recent
concrete referent so retrieval stays grounded. Memory never acts as the source
of legal truth — it only supplies context for evidence-backed retrieval, so the
fail-closed invariant is preserved.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.memory import (
    MEMORY_ENTITY,
    MEMORY_RECENT,
    MEMORY_SUMMARY,
    ConversationMemory,
)

_SECTION_REF = re.compile(r"\bsections?\s+(\d{1,3}(?:\s*,\s*\d{1,3})*(?:\s+and\s+\d{1,3})?)\b", re.I)
_NUM = re.compile(r"\d{1,3}")
_PRONOUN = re.compile(r"\b(its|it|that|those|this|them|they|such offence|the section)\b", re.I)
_TOPIC_WORDS = (
    "murder",
    "theft",
    "robbery",
    "dacouity",
    "assault",
    "hurt",
    "cheating",
    "fraud",
    "bail",
    "defamation",
    "criminal",
    "breach of trust",
)


def _extract_sections(text: str) -> list[int]:
    """Extract cited section numbers from text."""
    return [int(n) for n in _NUM.findall(" ".join(_SECTION_REF.findall(text or "")))]


@dataclass
class Recall:
    query: str
    referent: str | None
    confidence: float


def _heading(text: str) -> str:
    return " ".join(text.split())[:120]


class MemoryService:
    """Read/write layered conversation memory + coreference resolution."""

    def __init__(self, *, recent_window: int | None = None) -> None:
        settings = get_settings()
        self._window = recent_window or settings.memory_recent_window

    # -- persistence -------------------------------------------------------

    async def add_recent(
        self,
        session: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        content: str,
        source_message_id: uuid.UUID | None = None,
    ) -> None:
        await self._push(
            session,
            conversation_id=conversation_id,
            layer=MEMORY_RECENT,
            content=_heading(content),
            source_message_id=source_message_id,
        )

    async def add_entity(
        self,
        session: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        entity: str,
        entity_type: str,
        content: str,
        confidence: float,
        section_refs: list[int] | None = None,
        source_message_id: uuid.UUID | None = None,
    ) -> None:
        await self._push(
            session,
            conversation_id=conversation_id,
            layer=MEMORY_ENTITY,
            content=_heading(content),
            entity=entity,
            entity_type=entity_type,
            confidence=confidence,
            section_refs=",".join(str(s) for s in (section_refs or [])) or None,
            source_message_id=source_message_id,
        )

    async def upsert_summary(
        self,
        session: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        content: str,
        section_refs: list[int] | None = None,
        source_message_id: uuid.UUID | None = None,
    ) -> None:
        await self._push(
            session,
            conversation_id=conversation_id,
            layer=MEMORY_SUMMARY,
            content=_heading(content),
            section_refs=",".join(str(s) for s in (section_refs or [])) or None,
            source_message_id=source_message_id,
        )

    async def _push(
        self,
        session: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        layer: str,
        content: str,
        entity: str | None = None,
        entity_type: str | None = None,
        confidence: float | None = None,
        section_refs: str | None = None,
        source_message_id: uuid.UUID | None = None,
    ) -> None:
        mem = ConversationMemory(
            conversation_id=conversation_id,
            layer=layer,
            content=content,
            entity=entity,
            entity_type=entity_type,
            confidence=confidence,
            section_refs=section_refs,
            source_message_id=source_message_id,
        )
        session.add(mem)
        await session.flush()
        await self._trim_recent(session, conversation_id)

    async def _trim_recent(self, session: AsyncSession, conversation_id: uuid.UUID) -> None:
        stale = (
            (
                await session.execute(
                    select(ConversationMemory.seq)
                    .where(
                        ConversationMemory.conversation_id == conversation_id,
                        ConversationMemory.layer == MEMORY_RECENT,
                        ConversationMemory.invalidated.is_(False),
                    )
                    .order_by(ConversationMemory.seq.desc())
                    .offset(self._window)
                )
            )
            .scalars()
            .all()
        )
        if stale:
            await session.execute(
                update(ConversationMemory).where(ConversationMemory.seq.in_(list(stale))).values(invalidated=True)
            )

    async def recall(
        self, session: AsyncSession, conversation_id: uuid.UUID, *, include_invalid: bool = False
    ) -> list[ConversationMemory]:
        stmt = (
            select(ConversationMemory)
            .where(ConversationMemory.conversation_id == conversation_id)
            .order_by(ConversationMemory.seq.asc())
        )
        if not include_invalid:
            stmt = stmt.where(ConversationMemory.invalidated.is_(False))
        return list((await session.execute(stmt)).scalars().all())

    async def invalidate_topics(self, session: AsyncSession, conversation_id: uuid.UUID, topics: list[str]) -> None:
        tset = {t.lower() for t in topics}
        if not tset:
            return
        for mem in await self.recall(session, conversation_id):
            if mem.layer == MEMORY_ENTITY and mem.entity and mem.entity.lower() in tset:
                mem.invalidated = True
        await session.flush()

    def entity_is_active(self, mem: ConversationMemory) -> bool:
        return bool(mem.entity) and mem.invalidated is False

    # -- extraction ---------------------------------------------------------

    def extract_entities(self, text: str) -> list[dict]:
        entities: list[dict] = []
        for sec in _extract_sections(text):
            entities.append(
                {
                    "entity": f"section {sec}",
                    "entity_type": "SECTION",
                    "confidence": 0.0,
                    "content": f"BNS section {sec}",
                    "section_refs": [sec],
                }
            )
        lowered = (text or "").lower()
        for word in _TOPIC_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", lowered):
                entities.append(
                    {
                        "entity": word,
                        "entity_type": "OFFENCE",
                        "confidence": 0.7,
                        "content": f"Discussed: {word}",
                        "section_refs": [],
                    }
                )
        return entities

    # -- coreference --------------------------------------------------------

    def core_reference(self, query: str, recent: list[str]) -> Recall:
        if not _PRONOUN.search(query or ""):
            return Recall(query, None, 0.0)
        for turn in reversed(recent or []):
            lowered_turn = turn.lower()
            for sec in _extract_sections(turn):
                referent = f"section {sec}"
                if referent in lowered_turn:
                    return Recall(f"{referent} {query}", referent, 0.9)
            for word in _TOPIC_WORDS:
                if re.search(rf"\b{re.escape(word)}\b", lowered_turn):
                    resolved = re.sub(r"\b(it|that|those|this|them|they)\b", f"the {word}", query)
                    return Recall(resolved, word, 0.7)
        return Recall(query, None, 0.2)

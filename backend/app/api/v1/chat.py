"""Chat router (Phase 8). Matches docs/api.md chat contract."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit_service
from app.auth.dependencies import get_current_user
from app.chat.service import (
    create_conversation,
    get_conversation_or_404,
    run_turn,
)
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.models.chat import Message
from app.models.user import User
from app.schemas.chat import (
    CitationRead,
    ConversationDetail,
    ConversationList,
    ConversationRead,
    MessageRead,
    SendMessageRequest,
)

router = APIRouter()

_MESSAGE_LIMIT = 50


def _citation_read(ev) -> CitationRead:
    return CitationRead(
        chunk_id=ev.chunk_id,
        section_id=ev.section_id,
        section_title=ev.section_title,
        element_type=ev.element_type,
        excerpt=ev.excerpt,
    )


def _message_read(msg: Message) -> MessageRead:
    return MessageRead(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        intent=msg.intent,
        model=msg.model,
        grounded=msg.grounded,
        created_at=msg.created_at,
        citations=[_citation_read(c) for c in msg.citations],
    )


@router.get("/", response_model=ConversationList, summary="List my chats")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConversationList:
    from sqlalchemy import select

    from app.models.chat import Conversation

    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    return ConversationList(conversations=[ConversationRead.model_validate(c) for c in result.scalars().all()])


@router.post("/", response_model=ConversationRead, summary="Create a chat")
async def create_chat(
    payload: SendMessageRequest | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConversationRead:
    title = payload.content[:60] if payload and payload.content else None
    conv = await create_conversation(session, current_user.id, title=title)
    await audit_service.record(
        session,
        action="chat.create",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="conversation",
        resource_id=str(conv.id),
    )
    await session.commit()
    return ConversationRead.model_validate(conv)


@router.get("/{conversation_id}", response_model=ConversationDetail, summary="Get messages")
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    conv = await get_conversation_or_404(session, conversation_id, current_user.id)
    detail = ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[_message_read(m) for m in conv.messages],
    )
    return detail


@router.post("/{conversation_id}", response_model=MessageRead, summary="Send a message")
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageRead:
    conv = await get_conversation_or_404(session, conversation_id, current_user.id)
    turn = await run_turn(session, conversation=conv, user_content=payload.content)
    await audit_service.record(
        session,
        action="chat.message",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="conversation",
        resource_id=str(conv.id),
        metadata={"grounded": turn.grounded, "intent": turn.intent},
    )
    await session.commit()
    await session.refresh(turn.message)
    return _message_read(turn.message)

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator.pipeline import pipeline as ai_pipeline
from app.api.deps import get_current_user
from app.core.logging import get_logger, request_id_var
from app.core.pagination import Paginator
from app.database.models.chat import Chat
from app.database.models.message import Message
from app.database.models.user import User
from app.database.session import get_db
from app.middleware.prompt_injection import check_text_for_injection
from app.middleware.rate_limit import check_rate_limit
from app.schemas.chat import ChatCreate, ChatFeedback, ChatResponse, ChatSend, MessageResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

_agent_initialized = False


async def _ensure_agent():
    global _agent_initialized
    if not _agent_initialized:
        try:
            from app.ai.agents.master_agent import master_agent

            master_agent.start()
            _agent_initialized = True
        except Exception as e:
            logger.warning("agent_init_failed", error=str(e))


async def _get_chat_with_history(chat_id: str, user_id: str, db: AsyncSession, max_history: int = 10):
    result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id))
    chat = result.scalar_one_or_none()
    if not chat:
        return None, []

    msgs = await db.execute(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.desc()).limit(max_history)
    )
    history = list(reversed(msgs.scalars().all()))
    return chat, history


async def _route_via_agent(query: str, mode: str, user_id: str, history: list | None = None) -> str:
    result = await ai_pipeline.process(
        query=query,
        mode=mode,
        user_id=user_id,
        chat_history=history,
    )
    response = result.get("response", "")
    if response:
        return response
    return "I'm unable to process your request at the moment. Please try again."


@router.get("/", response_model=list[ChatResponse])
async def list_chats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total_q = await db.execute(select(func.count(Chat.id)).where(Chat.user_id == user.id))
    total = total_q.scalar() or 0
    paginator = Paginator(total, page, page_size)

    result = await db.execute(
        select(Chat)
        .where(Chat.user_id == user.id)
        .order_by(Chat.updated_at.desc())
        .limit(paginator.page_size)
        .offset(paginator.offset)
    )
    chats = result.scalars().all()
    return chats


@router.post("/", response_model=ChatResponse, status_code=201)
async def create_chat(body: ChatCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chat = Chat(id=str(uuid.uuid4()), user_id=user.id, title=body.title, mode=body.mode)
    db.add(chat)
    await db.flush()
    return chat


@router.get("/{chat_id}", response_model=list[MessageResponse])
async def get_chat_messages(chat_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == user.id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    msgs = await db.execute(select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at))
    return msgs.scalars().all()


@router.post("/{chat_id}", response_model=MessageResponse)
async def send_message(
    chat_id: str,
    body: ChatSend,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(check_rate_limit),
):
    violations = check_text_for_injection(body.message)
    high = [v for v in violations if v["severity"] == "high"]
    if high:
        raise HTTPException(status_code=400, detail="Message contains prohibited content")

    chat, history = await _get_chat_with_history(chat_id, user.id, db)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    user_msg = Message(id=str(uuid.uuid4()), chat_id=chat_id, role="user", content=body.message)
    db.add(user_msg)
    await db.flush()

    request_id = request_id_var.get()
    logger.info("chat_message_received", user_id=user.id, chat_id=chat_id, request_id=request_id)

    response_content = await _route_via_agent(body.message, body.mode, user.id, history)

    assistant_msg = Message(id=str(uuid.uuid4()), chat_id=chat_id, role="assistant", content=response_content)
    db.add(assistant_msg)

    if chat.title == "New Chat":
        chat.title = body.message[:50] + ("..." if len(body.message) > 50 else "")

    await db.flush()
    return assistant_msg


@router.post("/{chat_id}/stream")
async def send_message_stream(
    chat_id: str, body: ChatSend, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    violations = check_text_for_injection(body.message)
    high = [v for v in violations if v["severity"] == "high"]
    if high:
        raise HTTPException(status_code=400, detail="Message contains prohibited content")

    chat, history = await _get_chat_with_history(chat_id, user.id, db)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    user_msg = Message(id=str(uuid.uuid4()), chat_id=chat_id, role="user", content=body.message)
    db.add(user_msg)
    await db.flush()

    if chat.title == "New Chat":
        chat.title = body.message[:50] + ("..." if len(body.message) > 50 else "")
        await db.flush()

    async def event_generator():
        from app.database.session import async_session_factory

        full_content = ""
        assistant_id = str(uuid.uuid4())

        try:
            async for token in ai_pipeline.stream_response(
                body.message, body.mode, user.id, history
            ):
                full_content += token
                yield f"data: {json.dumps({'token': token, 'content': full_content})}\n\n"
        except Exception as e:
            logger.error("stream_generation_error", error=str(e))
            full_content = "I'm unable to process your request at the moment. Please try again."
            yield f"data: {json.dumps({'token': full_content, 'content': full_content})}\n\n"

        try:
            async with async_session_factory() as session:
                assistant_msg = Message(id=assistant_id, chat_id=chat_id, role="assistant", content=full_content)
                session.add(assistant_msg)
                await session.commit()
        except Exception as e:
            logger.error("stream_save_failed", error=str(e))

        yield f"data: {json.dumps({'done': True, 'message_id': assistant_id})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{chat_id}/messages/{message_id}/feedback")
async def feedback_message(
    chat_id: str,
    message_id: str,
    body: ChatFeedback,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Message).where(Message.id == message_id, Message.chat_id == chat_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    chat_result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == user.id))
    if not chat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Chat not found")

    import uuid as _uuid

    from app.database.models.feedback import Feedback

    feedback = Feedback(
        id=str(_uuid.uuid4()),
        user_id=user.id,
        message_id=message_id,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(feedback)
    await db.flush()
    logger.info("feedback_received", user_id=user.id, message_id=message_id, rating=body.rating)
    return {"message": "Feedback recorded"}


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(chat_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == user.id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    await db.delete(chat)
    await db.flush()
    return None

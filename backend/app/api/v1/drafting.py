import json
import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.drafting.exporter import draft_exporter
from app.ai.drafting.orchestrator import orchestrator
from app.ai.drafting.questionnaire import questionnaire
from app.ai.drafting.template_registry import template_registry
from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.core.pagination import Paginator
from app.database.models.document import Document
from app.database.models.document_version import DocumentVersion
from app.database.models.draft_session import DraftAnswer, DraftSession
from app.database.models.user import User
from app.database.session import get_db
from app.middleware.rate_limit import check_rate_limit
from app.schemas.document import DocumentResponse
from app.schemas.drafting import (
    AnswerRequest,
    AnswerResponse,
    DraftGenerate,
    QuestionnaireResponse,
    SaveProgressRequest,
    SaveRawDraft,
    StartDraftRequest,
    StartDraftResponse,
    SuggestRequest,
    SuggestResponse,
    ValidationError,
    ValidationRequest,
    ValidationResponse,
)
from app.services.drafting_service import get_draft_template, get_draft_types

logger = get_logger(__name__)
router = APIRouter(prefix="/drafting", tags=["drafting"])


@router.post("/start", response_model=StartDraftResponse)
async def start_draft_session(
    body: StartDraftRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    draft_type = body.template or body.draft_type or "legal_notice"
    qdef = questionnaire.get_definitions(draft_type)
    if not qdef:
        raise HTTPException(status_code=404, detail=f"Draft type template not found: {draft_type}")

    session = DraftSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        draft_type=draft_type,
        current_step=0,
        total_steps=len(qdef.get("groups", [])) or 1,
        status="in_progress",
    )
    db.add(session)
    await db.flush()

    q_resp = QuestionnaireResponse(
        draft_type=draft_type,
        title=qdef.get("title", draft_type),
        description=qdef.get("description", ""),
        groups=[
            {
                "id": g.get("id", ""),
                "title": g.get("title", ""),
                "description": g.get("description", ""),
                "fields": [
                    {
                        "id": f.get("key", f.get("id", "")),
                        "label": f.get("label", ""),
                        "type": f.get("type", "text"),
                        "required": f.get("required", False),
                        "placeholder": f.get("placeholder", ""),
                        "help_text": f.get("help_text", ""),
                        "default": f.get("default"),
                        "validation": f.get("validation"),
                        "options": [
                            {
                                "label": o if isinstance(o, str) else o.get("label", o),
                                "value": o if isinstance(o, str) else o.get("value", o),
                            }
                            for o in (f.get("options") or [])
                        ]
                        if f.get("options")
                        else None,
                    }
                    for f in g.get("fields", [])
                ],
            }
            for g in qdef.get("groups", [])
        ],
    )

    return StartDraftResponse(
        session_id=session.id,
        draft_type=draft_type,
        title=qdef.get("title", draft_type),
        questionnaire=q_resp,
    )


@router.post("/session/{session_id}/answer", response_model=AnswerResponse)
async def save_session_answer(
    session_id: str,
    body: AnswerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DraftSession).where(DraftSession.id == session_id, DraftSession.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Draft session not found")

    existing_data = json.loads(session.form_data) if session.form_data else {}

    if body.answers:
        for k, v in body.answers.items():
            existing_data[k] = v
            ans = DraftAnswer(
                id=str(uuid.uuid4()),
                session_id=session.id,
                field_key=k,
                field_value=str(v) if v is not None else None,
            )
            db.add(ans)
    elif body.field_key:
        existing_data[body.field_key] = body.field_value
        ans = DraftAnswer(
            id=str(uuid.uuid4()),
            session_id=session.id,
            field_key=body.field_key,
            field_value=str(body.field_value) if body.field_value is not None else None,
        )
        db.add(ans)

    session.form_data = json.dumps(existing_data)
    session.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return AnswerResponse(
        session_id=session.id,
        field_key=body.field_key,
        saved=True,
        updated_at=session.updated_at.isoformat(),
    )


@router.get("/types")
async def list_draft_types():
    return {"draft_types": get_draft_types(), "templates": template_registry.list_types()}


@router.get("/templates/{draft_type}")
async def get_template(draft_type: str):
    tpl = template_registry.get(draft_type)
    if not tpl:
        raise HTTPException(status_code=404, detail="Draft type not found")
    svc = get_draft_template(draft_type)
    return {"template": svc, "definition": tpl} if svc else {"definition": tpl}


@router.post("/generate", response_model=DocumentResponse)
async def create_draft(
    body: DraftGenerate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(check_rate_limit),
):
    result = await orchestrator.run_pipeline(body.draft_type, body.details or {})
    content = result.get("content", "")
    title = result.get("title", template_registry.get_title(body.draft_type))

    doc = Document(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=title,
        content=content,
        doc_type=body.draft_type,
    )
    db.add(doc)
    await db.flush()
    return doc


@router.post("/save", response_model=DocumentResponse)
async def save_raw_draft(
    body: SaveRawDraft,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(check_rate_limit),
):
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=body.title,
        content=body.content,
        doc_type=body.draft_type,
    )
    db.add(doc)
    await db.flush()
    return doc


@router.get("/generate/stream/{draft_type}")
async def stream_generate_draft(draft_type: str, user: User = Depends(get_current_user)):
    details_raw = {}

    async def event_stream():
        async for event in orchestrator.stream_generate(draft_type, details_raw):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/questionnaire/{draft_type}", response_model=QuestionnaireResponse)
async def get_questionnaire(draft_type: str):
    qdef = questionnaire.get_definitions(draft_type)
    if not qdef:
        raise HTTPException(status_code=404, detail="Draft type not found")
    return QuestionnaireResponse(
        draft_type=draft_type,
        title=qdef.get("title", draft_type),
        description=qdef.get("description", ""),
        groups=[
            {
                "id": g.get("id", ""),
                "title": g.get("title", ""),
                "description": g.get("description", ""),
                "fields": [
                    {
                        "id": f.get("key", f.get("id", "")),
                        "label": f.get("label", ""),
                        "type": f.get("type", "text"),
                        "required": f.get("required", False),
                        "placeholder": f.get("placeholder", ""),
                        "help_text": f.get("help_text", ""),
                        "default": f.get("default"),
                        "validation": f.get("validation"),
                        "options": [
                            {
                                "label": o if isinstance(o, str) else o.get("label", o),
                                "value": o if isinstance(o, str) else o.get("value", o),
                            }
                            for o in (f.get("options") or [])
                        ]
                        if f.get("options")
                        else None,
                    }
                    for f in g.get("fields", [])
                ],
            }
            for g in qdef.get("groups", [])
        ],
    )


@router.post("/questionnaire/{draft_type}/validate", response_model=ValidationResponse)
async def validate_questionnaire(draft_type: str, body: ValidationRequest):
    qdef = questionnaire.get_definitions(draft_type)
    if not qdef:
        raise HTTPException(status_code=404, detail="Draft type not found")
    if body.group_id:
        errs = questionnaire.validate_group(draft_type, body.group_id, body.details)
    else:
        errs = questionnaire.validate(draft_type, body.details)
    return ValidationResponse(
        valid=len(errs) == 0,
        errors=[ValidationError(**e) for e in errs],
    )


@router.post("/questionnaire/{draft_type}/suggest", response_model=SuggestResponse)
async def suggest_field(draft_type: str, body: SuggestRequest):
    qdef = questionnaire.get_definitions(draft_type)
    if not qdef:
        raise HTTPException(status_code=404, detail="Draft type not found")
    fields = questionnaire.get_fields_flat(draft_type)
    field_map = {f.get("key", f.get("id")): f for f in fields}
    field_def = field_map.get(body.field_id)
    if not field_def:
        raise HTTPException(status_code=404, detail="Field not found")
    try:
        from app.ai.llms.router import llm_router

        context_str = json.dumps(body.context or {}, indent=2)
        prompt = (
            f"You are a legal drafting assistant for Indian law.\n"
            f"Document type: {qdef.get('title', draft_type)}\n"
            f"Field: {field_def.get('label', body.field_id)}\n"
            f"Context:\n{context_str}\n\n"
            f"Suggest a concise and appropriate value for this field. Return ONLY the value."
        )
        suggestion = await llm_router.route(prompt, "legal_drafting")
        if suggestion and len(suggestion.strip()) > 3:
            return SuggestResponse(suggestion=suggestion.strip(), confidence=0.7)
    except Exception as e:
        logger.warning("ai_suggest_failed", error=str(e))
    return SuggestResponse(suggestion="", confidence=0.0)


@router.post("/save-progress")
async def save_progress(
    body: SaveProgressRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    existing = await db.execute(
        select(DraftSession)
        .where(
            DraftSession.user_id == user.id,
            DraftSession.draft_type == body.draft_type,
            DraftSession.status == "in_progress",
        )
        .order_by(DraftSession.updated_at.desc())
        .limit(1)
    )
    session = existing.scalar_one_or_none()
    if not session:
        session = DraftSession(
            id=str(uuid.uuid4()),
            user_id=user.id,
            draft_type=body.draft_type,
            current_step=body.current_step,
        )
        db.add(session)
    session.form_data = json.dumps(body.form_data)
    session.current_step = body.current_step
    session.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return {"session_id": session.id}


@router.get("/sessions")
async def list_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DraftSession).where(DraftSession.user_id == user.id).order_by(DraftSession.updated_at.desc()).limit(10)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "draft_type": s.draft_type,
            "current_step": s.current_step,
            "progress": s.progress,
            "status": s.status,
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DraftSession).where(DraftSession.id == session_id, DraftSession.user_id == user.id)
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    answers = await db.execute(select(DraftAnswer).where(DraftAnswer.session_id == session_id))
    return {
        "id": s.id,
        "draft_type": s.draft_type,
        "current_step": s.current_step,
        "total_steps": s.total_steps,
        "progress": s.progress,
        "form_data": json.loads(s.form_data) if s.form_data else {},
        "status": s.status,
        "answers": [{"field_key": a.field_key, "field_value": a.field_value} for a in answers.scalars().all()],
    }


@router.get("/export/{doc_id}/docx")
async def export_docx(doc_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    content = await draft_exporter.export_docx(doc.content, doc.title)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{doc.title.replace(" ", "_")}.docx"'},
    )


@router.get("/export/{doc_id}/pdf")
async def export_pdf(doc_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    content = await draft_exporter.export_pdf(doc.content, doc.title)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.title.replace(" ", "_")}.pdf"'},
    )


@router.get("/export/{doc_id}/markdown")
async def export_markdown(doc_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    content = await draft_exporter.export_markdown(doc.content, doc.title)
    return StreamingResponse(
        BytesIO(content),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{doc.title.replace(" ", "_")}.md"'},
    )


@router.post("/regenerate-section")
async def regenerate_section(
    draft_id: str,
    section: str,
    instructions: str = "",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == draft_id, Document.user_id == user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        from app.ai.llms.router import llm_router

        prompt = (
            f"You are a legal drafting assistant. Regenerate the following section of a {doc.doc_type} document.\n\n"
            f"Section to regenerate: {section}\n"
            f"Additional instructions: {instructions}\n\n"
            f"Existing document:\n{doc.content[:2000]}\n\n"
            f"Return ONLY the regenerated section content."
        )
        new_content = await llm_router.route(prompt, "legal_drafting")
        if new_content and len(new_content) > 20:
            version = await db.execute(
                select(func.max(DocumentVersion.version)).where(DocumentVersion.document_id == doc.id)
            )
            v = (version.scalar() or 0) + 1
            dv = DocumentVersion(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                version=v,
                content=doc.content,
                title=doc.title,
                change_summary=f"Regenerated section: {section}",
                created_by=user.id,
            )
            db.add(dv)
            return {"new_content": new_content, "version": v}
    except Exception as e:
        logger.warning("regenerate_failed", error=str(e))
    return {"new_content": "", "version": 0}


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total_q = await db.execute(select(func.count(Document.id)).where(Document.user_id == user.id))
    total = total_q.scalar() or 0
    paginator = Paginator(total, page, page_size)
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
        .limit(paginator.page_size)
        .offset(paginator.offset)
    )
    return result.scalars().all()


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.flush()
    return None


@router.get("/documents/{doc_id}/versions")
async def get_document_versions(
    doc_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    versions = await db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == doc_id).order_by(DocumentVersion.version.desc())
    )
    return [
        {
            "version": v.version,
            "title": v.title,
            "change_summary": v.change_summary,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions.scalars().all()
    ]


@router.get("/documents/{doc_id}/download")
async def download_document_docx(
    doc_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    content = await draft_exporter.export_docx(doc.content, doc.title)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{doc.title.replace(" ", "_")}.docx"'},
    )

"""Documents router: upload, list, get, delete (frontend contract)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit_service
from app.auth.dependencies import get_current_user, require_permission
from app.core.exceptions import InvalidRequestError
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.models.analysis import DocumentAnalysis
from app.models.sources import SourceDocument
from app.models.user import User
from app.schemas.analysis import DocumentAnalysisRead
from app.schemas.sources import DocumentListResponse, DocumentRead, UploadResponse
from app.services.document_analysis import DocumentAnalysisService
from app.source_management.service import (
    create_uploaded_document,
    delete_document,
    get_document,
)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload/", response_model=UploadResponse, summary="Upload a legal document")
async def upload(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("documents.upload")),
    session: AsyncSession = Depends(get_db),
) -> UploadResponse:
    # Derive extension from the uploaded filename.
    filename = file.filename or "unnamed"
    actual_ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if actual_ext not in ALLOWED_EXTENSIONS:
        raise InvalidRequestError("Unsupported file type. Allowed: " + ", ".join(sorted(ALLOWED_EXTENSIONS)))
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise InvalidRequestError("File exceeds the 10 MB size limit.")

    file_type = actual_ext.lstrip(".")
    if file_type in {"png", "jpg", "jpeg", "tiff", "tif", "bmp"}:
        file_type = "image"

    result = await create_uploaded_document(
        session,
        filename=filename,
        file_type=file_type,
        file_size=len(content),
        content=content,
        uploaded_by=current_user.id,
    )
    await audit_service.record(
        session,
        action="documents.upload",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="document",
        resource_id=str(result.document.id),
        metadata={"filename": filename, "duplicate": result.is_duplicate},
    )
    await session.commit()
    doc = result.document
    return UploadResponse(
        id=doc.id,
        filename=doc.filename,
        original_name=doc.original_name,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        is_duplicate=result.is_duplicate,
    )


@router.get("/documents/admin/all", response_model=DocumentListResponse, summary="Admin list all documents")
async def list_documents_admin(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_permission("documents.read")),
    session: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    return await _list_documents(session, limit=limit, offset=offset)


@router.get("/documents/", response_model=DocumentListResponse, summary="List documents")
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    return await _list_documents(session, limit=limit, offset=offset)


async def _list_documents(session: AsyncSession, *, limit: int, offset: int) -> DocumentListResponse:
    total = (await session.execute(select(func.count()).select_from(SourceDocument))).scalar_one()
    result = await session.execute(
        select(SourceDocument).order_by(SourceDocument.created_at.desc()).offset(offset).limit(limit)
    )
    docs = result.scalars().all()
    return DocumentListResponse(documents=[DocumentRead.model_validate(d) for d in docs], total=int(total))


@router.get("/documents/{document_id}", response_model=DocumentRead, summary="Get a document")
async def get_document_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentRead:
    doc = await get_document(session, document_id)
    return DocumentRead.model_validate(doc)


@router.delete("/documents/{document_id}", summary="Delete a document")
async def delete_document_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(require_permission("documents.delete")),
    session: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    await delete_document(session, document_id)
    await session.commit()
    return {"success": True}


@router.post(
    "/documents/{document_id}/analyze",
    response_model=DocumentAnalysisRead,
    summary="Analyze a user document for legal issues",
)
async def analyze_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentAnalysis:
    doc = await get_document(session, document_id)
    service = DocumentAnalysisService()
    user_text = await service.read_document_text(doc)

    analysis = DocumentAnalysis(
        user_id=current_user.id,
        document_id=doc.id,
        status="PENDING",
        document_text=user_text or None,
        grounded=False,
    )
    session.add(analysis)
    await session.flush()
    analysis = await service.analyze(session, analysis=analysis)
    await audit_service.record(
        session,
        action="documents.analyze",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="analysis",
        resource_id=str(analysis.id),
        metadata={"document": str(doc.id), "status": analysis.status},
    )
    await session.commit()
    await session.refresh(analysis)
    return analysis


@router.get(
    "/documents/{document_id}/analyses/{analysis_id}",
    response_model=DocumentAnalysisRead,
    summary="Get a document analysis",
)
async def get_analysis(
    document_id: uuid.UUID,
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentAnalysis:
    result = await session.execute(
        select(DocumentAnalysis).where(
            DocumentAnalysis.id == analysis_id,
            DocumentAnalysis.document_id == document_id,
        )
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Analysis not found.")
    return analysis

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.logging import get_logger
from app.database.models.uploaded_file import UploadedFile
from app.database.models.user import User
from app.database.session import get_db
from app.schemas.ingestion import DocumentListItem, DocumentListResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=DocumentListResponse)
async def list_uploaded_files(
    limit: int = 20,
    offset: int = 0,
    file_type: str | None = None,
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_q = select(UploadedFile).where(UploadedFile.user_id == user.id)
    count_q = select(func.count(UploadedFile.id)).where(UploadedFile.user_id == user.id)

    if file_type:
        base_q = base_q.where(UploadedFile.file_type == file_type)
        count_q = count_q.where(UploadedFile.file_type == file_type)
    if status:
        base_q = base_q.where(UploadedFile.status == status)
        count_q = count_q.where(UploadedFile.status == status)

    total = await db.scalar(count_q) or 0

    q = base_q.order_by(UploadedFile.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    files = result.scalars().all()

    return DocumentListResponse(
        total=total,
        documents=[
            DocumentListItem(
                id=f.id,
                filename=f.filename,
                file_size=f.file_size,
                mime_type=f.mime_type,
                file_type=f.file_type,
                status=f.status,
                created_at=f.created_at,
            )
            for f in files
        ],
    )


@router.get("/{doc_id}")
async def get_uploaded_file(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UploadedFile).where(UploadedFile.id == doc_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Document not found")
    if f.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your document")

    content = ""
    fpath = Path(f.file_path)
    if fpath.exists():
        try:
            content = fpath.read_bytes()
        except Exception:
            pass

    return {
        "id": f.id,
        "filename": f.filename,
        "file_size": f.file_size,
        "mime_type": f.mime_type,
        "file_type": f.file_type,
        "status": f.status,
        "content_preview": content[:5000].decode("utf-8", errors="replace") if content else "",
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.delete("/{doc_id}")
async def delete_uploaded_file(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UploadedFile).where(UploadedFile.id == doc_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Document not found")
    if f.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your document")

    fpath = Path(f.file_path)
    if fpath.exists():
        try:
            fpath.unlink()
        except Exception as e:
            logger.warning("file_delete_failed", path=str(fpath), error=str(e))

    from app.database.models.ingestion_job import IngestionJob

    jobs_result = await db.execute(select(IngestionJob).where(IngestionJob.file_id == doc_id))
    for job in jobs_result.scalars().all():
        await db.delete(job)

    from app.database.models.document import Document as Doc

    docs_result = await db.execute(select(Doc).where(Doc.id == doc_id))
    for doc in docs_result.scalars().all():
        await db.delete(doc)

    await db.delete(f)
    await db.commit()

    return {"status": "deleted", "id": doc_id}


@router.get("/admin/all", response_model=DocumentListResponse)
async def admin_list_all_files(
    limit: int = 50,
    offset: int = 0,
    file_type: str | None = None,
    status: str | None = None,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    base_q = select(UploadedFile)
    count_q = select(func.count(UploadedFile.id))

    if file_type:
        base_q = base_q.where(UploadedFile.file_type == file_type)
        count_q = count_q.where(UploadedFile.file_type == file_type)
    if status:
        base_q = base_q.where(UploadedFile.status == status)
        count_q = count_q.where(UploadedFile.status == status)

    total = await db.scalar(count_q) or 0
    q = base_q.order_by(UploadedFile.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    files = result.scalars().all()

    return DocumentListResponse(
        total=total,
        documents=[
            DocumentListItem(
                id=f.id,
                filename=f.filename,
                file_size=f.file_size,
                mime_type=f.mime_type,
                file_type=f.file_type,
                status=f.status,
                created_at=f.created_at,
            )
            for f in files
        ],
    )

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.database.models.uploaded_file import UploadedFile
from app.database.models.user import User
from app.database.session import get_db

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "text/plain": "txt",
    "image/png": "image",
    "image/jpeg": "image",
    "image/tiff": "image",
    "image/bmp": "image",
}


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    max_size = settings.max_upload_size_mb * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.max_upload_size_mb}MB",
        )

    ext = Path(file.filename).suffix.lower()
    mime_type = file.content_type or "application/octet-stream"
    file_type = ALLOWED_MIME_TYPES.get(mime_type, "unknown")

    if file_type == "unknown" and ext in (".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        ext_map = {
            ".pdf": "pdf",
            ".docx": "docx",
            ".doc": "doc",
            ".txt": "txt",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".tiff": "image",
            ".tif": "image",
            ".bmp": "image",
        }
        file_type = ext_map.get(ext, "unknown")

    if file_type == "unknown":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {mime_type}",
        )

    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / safe_name
    file_path.write_bytes(contents)

    db_file = UploadedFile(
        user_id=user.id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(contents),
        mime_type=mime_type,
        file_type=file_type,
        status="uploaded",
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    logger.info("file_uploaded", file_id=db_file.id, filename=file.filename, size=len(contents))

    return {
        "id": db_file.id,
        "filename": db_file.filename,
        "size": db_file.file_size,
        "mime_type": db_file.mime_type,
        "file_type": db_file.file_type,
        "status": db_file.status,
        "created_at": db_file.created_at.isoformat() if db_file.created_at else None,
    }

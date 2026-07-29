from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.logging import get_logger
from app.database.models.ingestion_job import IngestionJob
from app.database.models.uploaded_file import UploadedFile
from app.database.models.user import User
from app.database.session import get_db
from app.ingestion.service import IngestionService
from app.schemas.ingestion import IngestionJobListResponse, IngestionJobResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/ingest/{file_id}", response_model=IngestionJobResponse)
async def ingest_document(
    file_id: str,
    chunk_size: int = 500,
    overlap: int = 50,
    chunk_strategy: str = "recursive",
    collection_name: str = "ingested_docs",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
    uploaded_file = result.scalar_one_or_none()
    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")

    if uploaded_file.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your file")

    service = IngestionService(db_session=db)
    try:
        stats = await service.ingest_file(
            file_id=file_id,
            user_id=user.id,
            chunk_size=chunk_size,
            overlap=overlap,
            chunk_strategy=chunk_strategy,
            collection_name=collection_name,
        )

        result = await db.execute(
            select(IngestionJob).where(IngestionJob.file_id == file_id).order_by(IngestionJob.created_at.desc())
        )
        job = result.scalar_one()

        uploaded_file.status = "ingested"
        await db.commit()

        return IngestionJobResponse(
            id=job.id,
            filename=job.filename,
            doc_type=job.doc_type,
            status=job.status,
            progress=job.progress,
            chunks_count=job.chunks_count,
            stats=stats,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on disk")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("ingestion_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/jobs", response_model=IngestionJobListResponse)
async def list_ingestion_jobs(
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_q = select(func.count(IngestionJob.id)).where(IngestionJob.user_id == user.id)
    total = await db.scalar(total_q) or 0

    q = (
        select(IngestionJob)
        .where(IngestionJob.user_id == user.id)
        .order_by(IngestionJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(q)
    jobs = result.scalars().all()

    return IngestionJobListResponse(
        total=total,
        jobs=[
            IngestionJobResponse(
                id=j.id,
                filename=j.filename,
                doc_type=j.doc_type,
                status=j.status,
                progress=j.progress,
                error_message=j.error_message,
                chunks_count=j.chunks_count,
                stats=j.get_stats(),
                created_at=j.created_at,
                updated_at=j.updated_at,
            )
            for j in jobs
        ],
    )


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your job")

    return IngestionJobResponse(
        id=job.id,
        filename=job.filename,
        doc_type=job.doc_type,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        chunks_count=job.chunks_count,
        stats=job.get_stats(),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/admin/jobs", response_model=IngestionJobListResponse)
async def admin_list_all_jobs(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_q = select(func.count(IngestionJob.id))
    total = await db.scalar(total_q) or 0

    q = select(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    jobs = result.scalars().all()

    return IngestionJobListResponse(
        total=total,
        jobs=[
            IngestionJobResponse(
                id=j.id,
                filename=j.filename,
                doc_type=j.doc_type,
                status=j.status,
                progress=j.progress,
                error_message=j.error_message,
                chunks_count=j.chunks_count,
                stats=j.get_stats(),
                created_at=j.created_at,
                updated_at=j.updated_at,
            )
            for j in jobs
        ],
    )

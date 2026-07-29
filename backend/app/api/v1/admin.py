from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app.api.deps import require_admin
from app.core.logging import get_logger
from app.database.session import async_session_factory

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def admin_stats(user=Depends(require_admin)):
    try:
        async with async_session_factory() as session:
            user_count = await session.scalar(text("SELECT count(*) FROM users"))
            chat_count = await session.scalar(text("SELECT count(*) FROM chats"))
            msg_count = await session.scalar(text("SELECT count(*) FROM messages"))
            doc_count = await session.scalar(text("SELECT count(*) FROM documents"))
            upload_count = await session.scalar(text("SELECT count(*) FROM uploaded_files"))
            job_count = await session.scalar(text("SELECT count(*) FROM ingestion_jobs WHERE status = 'completed'"))
            pending_jobs = await session.scalar(
                text("SELECT count(*) FROM ingestion_jobs WHERE status IN ('pending', 'processing')")
            )
        return {
            "users": user_count or 0,
            "chats": chat_count or 0,
            "messages": msg_count or 0,
            "documents": doc_count or 0,
            "uploads": upload_count or 0,
            "ingested_docs": job_count or 0,
            "pending_ingestions": pending_jobs or 0,
        }
    except Exception as e:
        logger.error("admin_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


@router.get("/audit-logs")
async def get_audit_logs(limit: int = 50, offset: int = 0, user=Depends(require_admin)):
    try:
        from app.database.models.audit_log import AuditLog

        async with async_session_factory() as session:
            from sqlalchemy import func, select

            total = await session.scalar(select(func.count(AuditLog.id)))
            result = await session.execute(
                select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
            )
            logs = result.scalars().all()
            return {
                "total": total or 0,
                "limit": limit,
                "offset": offset,
                "logs": [
                    {
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                        "user_id": log.user_id,
                        "action": log.action,
                        "resource": log.resource,
                        "ip_address": log.ip_address,
                        "status_code": log.status_code,
                        "duration_ms": log.duration_ms,
                    }
                    for log in logs
                ],
            }
    except Exception as e:
        logger.error("admin_audit_logs_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs")

import asyncio

from fastapi import APIRouter

from app.core.cache import get_cache
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.database.session import check_db_health

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


async def _check_redis() -> dict:
    try:
        import redis.asyncio as redis

        settings = get_settings()
        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_neo4j() -> dict:
    try:
        from app.graph.neo4j import Neo4jManager

        manager = Neo4jManager()
        if manager._driver:
            await manager._driver.verify_connectivity()
            return {"status": "healthy"}
        return {"status": "not_configured"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_chroma() -> dict:
    try:
        from app.ingestion.chroma.vector_store import is_healthy

        healthy = is_healthy()
        return {"status": "healthy" if healthy else "unhealthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_ollama() -> dict:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            return {"status": "healthy" if r.status_code == 200 else "unhealthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health")
async def health_check():
    db = await check_db_health()
    return {
        "status": "healthy" if db == "healthy" else "unhealthy",
        "services": {
            "database": db,
        },
    }


@router.get("/health/detailed")
async def health_check_detailed():
    results = await asyncio.gather(
        check_db_health(),
        _check_redis(),
        _check_neo4j(),
        _check_chroma(),
        _check_ollama(),
        return_exceptions=True,
    )
    db = results[0] if not isinstance(results[0], Exception) else "error"
    redis = results[1] if not isinstance(results[1], Exception) else {"status": "unhealthy"}
    neo4j = results[2] if not isinstance(results[2], Exception) else {"status": "unhealthy"}
    chroma = results[3] if not isinstance(results[3], Exception) else {"status": "unhealthy"}
    ollama = results[4] if not isinstance(results[4], Exception) else {"status": "unhealthy"}

    all_healthy = all(
        (s.get("status") if isinstance(s, dict) else s) == "healthy" for s in [db, redis, neo4j, chroma, ollama]
    )
    cache_stats = get_cache().get_stats()

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {
            "database": db,
            "redis": redis,
            "neo4j": neo4j,
            "vector_store": chroma,
            "llm": ollama,
        },
        "cache": cache_stats,
    }


@router.get("/health/liveness")
async def liveness():
    return {"status": "alive"}


@router.get("/health/readiness")
async def readiness():
    db = await check_db_health()
    if db != "healthy":
        return {"status": "not_ready", "reason": "database_unavailable"}
    return {"status": "ready"}


@router.get("/metrics")
async def metrics():
    from app.ai.llms.router import llm_router

    return {
        "llm": llm_router.get_stats(),
    }

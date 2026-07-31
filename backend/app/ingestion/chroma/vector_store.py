import asyncio
import threading
import time

from app.ai.response_modes.local_fallback import OFFLINE_KNOWLEDGE_BASE
from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

_client = None
_collection = None
_lock = threading.Lock()
_last_health_check = 0.0
_health_check_interval = 30.0


def _get_client():
    global _client, _last_health_check
    now = time.time()
    needs_reconnect = False

    with _lock:
        if _client is None:
            needs_reconnect = True
        elif now - _last_health_check > _health_check_interval:
            _last_health_check = now
            try:
                _client.heartbeat()
            except Exception:
                needs_reconnect = True
                _client = None

        if needs_reconnect:
            import chromadb

            _client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                headers={"Authorization": f"Bearer {settings.chroma_token}"},
            )
            logger.info("chroma_client_connected", host=settings.chroma_host, port=settings.chroma_port)

    return _client


async def _run_sync(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


def _sync_initialize():
    client = _get_client()
    global _collection
    try:
        _collection = client.get_collection("bnsai_legal")
    except Exception:
        _collection = client.create_collection("bnsai_legal")

    if _collection.count() == 0:
        for topic_id, entry in OFFLINE_KNOWLEDGE_BASE.items():
            text = f"{entry['title']}. {entry['description']} {entry.get('procedure', '')} {entry.get('citation', '')}"
            _collection.add(
                documents=[text],
                metadatas=[{"topic": topic_id, "title": entry["title"]}],
                ids=[f"legal_{topic_id}"],
            )
        logger.info("vector_store_populated", count=len(OFFLINE_KNOWLEDGE_BASE))


async def initialize_vector_store():
    try:
        await _run_sync(_sync_initialize)
        return True
    except Exception as e:
        logger.warning("vector_store_init_failed", error=str(e))
        return False


def _sync_query(query: str, n_results: int = 3) -> str | None:
    global _client, _collection
    if _collection is None:
        return None
    try:
        results = _collection.query(query_texts=[query], n_results=n_results)
    except Exception:
        _client = None
        _collection = None
        logger.warning("vector_store_query_error_reconnecting")
        return None

    if not results or not results["documents"] or not results["documents"][0]:
        return None
    context = "\n\n".join(results["documents"][0])
    return (
        f"Based on legal knowledge base search:\n\n{context}\n\n"
        "For complete information, please consult a qualified legal professional."
    )


async def query_vector_store(query: str, n_results: int = 3) -> str | None:
    try:
        if _collection is None:
            await initialize_vector_store()
        return await _run_sync(_sync_query, query, n_results)
    except Exception as e:
        logger.warning("vector_store_query_failed", error=str(e))
        return None


def get_collection():
    return _collection


def get_client():
    return _client


def is_healthy() -> bool:
    try:
        client = _get_client()
        client.heartbeat()
        return True
    except Exception:
        return False

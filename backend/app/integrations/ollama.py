import httpx

from app.core.settings import get_settings

settings = get_settings()

_ollama_client: httpx.AsyncClient | None = None
_gemini_client: httpx.AsyncClient | None = None
_chroma_client: httpx.AsyncClient | None = None


def get_ollama_client() -> httpx.AsyncClient:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _ollama_client


def get_gemini_client() -> httpx.AsyncClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _gemini_client


def get_chroma_http_client() -> httpx.AsyncClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = httpx.AsyncClient(
            base_url=f"http://{settings.chroma_host}:{settings.chroma_port}",
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _chroma_client


async def close_http_clients():
    global _ollama_client, _gemini_client, _chroma_client
    for client in [_ollama_client, _gemini_client, _chroma_client]:
        if client is not None:
            await client.aclose()
    _ollama_client = None
    _gemini_client = None
    _chroma_client = None

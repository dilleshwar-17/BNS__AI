import chromadb

from app.core.settings import get_settings

settings = get_settings()

_chroma_client = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            headers={"Authorization": f"Bearer {settings.chroma_token}"},
        )
    return _chroma_client

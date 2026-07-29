from app.integrations.ollama import get_ollama_client
from app.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model

    async def embed(self, text: str) -> list[float]:
        client = get_ollama_client()
        resp = await client.post("/api/embeddings", json={"model": self.model, "prompt": text})
        resp.raise_for_status()
        return resp.json()["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        client = get_ollama_client()
        resp = await client.post("/api/embed", json={"model": self.model, "input": texts})
        resp.raise_for_status()
        return resp.json()["embeddings"]

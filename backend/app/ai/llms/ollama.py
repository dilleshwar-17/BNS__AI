import json
from typing import AsyncGenerator

from app.ai.llms.base import BaseLLM
from app.integrations.ollama import get_ollama_client
from app.logging import get_logger

logger = get_logger(__name__)


class OllamaLLM(BaseLLM):
    def __init__(self, model: str = "mistral"):
        self.model = model

    async def generate(self, prompt: str, **kwargs) -> str:
        client = get_ollama_client()
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        resp = await client.post("/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "")

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        client = get_ollama_client()
        payload = {"model": self.model, "prompt": prompt, "stream": True}
        async with client.stream("POST", "/api/generate", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

    async def is_available(self) -> bool:
        try:
            client = get_ollama_client()
            resp = await client.get("/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

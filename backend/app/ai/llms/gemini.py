import json
from typing import AsyncGenerator

from app.ai.llms.base import BaseLLM
from app.core.settings import get_settings
from app.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class GeminiLLM(BaseLLM):
    def __init__(self):
        self.api_key = settings.gemini_api_key

    async def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            return ""
        import httpx

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidate = data.get("candidates", [{}])[0]
            return candidate.get("content", {}).get("parts", [{}])[0].get("text", "")

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        if not self.api_key:
            return
        import httpx

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?alt=sse&key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            text = (
                                data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            )
                            if text:
                                yield text
                        except json.JSONDecodeError:
                            continue

    async def is_available(self) -> bool:
        return bool(self.api_key)

from app.ai.llms.gemini import GeminiLLM
from app.ai.llms.ollama import OllamaLLM
from app.logging import get_logger

logger = get_logger(__name__)


class LLMHealthCheck:
    def __init__(self):
        self.ollama = OllamaLLM()
        self.gemini = GeminiLLM()

    async def check_all(self) -> dict:
        results = {}
        try:
            results["ollama"] = "healthy" if await self.ollama.is_available() else "unavailable"
        except Exception as e:
            results["ollama"] = f"error: {e}"
        try:
            results["gemini"] = "healthy" if await self.gemini.is_available() else "unavailable"
        except Exception as e:
            results["gemini"] = f"error: {e}"
        return results

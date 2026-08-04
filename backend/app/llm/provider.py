"""LLM provider abstraction.

Phase 8. Provides a common ``LLMProvider`` interface so the orchestration layer
is provider-agnostic. Ollama (local, privacy-preserving) is the default in
development; Gemini is used when a cloud API key is configured. ``ChatStub``
exists for tests and graceful degradation when no model is running.

Only *generation* lives here — legal grounding is enforced elsewhere, so the
LLM is never the sole source of truth (spec: fail-closed, cite-only-verified).
"""

from __future__ import annotations

import abc
import json
import urllib.request
from dataclasses import dataclass
from typing import Optional

from app.core.config import get_settings


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: Optional[dict] = None


class LLMProvider(abc.ABC):
    """Generate assistant text from a message list."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str: ...

    @abc.abstractmethod
    def generate(self, messages: list[LLMMessage], *, max_tokens: int = 1024) -> LLMResponse: ...


class OllamaProvider(LLMProvider):
    """Local generation via an Ollama-compatible HTTP endpoint."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.ollama_model

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, messages: list[LLMMessage], *, max_tokens: int = 1024) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        request = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=settings_ollama_timeout()) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        text = data.get("message", {}).get("content", "").strip()
        return LLMResponse(text=text, model=self._model)


class GeminiProvider(LLMProvider):
    """Cloud generation via the Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        settings = get_settings()
        self._model = model or settings.gemini_model
        self._api_key = api_key or settings.gemini_api_key
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY is required.")

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, messages: list[LLMMessage], *, max_tokens: int = 1024) -> LLMResponse:
        import google.generativeai as genai  # local import, optional dependency

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self._model)
        system = "\n".join(m.content for m in messages if m.role == "system")
        user = messages[-1].content if messages else ""
        prompt = f"{system}\n\n{user}".strip()
        resp = model.generate_content(prompt, generation_config={"max_output_tokens": max_tokens})
        return LLMResponse(text=getattr(resp, "text", "").strip(), model=self._model)


class ChatStubProvider(LLMProvider):
    """Deterministic no-op provider for tests / graceful degradation."""

    def __init__(self, model: str = "stub") -> None:
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, messages: list[LLMMessage], *, max_tokens: int = 1024) -> LLMResponse:
        return LLMResponse(text="[stub] acknowledged", model=self._model)


def settings_ollama_timeout() -> int:
    return 60


def get_llm_provider() -> LLMProvider:
    """Return the configured provider (Ollama default; Gemini if API key)."""
    settings = get_settings()
    if settings.gemini_api_key:
        return GeminiProvider()
    if settings.ollama_base_url:
        return OllamaProvider()
    return ChatStubProvider()

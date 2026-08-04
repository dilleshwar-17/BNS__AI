"""Embedding providers: local (sentence-transformers) and cloud (Gemini).

Abstract interface so the retrieval layer is provider-agnostic.
"""

from __future__ import annotations

import abc
import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, List, Optional

import numpy as np
from app.core.config import get_settings


@dataclass
class EmbeddingResult:
    vectors: np.ndarray  # shape (n, dim)
    model: str
    dim: int


class EmbeddingProvider(abc.ABC):
    """Abstract embedding provider."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str: ...

    @property
    @abc.abstractmethod
    def dimension(self) -> int: ...

    @abc.abstractmethod
    def embed(self, texts: List[str]) -> EmbeddingResult: ...

    def content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embeddings via sentence-transformers (runs on CPU/GPU).

    The underlying SentenceTransformer model is loaded lazily on first use so
    that a cold request does not pay the multi-second model load time.
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        self._model_name = model_name or get_settings().embedding_model
        self._model: Optional[Any] = None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    @property
    def dimension(self) -> int:
        model = self._get_model()
        # sentence-transformers >= 3.0 uses get_embedding_dimension()
        if hasattr(model, "get_embedding_dimension"):
            return model.get_embedding_dimension()
        return model.get_sentence_embedding_dimension()

    def embed(self, texts: List[str]) -> EmbeddingResult:
        model = self._get_model()
        vecs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return EmbeddingResult(vectors=vecs, model=self._model_name, dim=self.dimension)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Cloud embeddings via Google Gemini API."""

    def __init__(self, model: str = "gemini-embedding-001", api_key: Optional[str] = None) -> None:
        import google.generativeai as genai

        self._model_name = model
        self._api_key = api_key or get_settings().gemini_api_key
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        genai.configure(api_key=self._api_key)
        self._genai = genai

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return 768  # gemini-embedding-001 dimension

    def embed(self, texts: List[str]) -> EmbeddingResult:
        # Batch in chunks of 100 (API limit)
        all_vecs: List[List[float]] = []
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            resp = self._genai.embed_content(model=self._model_name, content=batch)
            all_vecs.extend(resp["embedding"])
        vecs = np.array(all_vecs, dtype=np.float32)
        # Normalize
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / np.maximum(norms, 1e-12)
        return EmbeddingResult(vectors=vecs, model=self._model_name, dim=self.dimension)


@lru_cache(maxsize=None)
def _provider() -> EmbeddingProvider:
    """Cached provider factory so the embedding model is loaded once."""
    settings = get_settings()
    if settings.gemini_api_key:
        return GeminiEmbeddingProvider(api_key=settings.gemini_api_key)
    return LocalEmbeddingProvider()


def get_embedding_provider() -> EmbeddingProvider:
    """Factory: returns the shared configured provider (model loaded once)."""
    return _provider()

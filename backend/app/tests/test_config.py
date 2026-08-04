"""Configuration tests."""

from __future__ import annotations

from app.core.config import Settings, get_settings


def test_default_settings() -> None:
    settings = Settings()
    assert settings.api_prefix == "/api/v1"
    assert settings.environment in {"development", "testing", "staging", "production"}
    assert settings.rag_top_k >= settings.rag_rerank_top_k


def test_get_settings_is_singleton() -> None:
    assert get_settings() is get_settings()


def test_cors_origins_parses_csv(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS_CSV", "http://a.com, http://b.com")
    settings = Settings()
    assert settings.cors_origins == ["http://a.com", "http://b.com"]

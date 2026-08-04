"""Centralized application configuration.

All environment variables are read here via pydantic-settings. Business logic
must never read ``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "testing", "staging", "production"]

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application -------------------------------------------------------
    app_name: str = "BNS AI"
    app_version: str = "1.0.0"
    environment: Environment = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # --- Database ----------------------------------------------------------
    database_url: str = "postgresql+asyncpg://bnsai:bnsai_secret@localhost:5432/bnsai"
    pool_size: int = 50
    max_overflow: int = 100
    pool_pre_ping: bool = True

    # --- Redis -------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # --- Storage -----------------------------------------------------------
    storage_dir: Path = BACKEND_DIR / "data" / "uploads"

    # --- Neo4j -------------------------------------------------------------
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "bnsai_neo4j"

    # --- ChromaDB ----------------------------------------------------------
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_token: str | None = None

    # --- Ollama ------------------------------------------------------------
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    # --- Gemini ------------------------------------------------------------
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"

    # --- Embeddings --------------------------------------------------------
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # --- JWT ---------------------------------------------------------------
    secret_key: str = "change_me_generate_with_openssl_rand_base64_32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Security ----------------------------------------------------------
    cors_origins_csv: str = "http://localhost:5173,http://localhost:8080"
    rate_limit_default: int = 120
    rate_limit_window_seconds: int = 60

    # --- RAG ---------------------------------------------------------------
    rag_top_k: int = 20
    rag_rerank_top_k: int = 6
    rag_min_score: float = 0.60
    rag_lexical_enabled: bool = True
    rag_semantic_enabled: bool = True
    rag_graph_enabled: bool = True

    # --- Agents ------------------------------------------------------------
    max_agent_steps: int = 5
    max_retrieval_rounds: int = 2
    agent_timeout_seconds: float = 30.0

    # --- Conversation memory (Phase 13) ------------------------------------
    memory_recent_window: int = 6

    # --- Legal research (Phase 16) -----------------------------------------
    research_max_subqueries: int = 5
    research_max_evidence: int = 15

    # --- Document analysis (Phase 17) --------------------------------------
    analysis_max_issues: int = 8

    # --- Logging -----------------------------------------------------------
    log_level: str = "INFO"

    # --- Voice -------------------------------------------------------------
    stt_provider: str = "none"
    tts_provider: str = "none"

    # --- Caching -----------------------------------------------------------
    llm_cache_ttl: int = 300
    vector_cache_ttl: int = 600

    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower()
        return v

    @property
    def cors_origins(self) -> list[str]:
        """Parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.cors_origins_csv.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()

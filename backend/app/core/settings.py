import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    neo4j_uri: Optional[str] = None
    neo4j_user: Optional[str] = None
    neo4j_password: Optional[str] = None
    chroma_host: Optional[str] = None
    chroma_port: int = 8000
    chroma_token: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:3000/auth/callback/google"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    csp_policy: str = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:;"
    rate_limit_per_minute: int = 300
    max_upload_size_mb: int = 10
    trusted_hosts: str = "localhost,127.0.0.1"
    pool_size: int = 5
    max_overflow: int = 10
    pool_pre_ping: bool = True
    log_level: str = "INFO"
    environment: str = "development"

    @property
    def jwt_algorithm(self) -> str:
        return self.algorithm

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def trusted_hosts_list(self) -> list[str]:
        if not self.trusted_hosts:
            return []
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        try:
            _settings = Settings()
        except Exception:
            _settings = Settings(
                database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bnsai_test.db"),
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
            )
    return _settings

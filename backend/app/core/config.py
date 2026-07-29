from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://bnsai:bnsai_secret@localhost:5432/bnsai"
    redis_url: str = "redis://localhost:6379/0"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "bnsai_neo4j"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_token: str = "bnsai_chroma"
    ollama_base_url: str = "http://localhost:11434"
    gemini_api_key: str = ""
    secret_key: str = "bnsai_secret_key_change_in_production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    log_level: str = "INFO"
    llm_cache_ttl: int = 300
    vector_cache_ttl: int = 600
    pool_size: int = 10
    max_overflow: int = 20
    pool_pre_ping: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()

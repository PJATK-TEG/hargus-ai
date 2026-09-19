from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so it works regardless of CWD
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HARGUS_",
        env_file=str(_ENV_FILE),
        extra="ignore",
    )

    # Application
    app_name: str = "Hargus AI API"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    frontend_origin: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://hargus:hargus@localhost:5432/hargus"

    # Temporal
    temporal_enabled: bool = False
    temporal_server_url: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "hargus-ai"

    @field_validator("temporal_server_url")
    @classmethod
    def validate_temporal_server_url(cls, value: str) -> str:
        host, separator, port = value.rpartition(":")
        if not separator or not host or not port.isdigit():
            raise ValueError("temporal_server_url must be in host:port format")
        port_number = int(port)
        if port_number < 1 or port_number > 65535:
            raise ValueError("temporal_server_url port must be between 1 and 65535")
        return value

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # Storage
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_path: str = "./data/files"
    s3_bucket: str = ""
    s3_prefix: str = ""
    s3_endpoint_url: str = ""
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # LLM
    llm_provider: Literal["ollama", "openai", "anthropic", "bedrock"] = "ollama"
    llm_model: str = "llama3.1"
    llm_temperature: float = 0.1

    # Embeddings
    embedding_provider: Literal["ollama", "openai", "bedrock"] = "ollama"
    embedding_model: str = "nomic-embed-text"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = ""  # override for OpenAI-compatible endpoints (e.g. OpenRouter)

    # Anthropic
    anthropic_api_key: str = ""

    # Langfuse
    langfuse_enabled: bool = False
    langfuse_host: str = "http://localhost:3001"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

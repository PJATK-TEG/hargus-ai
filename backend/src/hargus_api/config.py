from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HARGUS_", env_file=".env", extra="ignore")

    app_name: str = "Hargus AI API"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    frontend_origin: str = "http://localhost:3000"
    database_url: str | None = None

    temporal_enabled: bool = False
    temporal_server_url: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "hargus-ai"

    @field_validator("temporal_server_url")
    @classmethod
    def validate_temporal_server_url(cls, value: str) -> str:
        # Temporal Python SDK expects host:port format.
        host, separator, port = value.rpartition(":")
        if not separator or not host or not port.isdigit():
            raise ValueError("temporal_server_url must be in host:port format")
        port_number = int(port)
        if port_number < 1 or port_number > 65535:
            raise ValueError("temporal_server_url port must be between 1 and 65535")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

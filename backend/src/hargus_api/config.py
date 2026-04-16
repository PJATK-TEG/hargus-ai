from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HARGUS_", env_file=".env", extra="ignore")

    app_name: str = "Hargus AI API"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    frontend_origin: str = "http://localhost:3000"

    temporal_enabled: bool = False
    temporal_server_url: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "hargus-ai"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

from fastapi import APIRouter

from hargus_api.config import get_settings
from hargus_api.schemas.domain import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
        temporalEnabled=settings.temporal_enabled,
    )

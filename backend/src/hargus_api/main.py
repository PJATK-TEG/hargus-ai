from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hargus_api.api.routes.ai_tasks import router as ai_tasks_router
from hargus_api.api.routes.candidates import router as candidates_router
from hargus_api.api.routes.health import router as health_router
from hargus_api.api.routes.vacancies import router as vacancies_router
from hargus_api.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend scaffold for Hargus AI with Temporal-backed AI task stubs.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(vacancies_router, prefix=settings.api_prefix)
app.include_router(candidates_router, prefix=settings.api_prefix)
app.include_router(ai_tasks_router, prefix=settings.api_prefix)

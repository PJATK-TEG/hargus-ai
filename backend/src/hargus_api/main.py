import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from hargus_api.api.routes.ai_tasks import router as ai_tasks_router
from hargus_api.api.routes.background import router as background_router
from hargus_api.api.routes.candidates import router as candidates_router
from hargus_api.api.routes.health import router as health_router
from hargus_api.api.routes.vacancies import router as vacancies_router
from hargus_api.config import get_settings

settings = get_settings()
logger = logging.getLogger("hargus_api.request")

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


@app.middleware("http")
async def request_context_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()

    response = await call_next(request)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(vacancies_router, prefix=settings.api_prefix)
app.include_router(candidates_router, prefix=settings.api_prefix)
app.include_router(ai_tasks_router, prefix=settings.api_prefix)
app.include_router(background_router, prefix=settings.api_prefix)

from fastapi import APIRouter, Depends, HTTPException

from hargus_api.api.dependencies import get_current_user
from hargus_api.config import Settings, get_settings
from hargus_api.db.models import User
from hargus_api.schemas.domain import (
    AiTaskRecord,
    AiTaskRequest,
    BackgroundCheckRequest,
    BackgroundSource,
    BackgroundSourceInfo,
    BackgroundSourceListResponse,
    BackgroundSourceSearchRequest,
)
from hargus_api.services.ai_task_service import AiTaskService

router = APIRouter(prefix="/background", tags=["background"])

_SOURCE_CATALOG: list[BackgroundSourceInfo] = [
    BackgroundSourceInfo(
        id="courtlistener",
        name="CourtListener API",
        category="legal",
        requiresApiKey=False,
    ),
    BackgroundSourceInfo(
        id="recap",
        name="RECAP Archive",
        category="legal",
        requiresApiKey=False,
    ),
    BackgroundSourceInfo(
        id="fbi_cde",
        name="FBI Crime Data Explorer",
        category="legal",
        requiresApiKey=False,
    ),
    BackgroundSourceInfo(
        id="openalex",
        name="OpenAlex API",
        category="scholarly",
        requiresApiKey=False,
    ),
    BackgroundSourceInfo(
        id="crossref",
        name="Crossref REST API",
        category="scholarly",
        requiresApiKey=False,
    ),
    BackgroundSourceInfo(
        id="orcid",
        name="ORCID Public API",
        category="scholarly",
        requiresApiKey=False,
    ),
    BackgroundSourceInfo(
        id="wos",
        name="Web of Science Starter API",
        category="scholarly",
        requiresApiKey=True,
    ),
]


def get_ai_task_service(settings: Settings = Depends(get_settings)) -> AiTaskService:  # noqa: B008
    return AiTaskService(settings)


@router.get("/sources", response_model=BackgroundSourceListResponse)
async def list_background_sources(
    _: User = Depends(get_current_user),  # noqa: B008
) -> BackgroundSourceListResponse:
    return BackgroundSourceListResponse(items=_SOURCE_CATALOG)


@router.get("/checks", response_model=list[AiTaskRecord])
async def list_background_checks(
    service: AiTaskService = Depends(get_ai_task_service),  # noqa: B008
    _: User = Depends(get_current_user),  # noqa: B008
) -> list[AiTaskRecord]:
    return [
        task for task in service.list_tasks() if task.type == "candidate_background_check"
    ]


@router.post("/checks", response_model=AiTaskRecord, status_code=202)
async def submit_background_check(
    request: BackgroundCheckRequest,
    service: AiTaskService = Depends(get_ai_task_service),  # noqa: B008
    _: User = Depends(get_current_user),  # noqa: B008
) -> AiTaskRecord:
    sources = ", ".join(request.sources) if request.sources else "auto"
    prompt = request.prompt or f"Run background check using sources: {sources}"
    ai_task_request = AiTaskRequest(
        type="candidate_background_check",
        candidateId=request.candidate_id,
        candidateIds=request.candidate_ids,
        vacancyId=request.vacancy_id,
        prompt=prompt,
    )
    return await service.submit_task(ai_task_request)


@router.get("/checks/{task_id}", response_model=AiTaskRecord)
async def get_background_check(
    task_id: str,
    service: AiTaskService = Depends(get_ai_task_service),  # noqa: B008
    _: User = Depends(get_current_user),  # noqa: B008
) -> AiTaskRecord:
    task = service.get_task(task_id)
    if task is None or task.type != "candidate_background_check":
        raise HTTPException(status_code=404, detail="Background check task not found")
    return task


@router.post("/sources/{source}/search", response_model=AiTaskRecord, status_code=202)
async def search_background_source(
    source: BackgroundSource,
    request: BackgroundSourceSearchRequest,
    service: AiTaskService = Depends(get_ai_task_service),  # noqa: B008
    _: User = Depends(get_current_user),  # noqa: B008
) -> AiTaskRecord:
    ai_task_request = AiTaskRequest(
        type="candidate_background_check",
        candidateId=request.candidate_id,
        candidateIds=request.candidate_ids,
        vacancyId=request.vacancy_id,
        prompt=f"Search source={source} with query: {request.query}",
    )
    return await service.submit_task(ai_task_request)

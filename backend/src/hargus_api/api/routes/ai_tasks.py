from fastapi import APIRouter, Depends, HTTPException

from hargus_api.config import Settings, get_settings
from hargus_api.schemas.domain import AiTaskRecord, AiTaskRequest
from hargus_api.services.ai_task_service import AiTaskService

router = APIRouter(prefix="/ai/tasks", tags=["ai"])


def get_ai_task_service(settings: Settings = Depends(get_settings)) -> AiTaskService:  # noqa: B008
    return AiTaskService(settings)


@router.get("", response_model=list[AiTaskRecord])
async def list_ai_tasks(
    service: AiTaskService = Depends(get_ai_task_service),  # noqa: B008
) -> list[AiTaskRecord]:
    return service.list_tasks()


@router.post("", response_model=AiTaskRecord, status_code=202)
async def submit_ai_task(
    request: AiTaskRequest,
    service: AiTaskService = Depends(get_ai_task_service),  # noqa: B008
) -> AiTaskRecord:
    return await service.submit_task(request)


@router.get("/{task_id}", response_model=AiTaskRecord)
async def get_ai_task(
    task_id: str,
    service: AiTaskService = Depends(get_ai_task_service),  # noqa: B008
) -> AiTaskRecord:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="AI task not found")
    return task

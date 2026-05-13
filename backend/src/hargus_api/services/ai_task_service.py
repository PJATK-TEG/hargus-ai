from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from hargus_api.ai.config import get_analysis_prompt
from hargus_api.config import Settings
from hargus_api.db.base import AsyncSessionLocal
from hargus_api.db.repositories.ai_task_repo import AsyncAiTaskRepository
from hargus_api.db.repositories.workflow_run_repo import WorkflowRunRepository
from hargus_api.schemas.domain import AiTaskRecord, AiTaskRequest
from hargus_api.temporal.client import create_temporal_client
from hargus_api.temporal.models import AnalysisWorkflowInput

logger = logging.getLogger(__name__)

_temporal_client = None


async def _get_temporal_client(settings: Settings):
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = await create_temporal_client(settings)
    return _temporal_client


class AiTaskService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def list_tasks(self) -> list[AiTaskRecord]:
        async with AsyncSessionLocal() as session:
            repo = AsyncAiTaskRepository(session)
            return await repo.list_tasks()

    async def get_task(self, task_id: str) -> AiTaskRecord | None:
        async with AsyncSessionLocal() as session:
            repo = AsyncAiTaskRepository(session)
            return await repo.get_task(task_id)

    async def submit_task(self, request: AiTaskRequest) -> AiTaskRecord:
        resolved_prompt = request.prompt.strip() or get_analysis_prompt()

        now = datetime.now(UTC)
        task_id = str(uuid4())
        workflow_id = f"analysis-{task_id}"

        record = AiTaskRecord(
            id=task_id,
            type=request.type,
            status="queued",
            prompt=resolved_prompt,
            candidateId=request.candidate_id,
            candidateIds=request.candidate_ids,
            vacancyId=request.vacancy_id,
            workflowId=workflow_id,
            createdAt=now,
            updatedAt=now,
        )

        async with AsyncSessionLocal() as session:
            repo = AsyncAiTaskRepository(session)
            await repo.save_task(record)
            await session.commit()

        if self.settings.temporal_enabled:
            await _create_workflow_run_record(
                temporal_workflow_id=workflow_id,
                candidate_id=request.candidate_id or "",
                vacancy_id=request.vacancy_id or "",
                task_type=request.type,
            )

            client = await _get_temporal_client(self.settings)
            wf_input = AnalysisWorkflowInput(
                workflow_run_id=workflow_id,
                candidate_id=request.candidate_id or "",
                vacancy_id=request.vacancy_id or "",
                task_type=request.type,
                analysis_prompt=resolved_prompt,
            )
            await client.start_workflow(
                "CandidateAnalysisWorkflow",
                wf_input,
                id=workflow_id,
                task_queue=self.settings.temporal_task_queue,
            )
            logger.info("Started Temporal workflow %s for candidate %s", workflow_id, request.candidate_id)
            record = record.model_copy(update={"status": "running", "provider": "temporal"})
            async with AsyncSessionLocal() as session:
                repo = AsyncAiTaskRepository(session)
                await repo.save_task(record)
                await session.commit()

        return record


async def _create_workflow_run_record(
    temporal_workflow_id: str,
    candidate_id: str,
    vacancy_id: str,
    task_type: str,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            repo = WorkflowRunRepository(session)
            await repo.create(
                candidate_id=candidate_id,
                vacancy_id=vacancy_id,
                temporal_workflow_id=temporal_workflow_id,
                task_type=task_type,
            )
            await session.commit()
    except Exception:
        logger.warning(
            "Could not create WorkflowRun DB record for workflow %s — "
            "store_and_notify_activity may fail at the end of the run",
            temporal_workflow_id,
        )

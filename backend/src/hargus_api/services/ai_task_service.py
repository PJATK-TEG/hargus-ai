from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from hargus_api.config import Settings
from hargus_api.repositories.ai_task_repository import (
    InMemoryAiTaskRepository,
    PostgresAiTaskRepository,
)
from hargus_api.schemas.domain import AiTaskRecord, AiTaskRequest
from hargus_api.temporal.client import create_temporal_client
from hargus_api.temporal.workflows.ai_tasks import AiTaskWorkflow

_IN_MEMORY_REPOSITORY = InMemoryAiTaskRepository()
_POSTGRES_REPOSITORIES: dict[str, PostgresAiTaskRepository] = {}


class AiTaskService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if settings.database_url:
            if settings.database_url not in _POSTGRES_REPOSITORIES:
                _POSTGRES_REPOSITORIES[settings.database_url] = PostgresAiTaskRepository(
                    settings.database_url
                )
            self.repository = _POSTGRES_REPOSITORIES[settings.database_url]
        else:
            self.repository = _IN_MEMORY_REPOSITORY

    def list_tasks(self) -> list[AiTaskRecord]:
        return self.repository.list_tasks()

    def get_task(self, task_id: str) -> AiTaskRecord | None:
        return self.repository.get_task(task_id)

    async def submit_task(self, request: AiTaskRequest) -> AiTaskRecord:
        now = datetime.now(UTC)
        task_id = str(uuid4())
        workflow_id = f"ai-task-{task_id}"

        record = AiTaskRecord(
            id=task_id,
            type=request.type,
            status="queued",
            prompt=request.prompt,
            candidateId=request.candidate_id,
            candidateIds=request.candidate_ids,
            vacancyId=request.vacancy_id,
            workflowId=workflow_id,
            createdAt=now,
            updatedAt=now,
            result={
                "message": (
                    "Queued in stub mode. Connect your real Temporal flow to replace "
                    "this placeholder."
                ),
            },
        )
        self.repository.save_task(record)

        if self.settings.temporal_enabled:
            client = await create_temporal_client(self.settings)
            await client.start_workflow(
                AiTaskWorkflow.run,
                request,
                id=workflow_id,
                task_queue=self.settings.temporal_task_queue,
            )

        return record

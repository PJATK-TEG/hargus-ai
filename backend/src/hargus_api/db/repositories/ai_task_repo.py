from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.models import AiTask
from hargus_api.schemas.domain import AiTaskRecord


class AsyncAiTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_tasks(self) -> list[AiTaskRecord]:
        result = await self._session.execute(
            select(AiTask).order_by(AiTask.created_at.desc())
        )
        return [_to_record(row) for row in result.scalars().all()]

    async def get_task(self, task_id: str) -> AiTaskRecord | None:
        obj = await self._session.get(AiTask, task_id)
        return _to_record(obj) if obj is not None else None

    async def save_task(self, record: AiTaskRecord) -> None:
        stmt = (
            insert(AiTask)
            .values(
                id=record.id,
                type=record.type,
                status=record.status,
                prompt=record.prompt,
                candidate_id=record.candidate_id,
                candidate_ids=record.candidate_ids,
                vacancy_id=record.vacancy_id,
                provider=record.provider,
                workflow_id=record.workflow_id,
                created_at=record.created_at,
                updated_at=record.updated_at,
                result=record.result,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "status": record.status,
                    "updated_at": record.updated_at,
                    "result": record.result,
                    "workflow_id": record.workflow_id,
                    "provider": record.provider,
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()


def _to_record(obj: AiTask) -> AiTaskRecord:
    return AiTaskRecord(
        id=obj.id,
        type=obj.type,
        status=obj.status,
        prompt=obj.prompt,
        candidateId=obj.candidate_id,
        candidateIds=obj.candidate_ids or [],
        vacancyId=obj.vacancy_id,
        provider=obj.provider,
        workflowId=obj.workflow_id,
        createdAt=obj.created_at,
        updatedAt=obj.updated_at,
        result=obj.result,
    )

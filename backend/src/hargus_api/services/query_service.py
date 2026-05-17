from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from hargus_api.config import Settings, get_settings
from hargus_api.db.base import AsyncSessionLocal
from hargus_api.db.repositories.workflow_run_repo import WorkflowRunRepository
from hargus_api.services.message_service import save_message
from hargus_api.repositories.ai_task_repository import (
    PostgresAiTaskRepository,
    normalize_postgres_url,
)
from hargus_api.schemas.domain import AiTaskRecord
from hargus_api.temporal.client import create_temporal_client
from hargus_api.temporal.models import CandidateQueryInput

logger = logging.getLogger(__name__)

_POSTGRES_REPOSITORIES: dict[str, PostgresAiTaskRepository] = {}
_temporal_client = None


async def _get_temporal_client(settings: Settings):
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = await create_temporal_client(settings)
    return _temporal_client


def get_query_repository(settings: Settings) -> PostgresAiTaskRepository:
    psycopg_url = normalize_postgres_url(settings.database_url)
    if psycopg_url not in _POSTGRES_REPOSITORIES:
        _POSTGRES_REPOSITORIES[psycopg_url] = PostgresAiTaskRepository(psycopg_url)
    return _POSTGRES_REPOSITORIES[psycopg_url]


async def submit_candidate_query(
    candidate_id: str,
    vacancy_id: str,
    query: str,
) -> AiTaskRecord:
    settings = get_settings()
    repository = get_query_repository(settings)

    now = datetime.now(UTC)
    task_id = str(uuid4())
    workflow_id = f"query-{task_id}"

    record = AiTaskRecord(
        id=task_id,
        type="candidate_query",
        status="queued",
        prompt=query,
        candidateId=candidate_id,
        candidateIds=[],
        vacancyId=vacancy_id or None,
        workflowId=workflow_id,
        createdAt=now,
        updatedAt=now,
    )
    repository.save_task(record)

    await _save_user_message(candidate_id, query)

    if settings.temporal_enabled:
        await _create_workflow_run_record(
            temporal_workflow_id=workflow_id,
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
        )
        client = await _get_temporal_client(settings)
        wf_input = CandidateQueryInput(
            workflow_run_id=workflow_id,
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
            query=query,
        )
        await client.start_workflow(
            "CandidateQueryWorkflow",
            wf_input,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        logger.info("Started CandidateQueryWorkflow %s for candidate %s", workflow_id, candidate_id)
        record = record.model_copy(update={"status": "running", "provider": "temporal"})
        repository.save_task(record)

    return record


async def _save_user_message(candidate_id: str, content: str) -> None:
    try:
        async with AsyncSessionLocal() as session:
            await save_message(session, candidate_id, "user", content)
            await session.commit()
    except Exception:
        logger.warning("Could not save user message for candidate %s", candidate_id)


async def _create_workflow_run_record(
    temporal_workflow_id: str,
    candidate_id: str,
    vacancy_id: str,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            repo = WorkflowRunRepository(session)
            await repo.create(
                candidate_id=candidate_id,
                vacancy_id=vacancy_id,
                temporal_workflow_id=temporal_workflow_id,
                task_type="candidate_query",
            )
            await session.commit()
    except Exception:
        logger.warning(
            "Could not create WorkflowRun DB record for query workflow %s",
            temporal_workflow_id,
        )

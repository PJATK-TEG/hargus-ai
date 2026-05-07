from __future__ import annotations

import json
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

from hargus_api.schemas.domain import AiTaskRecord


def normalize_postgres_url(database_url: str) -> str:
    return database_url.replace("+asyncpg", "").replace("+psycopg2", "")


class InMemoryAiTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, AiTaskRecord] = {}

    def list_tasks(self) -> list[AiTaskRecord]:
        return list(self._tasks.values())

    def get_task(self, task_id: str) -> AiTaskRecord | None:
        return self._tasks.get(task_id)

    def save_task(self, task: AiTaskRecord) -> None:
        self._tasks[task.id] = task


class PostgresAiTaskRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._ensure_schema()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ai_tasks (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        prompt TEXT NOT NULL,
                        candidate_id TEXT NULL,
                        candidate_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                        vacancy_id TEXT NULL,
                        provider TEXT NOT NULL,
                        workflow_id TEXT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL,
                        result JSONB NULL
                    )
                    """
                )
            conn.commit()

    def list_tasks(self) -> list[AiTaskRecord]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM ai_tasks ORDER BY created_at DESC")
                rows = cur.fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_task(self, task_id: str) -> AiTaskRecord | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM ai_tasks WHERE id = %s", (task_id,))
                row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    def save_task(self, task: AiTaskRecord) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ai_tasks (
                        id,
                        type,
                        status,
                        prompt,
                        candidate_id,
                        candidate_ids,
                        vacancy_id,
                        provider,
                        workflow_id,
                        created_at,
                        updated_at,
                        result
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at,
                        result = EXCLUDED.result
                    """,
                    (
                        task.id,
                        task.type,
                        task.status,
                        task.prompt,
                        task.candidate_id,
                        json.dumps(task.candidate_ids),
                        task.vacancy_id,
                        task.provider,
                        task.workflow_id,
                        task.created_at,
                        task.updated_at,
                        json.dumps(task.result) if task.result is not None else None,
                    ),
                )
            conn.commit()

    @staticmethod
    def _row_to_task(row: dict) -> AiTaskRecord:
        candidate_ids = row["candidate_ids"] or []
        result = row["result"]
        return AiTaskRecord(
            id=row["id"],
            type=row["type"],
            status=row["status"],
            prompt=row["prompt"],
            candidateId=row["candidate_id"],
            candidateIds=candidate_ids,
            vacancyId=row["vacancy_id"],
            provider=row["provider"],
            workflowId=row["workflow_id"],
            createdAt=_to_datetime(row["created_at"]),
            updatedAt=_to_datetime(row["updated_at"]),
            result=result,
        )


def _to_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)

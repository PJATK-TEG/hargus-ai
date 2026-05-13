"""Track ai_tasks in Alembic and add storage_key to candidate_files

Revision ID: f1a2b3c4d5e6
Revises: 0384569732a1
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "0384569732a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ai_tasks may already exist (created at runtime by the old _ensure_schema).
    # Using CREATE TABLE IF NOT EXISTS makes this safe to run on both fresh and
    # existing databases.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_tasks (
            id          TEXT PRIMARY KEY,
            type        TEXT NOT NULL,
            status      TEXT NOT NULL,
            prompt      TEXT NOT NULL,
            candidate_id TEXT NULL,
            candidate_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            vacancy_id  TEXT NULL,
            provider    TEXT NOT NULL,
            workflow_id TEXT NULL,
            created_at  TIMESTAMPTZ NOT NULL,
            updated_at  TIMESTAMPTZ NOT NULL,
            result      JSONB NULL
        )
        """
    )

    op.add_column(
        "candidate_files",
        sa.Column("storage_key", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidate_files", "storage_key")
    op.drop_table("ai_tasks")

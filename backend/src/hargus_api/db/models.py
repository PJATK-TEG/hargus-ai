from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hargus_api.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    vacancy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    temporal_workflow_id: Mapped[str] = mapped_column(
        String(256), nullable=False, unique=True
    )
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    report: Mapped[AnalysisReport | None] = relationship(
        "AnalysisReport", back_populates="workflow_run", uselist=False
    )


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id"), nullable=False
    )
    candidate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    vacancy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    skill_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False)
    report_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    pdf_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    workflow_run: Mapped[WorkflowRun] = relationship(
        "WorkflowRun", back_populates="report"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(256), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # nomic-embed-text produces 768-dim vectors; adjust if switching models
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

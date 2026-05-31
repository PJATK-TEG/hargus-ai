from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.models import AnalysisReport, WorkflowRun



class WorkflowRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        candidate_id: str,
        vacancy_id: str,
        temporal_workflow_id: str,
        task_type: str,
    ) -> WorkflowRun:
        run = WorkflowRun(
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
            temporal_workflow_id=temporal_workflow_id,
            task_type=task_type,
            status="pending",
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def get_by_workflow_id(self, temporal_workflow_id: str) -> WorkflowRun | None:
        result = await self._session.execute(
            select(WorkflowRun).where(
                WorkflowRun.temporal_workflow_id == temporal_workflow_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, run_id: uuid.UUID) -> WorkflowRun | None:
        return await self._session.get(WorkflowRun, run_id)

    async def set_running(self, run_id: uuid.UUID) -> None:
        run = await self._session.get(WorkflowRun, run_id)
        if run:
            run.status = "running"

    async def set_completed(self, run_id: uuid.UUID) -> None:
        run = await self._session.get(WorkflowRun, run_id)
        if run:
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)

    async def set_failed(self, run_id: uuid.UUID, error: str) -> None:
        run = await self._session.get(WorkflowRun, run_id)
        if run:
            run.status = "failed"
            run.error_message = error
            run.completed_at = datetime.now(timezone.utc)

    async def save_report(
        self,
        workflow_run_id: uuid.UUID,
        candidate_id: str,
        vacancy_id: str,
        score_data: dict,
        report_snapshot: dict,
        pdf_storage_key: str | None,
    ) -> AnalysisReport:
        report = AnalysisReport(
            workflow_run_id=workflow_run_id,
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
            overall_score=score_data["overall_score"],
            skill_match_score=score_data["skill_match_score"],
            experience_score=score_data["experience_score"],
            risk_penalty=score_data.get("risk_penalty", 0.0),
            recommendation=score_data["recommendation"],
            report_snapshot=report_snapshot,
            pdf_storage_key=pdf_storage_key,
        )
        self._session.add(report)
        await self._session.flush()
        return report

    async def list_reports_by_candidate(self, candidate_id: str) -> list[AnalysisReport]:
        result = await self._session.execute(
            select(AnalysisReport)
            .where(AnalysisReport.candidate_id == candidate_id)
            .order_by(AnalysisReport.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_report_by_id(self, report_id: uuid.UUID) -> AnalysisReport | None:
        return await self._session.get(AnalysisReport, report_id)

    async def delete_report(self, candidate_id: str, report_id: uuid.UUID) -> bool:
        report = await self._session.get(AnalysisReport, report_id)
        if report is None or report.candidate_id != candidate_id:
            return False
        await self._session.delete(report)
        await self._session.flush()
        return True

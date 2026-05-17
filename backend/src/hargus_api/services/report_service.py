from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.repositories.workflow_run_repo import WorkflowRunRepository
from hargus_api.schemas.domain import AnalysisReportResponse
from hargus_api.storage.factory import get_storage


async def list_reports_by_candidate(
    session: AsyncSession, candidate_id: str
) -> list[AnalysisReportResponse]:
    repo = WorkflowRunRepository(session)
    reports = await repo.list_reports_by_candidate(candidate_id)
    return [
        AnalysisReportResponse(
            id=str(r.id),
            candidateId=r.candidate_id,
            vacancyId=r.vacancy_id,
            overallScore=r.overall_score,
            skillMatchScore=r.skill_match_score,
            experienceScore=r.experience_score,
            recommendation=r.recommendation,
            hasPdf=r.pdf_storage_key is not None,
            createdAt=r.created_at,
        )
        for r in reports
    ]


async def get_report_pdf(
    session: AsyncSession, candidate_id: str, report_id: uuid.UUID
) -> bytes:
    repo = WorkflowRunRepository(session)
    report = await repo.get_report_by_id(report_id)

    if report is None or report.candidate_id != candidate_id:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.pdf_storage_key:
        raise HTTPException(status_code=404, detail="PDF not available for this report")

    storage = get_storage()
    return await storage.download(report.pdf_storage_key)

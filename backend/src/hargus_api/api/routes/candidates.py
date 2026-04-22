import uuid

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from hargus_api.db.base import AsyncSessionLocal
from hargus_api.db.repositories.workflow_run_repo import WorkflowRunRepository
from hargus_api.schemas.domain import (
    AnalysisReportResponse,
    Candidate,
    CandidateListResponse,
    MessageListResponse,
    PaginationMeta,
)
from hargus_api.services.candidate_service import (
    get_candidate,
    get_candidate_messages,
    list_candidates_paginated,
)
from hargus_api.storage.factory import get_storage

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListResponse)
async def get_candidates(
    vacancy_id: str | None = Query(default=None, alias="vacancyId"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CandidateListResponse:
    items, total = list_candidates_paginated(vacancy_id=vacancy_id, limit=limit, offset=offset)
    return CandidateListResponse(
        items=items,
        meta=PaginationMeta(total=total, limit=limit, offset=offset, returned=len(items)),
    )


@router.get("/{candidate_id}", response_model=Candidate)
async def get_candidate_by_id(candidate_id: str) -> Candidate:
    candidate = get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.get("/{candidate_id}/reports", response_model=list[AnalysisReportResponse])
async def list_reports(candidate_id: str) -> list[AnalysisReportResponse]:
    async with AsyncSessionLocal() as session:
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


@router.get("/{candidate_id}/reports/{report_id}/pdf")
async def get_report_pdf(candidate_id: str, report_id: str) -> Response:
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID")

    async with AsyncSessionLocal() as session:
        repo = WorkflowRunRepository(session)
        report = await repo.get_report_by_id(rid)

    if report is None or report.candidate_id != candidate_id:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.pdf_storage_key:
        raise HTTPException(status_code=404, detail="PDF not available for this report")

    storage = get_storage()
    pdf_bytes = await storage.download(report.pdf_storage_key)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="report-{report_id[:8]}.pdf"'},
    )


@router.get("/{candidate_id}/messages", response_model=MessageListResponse)
async def get_messages(candidate_id: str) -> MessageListResponse:
    candidate = get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    items = get_candidate_messages(candidate_id)
    return MessageListResponse(
        items=items,
        meta=PaginationMeta(total=len(items), limit=len(items), offset=0, returned=len(items)),
    )

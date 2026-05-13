import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.base import get_db_session
from hargus_api.db.repositories.document_chunk_repo import DocumentChunkRepository
from hargus_api.db.repositories.workflow_run_repo import WorkflowRunRepository
from hargus_api.schemas.domain import (
    AnalysisReportResponse,
    Candidate,
    CandidateCreate,
    CandidateFile,
    CandidateFileCreate,
    CandidateListResponse,
    CandidateUpdate,
    DocumentChunkResponse,
    Message,
    MessageCreate,
    MessageListResponse,
    PaginationMeta,
)
from hargus_api.services.candidate_service import (
    add_candidate_file,
    add_message,
    create_candidate,
    delete_candidate,
    delete_candidate_file,
    get_candidate,
    get_candidate_messages,
    list_candidates_paginated,
    update_candidate,
)
from hargus_api.storage.factory import get_storage

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListResponse)
async def get_candidates(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    vacancy_id: str | None = Query(default=None, alias="vacancyId"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CandidateListResponse:
    items, total = await list_candidates_paginated(
        session, vacancy_id=vacancy_id, limit=limit, offset=offset
    )
    return CandidateListResponse(
        items=items,
        meta=PaginationMeta(total=total, limit=limit, offset=offset, returned=len(items)),
    )


@router.get("/{candidate_id}", response_model=Candidate)
async def get_candidate_by_id(
    candidate_id: str, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> Candidate:
    candidate = await get_candidate(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.get("/{candidate_id}/reports", response_model=list[AnalysisReportResponse])
async def list_reports(
    candidate_id: str, session: Annotated[AsyncSession, Depends(get_db_session)]
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


@router.get("/{candidate_id}/reports/{report_id}/pdf")
async def get_report_pdf(
    candidate_id: str, report_id: str, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> Response:
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID")

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


@router.post("", response_model=Candidate, status_code=201)
async def create_candidate_endpoint(
    body: CandidateCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Candidate:
    candidate = await create_candidate(session, body)
    await session.commit()
    return candidate


@router.patch("/{candidate_id}", response_model=Candidate)
async def update_candidate_endpoint(
    candidate_id: str,
    body: CandidateUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Candidate:
    candidate = await update_candidate(session, candidate_id, body)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    await session.commit()
    return candidate


@router.delete("/{candidate_id}", status_code=204)
async def delete_candidate_endpoint(
    candidate_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    deleted = await delete_candidate(session, candidate_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Candidate not found")
    await session.commit()
    return Response(status_code=204)


@router.get("/{candidate_id}/messages", response_model=MessageListResponse)
async def get_messages(
    candidate_id: str, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> MessageListResponse:
    candidate = await get_candidate(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    items = await get_candidate_messages(session, candidate_id)
    return MessageListResponse(
        items=items,
        meta=PaginationMeta(total=len(items), limit=len(items), offset=0, returned=len(items)),
    )


@router.post("/{candidate_id}/messages", response_model=Message, status_code=201)
async def create_message(
    candidate_id: str,
    body: MessageCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Message:
    candidate = await get_candidate(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    message = await add_message(session, candidate_id, body)
    await session.commit()
    return message


@router.post("/{candidate_id}/files", response_model=CandidateFile, status_code=201)
async def add_file(
    candidate_id: str,
    body: CandidateFileCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CandidateFile:
    candidate = await get_candidate(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    file = await add_candidate_file(session, candidate_id, body)
    await session.commit()
    return file


@router.delete("/{candidate_id}/files/{file_id}", status_code=204)
async def remove_file(
    candidate_id: str,
    file_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    deleted = await delete_candidate_file(session, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    await session.commit()
    return Response(status_code=204)


@router.get("/{candidate_id}/chunks", response_model=list[DocumentChunkResponse])
async def get_candidate_chunks(
    candidate_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=100, ge=1, le=500),
) -> list[DocumentChunkResponse]:
    candidate = await get_candidate(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    repo = DocumentChunkRepository(session)
    chunks = await repo.get_chunks_by_candidate(candidate_id, limit=limit)
    return [
        DocumentChunkResponse(
            id=str(c.id),
            candidateId=c.candidate_id,
            workflowRunId=c.workflow_run_id,
            sourceType=c.source_type,
            chunkIndex=c.chunk_index,
            content=c.content,
            hasEmbedding=c.embedding is not None,
            createdAt=c.created_at,
        )
        for c in chunks
    ]

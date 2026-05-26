import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.api.dependencies import get_current_user
from hargus_api.db.base import get_db_session
from hargus_api.db.models import User
from hargus_api.schemas.domain import (
    AiTaskRecord,
    AnalysisReportResponse,
    Candidate,
    CandidateFile,
    CandidateListResponse,
    CandidateQueryRequest,
    MessageListResponse,
    PaginationMeta,
)
from hargus_api.services.candidate_service import (
    create_candidate,
    delete_candidate,
    delete_candidate_file,
    get_candidate,
    list_candidates_paginated,
    upload_candidate_file,
)
from hargus_api.services.message_service import get_candidate_messages
from hargus_api.services.query_service import submit_candidate_query
from hargus_api.services.report_service import delete_report, get_report_pdf, list_reports_by_candidate

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("", response_model=Candidate, status_code=201)
async def create_candidate_endpoint(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
    vacancy_id: str = Form(...),
    cv: UploadFile = File(...),  # noqa: B008
    transcripts: list[UploadFile] = File(default=[]),  # noqa: B008
) -> Candidate:
    cv_data = (await cv.read(), cv.filename or "cv")
    transcript_data = [(await f.read(), f.filename or "transcript") for f in transcripts]
    return await create_candidate(session, vacancy_id, cv_data, transcript_data)


@router.get("", response_model=CandidateListResponse)
async def get_candidates(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
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


@router.delete("/{candidate_id}", status_code=204)
async def delete_candidate_endpoint(
    candidate_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> None:
    deleted = await delete_candidate(session, candidate_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Candidate not found")
    await session.commit()


@router.post("/{candidate_id}/files", response_model=CandidateFile, status_code=201)
async def upload_candidate_file_endpoint(
    candidate_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),  # noqa: B008
    type: str = Form(default="cv"),  # noqa: B008
) -> CandidateFile:
    result = await upload_candidate_file(
        session, candidate_id, await file.read(), file.filename or "file", type
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    await session.commit()
    return result


@router.delete("/{candidate_id}/files/{file_id}", status_code=204)
async def delete_candidate_file_endpoint(
    candidate_id: str,
    file_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> None:
    deleted = await delete_candidate_file(session, candidate_id, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    await session.commit()


@router.get("/{candidate_id}", response_model=Candidate)
async def get_candidate_by_id(
    candidate_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> Candidate:
    candidate = await get_candidate(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.get("/{candidate_id}/reports", response_model=list[AnalysisReportResponse])
async def list_reports(
    candidate_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await list_reports_by_candidate(session, candidate_id)


@router.get("/{candidate_id}/reports/{report_id}/pdf")
async def get_report_pdf_endpoint(
    candidate_id: str,
    report_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID") from None

    pdf_bytes = await get_report_pdf(session, candidate_id, rid)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="report-{report_id[:8]}.pdf"'},
    )


@router.delete("/{candidate_id}/reports/{report_id}", status_code=204)
async def delete_report_endpoint(
    candidate_id: str,
    report_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> None:
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID") from None
    deleted = await delete_report(session, candidate_id, rid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found")
    await session.commit()


@router.get("/{candidate_id}/messages", response_model=MessageListResponse)
async def get_messages(
    candidate_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> MessageListResponse:
    candidate = await get_candidate(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    items = await get_candidate_messages(session, candidate_id)
    return MessageListResponse(
        items=items,
        meta=PaginationMeta(total=len(items), limit=len(items), offset=0, returned=len(items)),
    )


@router.post("/{candidate_id}/query", response_model=AiTaskRecord, status_code=202)
async def query_candidate(
    candidate_id: str,
    body: CandidateQueryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> AiTaskRecord:
    candidate = await get_candidate(session, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return await submit_candidate_query(
        candidate_id=candidate_id,
        vacancy_id=body.vacancy_id,
        query=body.query,
    )

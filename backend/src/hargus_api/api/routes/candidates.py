from fastapi import APIRouter, HTTPException, Query

from hargus_api.schemas.domain import (
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

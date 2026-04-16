from fastapi import APIRouter, HTTPException, Query

from hargus_api.schemas.domain import Candidate, CandidateListResponse, MessageListResponse, PaginationMeta
from hargus_api.services.candidate_service import (
    get_candidate,
    get_candidate_messages,
    list_candidates,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListResponse)
async def get_candidates(vacancy_id: str | None = Query(default=None, alias="vacancyId")) -> CandidateListResponse:
    items = list_candidates(vacancy_id=vacancy_id)
    return CandidateListResponse(items=items, meta=PaginationMeta(total=len(items)))


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
    return MessageListResponse(items=items, meta=PaginationMeta(total=len(items)))

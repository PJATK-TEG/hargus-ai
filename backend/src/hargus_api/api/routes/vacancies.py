from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from hargus_api.schemas.domain import (
    CandidateListResponse,
    PaginationMeta,
    Vacancy,
    VacancyListResponse,
)
from hargus_api.services.candidate_service import get_vacancy, list_candidates, list_vacancies

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


def require_vacancy(vacancy_id: str) -> Vacancy:
    vacancy = get_vacancy(vacancy_id)
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy


@router.get("", response_model=VacancyListResponse)
async def get_vacancies() -> VacancyListResponse:
    items = list_vacancies()
    return VacancyListResponse(
        items=items,
        meta=PaginationMeta(total=len(items), limit=len(items), offset=0, returned=len(items)),
    )


@router.get("/{vacancy_id}", response_model=Vacancy)
async def get_vacancy_by_id(vacancy: Annotated[Vacancy, Depends(require_vacancy)]) -> Vacancy:  # noqa: B008
    return vacancy


@router.get("/{vacancy_id}/candidates", response_model=CandidateListResponse)
async def get_vacancy_candidates(
    vacancy: Annotated[Vacancy, Depends(require_vacancy)],  # noqa: B008
) -> CandidateListResponse:
    vacancy_id = vacancy.id
    items = list_candidates(vacancy_id=vacancy_id)
    return CandidateListResponse(
        items=items,
        meta=PaginationMeta(total=len(items), limit=len(items), offset=0, returned=len(items)),
    )

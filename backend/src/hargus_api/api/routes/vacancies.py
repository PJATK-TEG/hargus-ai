from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.api.dependencies import get_current_user
from hargus_api.db.base import get_db_session
from hargus_api.db.models import User
from hargus_api.schemas.domain import (
    CandidateListResponse,
    PaginationMeta,
    Vacancy,
    VacancyCreate,
    VacancyListResponse,
    VacancyUpdate,
)
from hargus_api.services.candidate_service import list_candidates
from hargus_api.services.vacancy_service import (
    create_vacancy,
    delete_vacancy,
    get_vacancy,
    list_vacancies,
    update_vacancy,
)

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


async def require_vacancy(vacancy_id: str, session: Annotated[AsyncSession, Depends(get_db_session)]) -> Vacancy:
    vacancy = await get_vacancy(session, vacancy_id)
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy


@router.post("", response_model=Vacancy, status_code=201)
async def post_vacancy(
    body: VacancyCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> Vacancy:
    return await create_vacancy(session, body.model_dump(by_alias=False))


@router.get("", response_model=VacancyListResponse)
async def get_vacancies(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> VacancyListResponse:
    items = await list_vacancies(session)
    return VacancyListResponse(
        items=items,
        meta=PaginationMeta(total=len(items), limit=len(items), offset=0, returned=len(items)),
    )


@router.get("/{vacancy_id}", response_model=Vacancy)
async def get_vacancy_by_id(
    vacancy: Annotated[Vacancy, Depends(require_vacancy)],  # noqa: B008
    _: Annotated[User, Depends(get_current_user)],
) -> Vacancy:
    return vacancy


@router.put("/{vacancy_id}", response_model=Vacancy)
async def update_vacancy_endpoint(
    vacancy_id: str,
    body: VacancyUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> Vacancy:
    updated = await update_vacancy(session, vacancy_id, body.model_dump(by_alias=False, exclude_none=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    await session.commit()
    return updated


@router.delete("/{vacancy_id}", status_code=204)
async def delete_vacancy_endpoint(
    vacancy_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> None:
    deleted = await delete_vacancy(session, vacancy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    await session.commit()


@router.get("/{vacancy_id}/candidates", response_model=CandidateListResponse)
async def get_vacancy_candidates(
    vacancy: Annotated[Vacancy, Depends(require_vacancy)],  # noqa: B008
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> CandidateListResponse:
    vacancy_id = vacancy.id
    items = await list_candidates(session, vacancy_id=vacancy_id)
    return CandidateListResponse(
        items=items,
        meta=PaginationMeta(total=len(items), limit=len(items), offset=0, returned=len(items)),
    )

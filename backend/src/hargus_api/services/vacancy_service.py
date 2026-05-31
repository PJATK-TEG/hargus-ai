from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.repositories.vacancy_repo import VacancyRepository
from hargus_api.schemas.domain import Vacancy


async def list_vacancies(session: AsyncSession) -> list[Vacancy]:
    rows = await VacancyRepository(session).list_all()
    return [Vacancy.model_validate(v, from_attributes=True) for v in rows]


async def get_vacancy(session: AsyncSession, vacancy_id: str) -> Vacancy | None:
    row = await VacancyRepository(session).get_by_id(vacancy_id)
    return Vacancy.model_validate(row, from_attributes=True) if row else None


async def create_vacancy(session: AsyncSession, data: dict) -> Vacancy:
    row = await VacancyRepository(session).create(data)
    return Vacancy.model_validate(row, from_attributes=True)


async def update_vacancy(session: AsyncSession, vacancy_id: str, data: dict) -> Vacancy | None:
    row = await VacancyRepository(session).update(vacancy_id, data)
    if row is None:
        return None
    return Vacancy.model_validate(row, from_attributes=True)


async def delete_vacancy(session: AsyncSession, vacancy_id: str) -> bool:
    return await VacancyRepository(session).delete(vacancy_id)

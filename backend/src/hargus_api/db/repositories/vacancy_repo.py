from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.models import Vacancy


class VacancyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> Vacancy:
        obj = Vacancy(**data)
        self._session.add(obj)
        await self._session.flush()
        return obj

    async def get_by_id(self, vacancy_id: str) -> Vacancy | None:
        return await self._session.get(Vacancy, vacancy_id)

    async def list_all(self) -> list[Vacancy]:
        result = await self._session.execute(select(Vacancy))
        return list(result.scalars().all())

    async def update(self, vacancy_id: str, updates: dict) -> Vacancy | None:
        obj = await self._session.get(Vacancy, vacancy_id)
        if obj is None:
            return None
        for key, value in updates.items():
            setattr(obj, key, value)
        await self._session.flush()
        return obj

    async def delete(self, vacancy_id: str) -> bool:
        obj = await self._session.get(Vacancy, vacancy_id)
        if obj is None:
            return False
        await self._session.delete(obj)
        await self._session.flush()
        return True

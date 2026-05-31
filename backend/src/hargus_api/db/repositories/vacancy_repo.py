from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.models import Vacancy


class VacancyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Vacancy]:
        result = await self._session.execute(select(Vacancy))
        return list(result.scalars().all())

    async def get_by_id(self, vacancy_id: str) -> Vacancy | None:
        return await self._session.get(Vacancy, vacancy_id)

    async def update(self, vacancy_id: str, data: dict) -> Vacancy | None:
        vacancy = await self._session.get(Vacancy, vacancy_id)
        if vacancy is None:
            return None
        for key, value in data.items():
            setattr(vacancy, key, value)
        await self._session.flush()
        await self._session.refresh(vacancy)
        return vacancy

    async def delete(self, vacancy_id: str) -> bool:
        vacancy = await self._session.get(Vacancy, vacancy_id)
        if vacancy is None:
            return False
        await self._session.delete(vacancy)
        await self._session.flush()
        return True

    async def create(self, data: dict) -> Vacancy:
        row = Vacancy(
            id=str(uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            candidates_count=0,
            status="active",
            hires_target=data.get("hires_target", 1),
            title=data["title"],
            department=data["department"],
            location=data["location"],
            type=data["type"],
            description=data["description"],
            requirements=data.get("requirements", []),
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

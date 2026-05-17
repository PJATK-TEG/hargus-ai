from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hargus_api.db.models import Candidate

logger = logging.getLogger(__name__)

_NAME_SENTINEL = "[run Analyze] New Candidate"


def _initials(name: str) -> str:
    parts = name.strip().split()
    return ("".join(p[0].upper() for p in parts[:2]) or "?")[:8]


class CandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, vacancy_id: str | None = None) -> list[Candidate]:
        stmt = select(Candidate).options(selectinload(Candidate.files))
        if vacancy_id is not None:
            stmt = stmt.where(Candidate.vacancy_id == vacancy_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_paginated(
        self,
        vacancy_id: str | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Candidate], int]:
        count_stmt = select(func.count(Candidate.id))
        stmt = select(Candidate).options(selectinload(Candidate.files)).limit(limit).offset(offset)
        if vacancy_id is not None:
            count_stmt = count_stmt.where(Candidate.vacancy_id == vacancy_id)
            stmt = stmt.where(Candidate.vacancy_id == vacancy_id)
        total = await self._session.scalar(count_stmt) or 0
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, candidate_id: str) -> Candidate | None:
        stmt = (
            select(Candidate)
            .options(selectinload(Candidate.files))
            .where(Candidate.id == candidate_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def create(self, data: dict) -> Candidate:
        candidate = Candidate(**data)
        self._session.add(candidate)
        await self._session.flush()
        return candidate

    async def update_from_analysis(
        self,
        candidate_id: str,
        parsed_fields: dict,
        score: int,
    ) -> None:
        candidate = await self._session.get(Candidate, candidate_id)
        if candidate is None:
            logger.warning("update_from_analysis: candidate %s not found in DB", candidate_id)
            return
        candidate.parsed_fields = parsed_fields
        candidate.score = score

    async def delete(self, candidate_id: str) -> bool:
        candidate = await self._session.get(Candidate, candidate_id)
        if candidate is None:
            return False
        await self._session.delete(candidate)
        await self._session.flush()
        return True

    async def update_profile(
        self,
        candidate_id: str,
        name: str,
        email: str,
        phone: str,
        location: str,
        linkedin_url: str,
    ) -> None:
        candidate = await self._session.get(Candidate, candidate_id)
        if candidate is None:
            logger.warning("update_profile: candidate %s not found", candidate_id)
            return
        if name and candidate.name == _NAME_SENTINEL:
            candidate.name = name
            candidate.avatar_initials = _initials(name)
        if email and not candidate.email:
            candidate.email = email
        if phone and not candidate.phone:
            candidate.phone = phone
        if location and not candidate.location:
            candidate.location = location
        if linkedin_url and not candidate.linkedin_url:
            candidate.linkedin_url = linkedin_url

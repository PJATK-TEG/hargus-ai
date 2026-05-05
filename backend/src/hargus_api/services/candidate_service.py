from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hargus_api.db.models import (
    Candidate as DBCandidate,
    Vacancy as DBVacancy,
    Message as DBMessage,
)
from hargus_api.schemas.domain import Candidate, Message, Vacancy

async def list_vacancies(session: AsyncSession) -> list[Vacancy]:
    result = await session.execute(select(DBVacancy))
    return [Vacancy.model_validate(v, from_attributes=True) for v in result.scalars().all()]


async def get_vacancy(session: AsyncSession, vacancy_id: str) -> Vacancy | None:
    db_v = await session.get(DBVacancy, vacancy_id)
    return Vacancy.model_validate(db_v, from_attributes=True) if db_v else None


async def list_candidates(session: AsyncSession, vacancy_id: str | None = None) -> list[Candidate]:
    stmt = select(DBCandidate).options(selectinload(DBCandidate.files))
    if vacancy_id is not None:
        stmt = stmt.where(DBCandidate.vacancy_id == vacancy_id)
    result = await session.execute(stmt)
    return [Candidate.model_validate(c, from_attributes=True) for c in result.scalars().all()]


async def list_candidates_paginated(
    session: AsyncSession,
    vacancy_id: str | None = None,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Candidate], int]:
    count_stmt = select(func.count(DBCandidate.id))
    stmt = select(DBCandidate).options(selectinload(DBCandidate.files)).limit(limit).offset(offset)
    
    if vacancy_id is not None:
        count_stmt = count_stmt.where(DBCandidate.vacancy_id == vacancy_id)
        stmt = stmt.where(DBCandidate.vacancy_id == vacancy_id)
        
    total = await session.scalar(count_stmt) or 0
    result = await session.execute(stmt)
    
    return [Candidate.model_validate(c, from_attributes=True) for c in result.scalars().all()], total


async def get_candidate(session: AsyncSession, candidate_id: str) -> Candidate | None:
    stmt = select(DBCandidate).options(selectinload(DBCandidate.files)).where(DBCandidate.id == candidate_id)
    result = await session.execute(stmt)
    db_c = result.scalars().first()
    return Candidate.model_validate(db_c, from_attributes=True) if db_c else None


async def get_candidate_messages(session: AsyncSession, candidate_id: str) -> list[Message]:
    stmt = select(DBMessage).where(DBMessage.candidate_id == candidate_id).order_by(DBMessage.timestamp)
    result = await session.execute(stmt)
    return [Message.model_validate(m, from_attributes=True) for m in result.scalars().all()]

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hargus_api.db.models import Candidate as DBCandidate
from hargus_api.db.models import Message as DBMessage
from hargus_api.db.models import Vacancy as DBVacancy
from hargus_api.db.repositories.candidate_repo import CandidateRepository
from hargus_api.db.repositories.vacancy_repo import VacancyRepository
from hargus_api.schemas.domain import (
    Candidate,
    CandidateCreate,
    CandidateFile,
    CandidateFileCreate,
    CandidateUpdate,
    Message,
    MessageCreate,
    Vacancy,
    VacancyCreate,
    VacancyUpdate,
)


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


# ── Write operations ──────────────────────────────────────────────────────────


async def create_vacancy(session: AsyncSession, data: VacancyCreate) -> Vacancy:
    repo = VacancyRepository(session)
    obj = await repo.create(data.model_dump(by_alias=False))
    return Vacancy.model_validate(obj, from_attributes=True)


async def update_vacancy(session: AsyncSession, vacancy_id: str, data: VacancyUpdate) -> Vacancy | None:
    repo = VacancyRepository(session)
    updates = {k: v for k, v in data.model_dump(by_alias=False).items() if v is not None}
    obj = await repo.update(vacancy_id, updates)
    return Vacancy.model_validate(obj, from_attributes=True) if obj else None


async def delete_vacancy(session: AsyncSession, vacancy_id: str) -> bool:
    return await VacancyRepository(session).delete(vacancy_id)


async def create_candidate(session: AsyncSession, data: CandidateCreate) -> Candidate:
    repo = CandidateRepository(session)
    raw = data.model_dump(by_alias=False)
    # tags and parsed_fields must be stored as plain dicts for JSONB
    raw["tags"] = [t.model_dump(by_alias=False) for t in data.tags]
    raw["parsed_fields"] = data.parsed_fields.model_dump(by_alias=False)
    obj = await repo.create(raw)
    # increment vacancy candidates_count
    vacancy = await session.get(DBVacancy, data.vacancy_id)
    if vacancy is not None:
        vacancy.candidates_count += 1
    await session.flush()
    # reload with files relationship for serialisation
    stmt = select(DBCandidate).options(selectinload(DBCandidate.files)).where(DBCandidate.id == obj.id)
    result = await session.execute(stmt)
    loaded = result.scalars().first()
    return Candidate.model_validate(loaded, from_attributes=True)


async def update_candidate(session: AsyncSession, candidate_id: str, data: CandidateUpdate) -> Candidate | None:
    repo = CandidateRepository(session)
    updates = {k: v for k, v in data.model_dump(by_alias=False).items() if v is not None}
    if "tags" in updates:
        updates["tags"] = [t.model_dump(by_alias=False) for t in data.tags]
    if "parsed_fields" in updates:
        updates["parsed_fields"] = data.parsed_fields.model_dump(by_alias=False)
    obj = await repo.update(candidate_id, updates)
    if obj is None:
        return None
    stmt = select(DBCandidate).options(selectinload(DBCandidate.files)).where(DBCandidate.id == obj.id)
    result = await session.execute(stmt)
    loaded = result.scalars().first()
    return Candidate.model_validate(loaded, from_attributes=True)


async def delete_candidate(session: AsyncSession, candidate_id: str) -> bool:
    obj = await session.get(DBCandidate, candidate_id)
    if obj is None:
        return False
    vacancy = await session.get(DBVacancy, obj.vacancy_id)
    if vacancy is not None and vacancy.candidates_count > 0:
        vacancy.candidates_count -= 1
    await CandidateRepository(session).delete(candidate_id)
    return True


async def add_candidate_file(session: AsyncSession, candidate_id: str, data: CandidateFileCreate) -> CandidateFile:
    repo = CandidateRepository(session)
    raw = data.model_dump(by_alias=False)
    obj = await repo.add_file(candidate_id, raw)
    return CandidateFile.model_validate(obj, from_attributes=True)


async def delete_candidate_file(session: AsyncSession, file_id: str) -> bool:
    return await CandidateRepository(session).delete_file(file_id)


async def add_message(session: AsyncSession, candidate_id: str, data: MessageCreate) -> Message:
    repo = CandidateRepository(session)
    obj = await repo.add_message(candidate_id, data.model_dump())
    return Message.model_validate(obj, from_attributes=True)

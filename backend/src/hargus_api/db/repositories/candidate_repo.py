from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.models import Candidate, CandidateFile, Message


class CandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> Candidate:
        obj = Candidate(**data)
        self._session.add(obj)
        await self._session.flush()
        return obj

    async def get_by_id(self, candidate_id: str) -> Candidate | None:
        return await self._session.get(Candidate, candidate_id)

    async def update(self, candidate_id: str, updates: dict) -> Candidate | None:
        obj = await self._session.get(Candidate, candidate_id)
        if obj is None:
            return None
        for key, value in updates.items():
            setattr(obj, key, value)
        await self._session.flush()
        return obj

    async def delete(self, candidate_id: str) -> bool:
        obj = await self._session.get(Candidate, candidate_id)
        if obj is None:
            return False
        await self._session.delete(obj)
        await self._session.flush()
        return True

    async def add_file(self, candidate_id: str, file_data: dict) -> CandidateFile:
        obj = CandidateFile(candidate_id=candidate_id, **file_data)
        self._session.add(obj)
        await self._session.flush()
        return obj

    async def get_file(self, file_id: str) -> CandidateFile | None:
        return await self._session.get(CandidateFile, file_id)

    async def delete_file(self, file_id: str) -> bool:
        obj = await self._session.get(CandidateFile, file_id)
        if obj is None:
            return False
        await self._session.delete(obj)
        await self._session.flush()
        return True

    async def add_message(self, candidate_id: str, message_data: dict) -> Message:
        obj = Message(candidate_id=candidate_id, **message_data)
        self._session.add(obj)
        await self._session.flush()
        return obj

    async def list_files(self, candidate_id: str) -> list[CandidateFile]:
        result = await self._session.execute(
            select(CandidateFile).where(CandidateFile.candidate_id == candidate_id)
        )
        return list(result.scalars().all())

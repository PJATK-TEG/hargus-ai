from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.models import DocumentChunk


class DocumentChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_candidate(self, candidate_id: str) -> list[DocumentChunk]:
        result = await self._session.execute(
            select(DocumentChunk).where(DocumentChunk.candidate_id == candidate_id)
        )
        return list(result.scalars().all())

    async def list_by_workflow_run(self, workflow_run_id: str) -> list[DocumentChunk]:
        result = await self._session.execute(
            select(DocumentChunk).where(DocumentChunk.workflow_run_id == workflow_run_id)
        )
        return list(result.scalars().all())

    async def save(self, chunk: DocumentChunk) -> DocumentChunk:
        self._session.add(chunk)
        await self._session.flush()
        return chunk

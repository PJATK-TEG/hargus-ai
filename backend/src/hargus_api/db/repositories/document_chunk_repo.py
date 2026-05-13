from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.models import DocumentChunk


class DocumentChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_chunks_by_candidate(
        self, candidate_id: str, limit: int = 100
    ) -> list[DocumentChunk]:
        result = await self._session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.candidate_id == candidate_id)
            .order_by(DocumentChunk.chunk_index)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_chunks_by_workflow_run(self, workflow_run_id: str) -> list[DocumentChunk]:
        result = await self._session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.workflow_run_id == workflow_run_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def delete_chunks_by_candidate(self, candidate_id: str) -> int:
        result = await self._session.execute(
            delete(DocumentChunk).where(DocumentChunk.candidate_id == candidate_id)
        )
        await self._session.flush()
        return result.rowcount

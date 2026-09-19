from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.models import Message


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_candidate(self, candidate_id: str) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.candidate_id == candidate_id)
            .order_by(Message.timestamp)
        )
        return list(result.scalars().all())

    async def create_message(self, candidate_id: str, role: str, content: str) -> Message:
        msg = Message(
            id=str(uuid4()),
            candidate_id=candidate_id,
            role=role,
            content=content,
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._session.add(msg)
        await self._session.flush()
        return msg

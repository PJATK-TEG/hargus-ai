from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.repositories.message_repo import MessageRepository
from hargus_api.schemas.domain import Message


async def get_candidate_messages(session: AsyncSession, candidate_id: str) -> list[Message]:
    rows = await MessageRepository(session).list_by_candidate(candidate_id)
    return [Message.model_validate(m, from_attributes=True) for m in rows]


async def save_message(session: AsyncSession, candidate_id: str, role: str, content: str) -> Message:
    repo = MessageRepository(session)
    msg = await repo.create_message(candidate_id, role, content)
    return Message.model_validate(msg, from_attributes=True)

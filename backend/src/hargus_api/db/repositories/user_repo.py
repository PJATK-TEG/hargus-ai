from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_by_id(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)

    async def create(self, email: str, password_hash: str, name: str, role: str = "recruiter") -> User:
        user = User(email=email, password_hash=password_hash, name=name, role=role)
        self._session.add(user)
        await self._session.flush()
        return user

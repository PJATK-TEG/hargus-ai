from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from hargus_api.api.dependencies import get_current_user
from hargus_api.db.base import get_db_session
from hargus_api.db.models import User
from hargus_api.db.repositories.user_repo import UserRepository
from hargus_api.schemas.domain import TokenResponse, UserCreate, UserLogin, UserResponse
from hargus_api.services.auth_service import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    repo = UserRepository(session)
    if await repo.get_by_email(body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await repo.create(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=body.role,
    )
    await session.commit()
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    repo = UserRepository(session)
    user = await repo.get_by_email(body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id)
    return TokenResponse(
        accessToken=token,
        user=UserResponse.model_validate(user, from_attributes=True),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(current_user, from_attributes=True)

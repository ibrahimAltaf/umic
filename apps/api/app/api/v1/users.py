"""User management API routes."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.permissions import PermissionCode
from app.dependencies.auth import DbSession, require_permissions
from app.models.auth import User
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.services.auth import AuthService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=dict)
async def list_users(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.USERS_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=200),
) -> dict:
    return AuthService(db).list_users(
        actor=user, page=page, page_size=page_size, search=search
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.USERS_WRITE))],
) -> UserOut:
    return AuthService(db).register_user(body, actor=user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.USERS_WRITE))],
) -> UserOut:
    return AuthService(db).update_user(user_id, body, actor=user)

"""Roles and permissions API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.permissions import PermissionCode
from app.dependencies.auth import DbSession, require_permissions
from app.models.auth import User
from app.repositories.user import RoleRepository
from app.schemas.auth import PermissionOut, RoleOut

router = APIRouter(tags=["Roles & Permissions"])


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
    db: DbSession,
    _: Annotated[User, Depends(require_permissions(PermissionCode.ROLES_READ))],
) -> list[RoleOut]:
    roles = RoleRepository(db).list_all()
    return [RoleOut.model_validate(r) for r in roles]


@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(
    db: DbSession,
    _: Annotated[User, Depends(require_permissions(PermissionCode.PERMISSIONS_READ))],
) -> list[PermissionOut]:
    perms = RoleRepository(db).list_permissions()
    return [PermissionOut.model_validate(p) for p in perms]

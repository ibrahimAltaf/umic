"""Global search API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.permissions import PermissionCode
from app.dependencies.auth import DbSession, require_permissions
from app.models.auth import User
from app.services.search import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("")
async def global_search(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    return SearchService(db).search(user=user, q=q, limit=limit)

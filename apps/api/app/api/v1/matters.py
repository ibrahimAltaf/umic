"""Matter API routes."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.permissions import PermissionCode
from app.dependencies.auth import DbSession, require_permissions
from app.models.auth import User
from app.schemas.domain import (
    BillingClassificationOut,
    MatterCreate,
    MatterOut,
    MatterStatusOut,
    MatterTypeOut,
    MatterUpdate,
)
from app.services.matter import MatterService

router = APIRouter(prefix="/matters", tags=["Matters"])


@router.get("/meta/reference")
async def matter_reference(
    db: DbSession,
    _: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
) -> dict:
    data = MatterService(db).reference_data()
    return {
        "matter_types": [MatterTypeOut.model_validate(t) for t in data["matter_types"]],
        "statuses": [MatterStatusOut.model_validate(s) for s in data["statuses"]],
        "billing_classifications": [
            BillingClassificationOut.model_validate(b)
            for b in data["billing_classifications"]
        ],
    }


@router.get("")
async def list_matters(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status_code: Optional[str] = None,
    billing_code: Optional[str] = None,
) -> dict:
    return MatterService(db).list_matters(
        user=user,
        page=page,
        page_size=page_size,
        search=search,
        status_code=status_code,
        billing_code=billing_code,
    )


@router.post("", response_model=MatterOut, status_code=status.HTTP_201_CREATED)
async def create_matter(
    body: MatterCreate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_WRITE))],
) -> MatterOut:
    return MatterService(db).create(body, user=user)


@router.get("/{matter_id}", response_model=MatterOut)
async def get_matter(
    matter_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
) -> MatterOut:
    return MatterService(db).get(matter_id, user=user)


@router.patch("/{matter_id}", response_model=MatterOut)
async def update_matter(
    matter_id: UUID,
    body: MatterUpdate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_WRITE))],
) -> MatterOut:
    return MatterService(db).update(matter_id, body, user=user)

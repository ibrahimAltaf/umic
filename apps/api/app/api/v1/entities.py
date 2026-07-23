"""Entity and relationship API routes."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.permissions import PermissionCode
from app.dependencies.auth import DbSession, require_permissions
from app.models.auth import User
from app.schemas.domain import (
    EntityCreate,
    EntityOut,
    EntityTypeOut,
    EntityUpdate,
    RelationshipCreate,
    RelationshipOut,
)
from app.services.domain import EntityService

router = APIRouter(tags=["Entities"])


@router.get("/entity-types", response_model=list[EntityTypeOut])
async def list_entity_types(
    db: DbSession,
    _: Annotated[User, Depends(require_permissions(PermissionCode.ENTITIES_READ))],
) -> list[EntityTypeOut]:
    return [EntityTypeOut.model_validate(t) for t in EntityService(db).list_types()]


@router.get("/entities")
async def list_entities(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.ENTITIES_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
) -> dict:
    return EntityService(db).list_entities(
        user=user, page=page, page_size=page_size, search=search
    )


@router.post("/entities", response_model=EntityOut, status_code=status.HTTP_201_CREATED)
async def create_entity(
    body: EntityCreate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.ENTITIES_WRITE))],
) -> EntityOut:
    return EntityService(db).create(body, user=user)


@router.get("/entities/{entity_id}", response_model=EntityOut)
async def get_entity(
    entity_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.ENTITIES_READ))],
) -> EntityOut:
    return EntityService(db).get(entity_id, user=user)


@router.patch("/entities/{entity_id}", response_model=EntityOut)
async def update_entity(
    entity_id: UUID,
    body: EntityUpdate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.ENTITIES_WRITE))],
) -> EntityOut:
    return EntityService(db).update(entity_id, body, user=user)


@router.post(
    "/relationships",
    response_model=RelationshipOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    body: RelationshipCreate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.ENTITIES_WRITE))],
) -> RelationshipOut:
    return EntityService(db).create_relationship(body, user=user)


@router.delete("/relationships/{relationship_id}")
async def delete_relationship(
    relationship_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.ENTITIES_WRITE))],
) -> dict:
    return EntityService(db).delete_relationship(relationship_id, user=user)

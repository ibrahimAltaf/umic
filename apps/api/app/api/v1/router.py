"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    entities,
    finance,
    integrations,
    intelligence,
    matters,
    operations,
    roles,
    search,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(matters.router)
api_router.include_router(entities.router)
api_router.include_router(operations.router)
api_router.include_router(integrations.router)
api_router.include_router(search.router)
api_router.include_router(finance.router)
api_router.include_router(intelligence.router)

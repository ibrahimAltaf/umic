"""Review, billing, dashboard, audit, integrations routes."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.permissions import PermissionCode
from app.dependencies.auth import DbSession, require_permissions
from app.models.auth import User
from app.schemas.domain import (
    AuditEventOut,
    BillingEntryCreate,
    BillingEntryDecision,
    BillingEntryOut,
    DashboardStats,
    IntegrationOut,
    ReviewItemOut,
    ReviewItemUpdate,
)
from app.services.domain import (
    AuditQueryService,
    BillingService,
    DashboardService,
    IntegrationService,
    ReviewService,
)

router = APIRouter(tags=["Operations"])


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
) -> DashboardStats:
    return DashboardService(db).stats(user=user)


@router.get("/review-queue", response_model=list[ReviewItemOut])
async def list_review_queue(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.REVIEW_QUEUE_READ))],
    status: Optional[str] = None,
) -> list[ReviewItemOut]:
    return ReviewService(db).list_items(user=user, status=status)


@router.patch("/review-queue/{item_id}", response_model=ReviewItemOut)
async def update_review_item(
    item_id: UUID,
    body: ReviewItemUpdate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.REVIEW_QUEUE_WRITE))],
) -> ReviewItemOut:
    return ReviewService(db).update(item_id, body, user=user)


@router.get("/billing/entries")
async def list_billing_entries(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_READ))],
    approval_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> dict:
    return BillingService(db).list_entries(
        user=user, approval_status=approval_status, page=page, page_size=page_size
    )


@router.post("/billing/entries", response_model=BillingEntryOut, status_code=201)
async def create_billing_entry(
    body: BillingEntryCreate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_WRITE))],
) -> BillingEntryOut:
    return BillingService(db).create(body, user=user)


@router.post("/billing/entries/{entry_id}/approve", response_model=BillingEntryOut)
async def approve_billing_entry(
    entry_id: UUID,
    body: BillingEntryDecision,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_APPROVE))],
) -> BillingEntryOut:
    return BillingService(db).approve(entry_id, user=user, reason=body.reason)


@router.post("/billing/entries/{entry_id}/reject", response_model=BillingEntryOut)
async def reject_billing_entry(
    entry_id: UUID,
    body: BillingEntryDecision,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_APPROVE))],
) -> BillingEntryOut:
    return BillingService(db).reject(entry_id, user=user, reason=body.reason)


@router.get("/billing/codes")
async def list_billing_codes(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_READ))],
) -> list:
    return BillingService(db).list_codes(user=user)


@router.get("/audit-events")
async def list_audit_events(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.AUDIT_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> dict:
    data = AuditQueryService(db).list_events(user=user, page=page, page_size=page_size)
    data["items"] = [AuditEventOut.model_validate(i) for i in data["items"]]
    return data


@router.get("/discrepancies")
async def list_discrepancies(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.REVIEW_QUEUE_READ))],
    matter_id: Optional[UUID] = None,
    status: Optional[str] = "open",
) -> list:
    from app.services.discrepancy import DiscrepancyService

    filter_status = None if status in (None, "", "all") else status
    return DiscrepancyService(db).list_alerts(user=user, matter_id=matter_id, status=filter_status)


@router.post("/discrepancies/{alert_id}/resolve")
async def resolve_discrepancy(
    alert_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.REVIEW_QUEUE_WRITE))],
) -> dict:
    from app.services.discrepancy import DiscrepancyService

    return DiscrepancyService(db).resolve(alert_id, user=user)


@router.get("/integrations", response_model=list[IntegrationOut])
async def list_integrations_legacy(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_READ))],
) -> list[IntegrationOut]:
    return [
        IntegrationOut.model_validate(c)
        for c in IntegrationService(db).list_connections(user=user)
    ]

"""Expenses, mileage, matter overview, T&E export, duplicates."""

from datetime import date
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.permissions import PermissionCode
from app.dependencies.auth import DbSession, require_permissions
from app.models.auth import User
from app.services.finance import FinanceService

router = APIRouter(tags=["Finance"])


class ExpenseCreate(BaseModel):
    matter_id: UUID
    amount: float = Field(..., gt=0)
    vendor: Optional[str] = None
    invoice_date: Optional[date] = None
    invoice_number: Optional[str] = None
    category: str = "general"
    tax: Optional[float] = None
    payment_status: str = "unpaid"
    reimbursable: bool = True
    billing_code: Optional[str] = None
    notes: Optional[str] = None


class MileageCreate(BaseModel):
    matter_id: UUID
    activity_date: date
    miles: float = Field(..., gt=0)
    origin: Optional[str] = None
    destination: Optional[str] = None
    trip_type: str = "round_trip"
    mileage_rate: float = 0.67
    travel_time_hours: Optional[float] = None
    notes: Optional[str] = None


class ExportBody(BaseModel):
    spreadsheet_id: Optional[str] = None


@router.get("/matters/{matter_id}/overview")
async def matter_overview(
    matter_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
) -> dict:
    return FinanceService(db).matter_overview(matter_id, user=user)


@router.get("/expenses")
async def list_expenses(
    db: DbSession,
    _: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_READ))],
    matter_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> dict:
    return FinanceService(db).list_expenses(matter_id=matter_id, page=page, page_size=page_size)


@router.post("/expenses", status_code=201)
async def create_expense(
    body: ExpenseCreate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_WRITE))],
) -> dict:
    return FinanceService(db).create_expense(body.model_dump(), user=user)


@router.post("/expenses/{expense_id}/approve")
async def approve_expense(
    expense_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_APPROVE))],
) -> dict:
    return FinanceService(db).decide_expense(expense_id, approve=True, user=user)


@router.post("/expenses/{expense_id}/reject")
async def reject_expense(
    expense_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_APPROVE))],
) -> dict:
    return FinanceService(db).decide_expense(expense_id, approve=False, user=user)


@router.get("/mileage")
async def list_mileage(
    db: DbSession,
    _: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_READ))],
    matter_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> dict:
    return FinanceService(db).list_mileage(matter_id=matter_id, page=page, page_size=page_size)


@router.post("/mileage", status_code=201)
async def create_mileage(
    body: MileageCreate,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_WRITE))],
) -> dict:
    return FinanceService(db).create_mileage(body.model_dump(), user=user)


@router.post("/mileage/{entry_id}/approve")
async def approve_mileage(
    entry_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_APPROVE))],
) -> dict:
    return FinanceService(db).decide_mileage(entry_id, approve=True, user=user)


@router.post("/mileage/{entry_id}/reject")
async def reject_mileage(
    entry_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_APPROVE))],
) -> dict:
    return FinanceService(db).decide_mileage(entry_id, approve=False, user=user)


@router.post("/matters/{matter_id}/export-te")
async def export_te(
    matter_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.BILLING_WRITE))],
    body: ExportBody | None = None,
) -> dict:
    return FinanceService(db).export_te_sheet(
        matter_id=matter_id,
        user=user,
        spreadsheet_id=body.spreadsheet_id if body else None,
    )


@router.get("/documents/duplicates")
async def document_duplicates(
    db: DbSession,
    _: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
) -> dict:
    return FinanceService(db).find_duplicate_documents()

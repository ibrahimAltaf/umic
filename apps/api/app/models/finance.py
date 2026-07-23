"""Expense and mileage models."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Expense(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "expenses"

    matter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    supporting_document_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unpaid")
    reimbursable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    billing_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    matter = relationship("Matter", lazy="joined")


class MileageEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "mileage_entries"

    matter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    origin: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    destination: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trip_type: Mapped[str] = mapped_column(String(32), nullable=False, default="round_trip")
    miles: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    mileage_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.67"))
    mileage_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    travel_time_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    matter = relationship("Matter", lazy="joined")

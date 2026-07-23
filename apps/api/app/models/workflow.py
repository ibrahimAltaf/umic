"""Review queue, billing foundation, and discrepancy models."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ReviewQueueItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "review_queue_items"

    item_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_record_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    related_record_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    matter_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    kanban_column: Mapped[str] = mapped_column(String(32), nullable=False, default="inbox")
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class DiscrepancyAlert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "discrepancy_alerts"

    matter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matters.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    imported_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class BillingCodeLibrary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "billing_code_libraries"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class BillingCode(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "billing_codes"
    __table_args__ = (
        UniqueConstraint("library_id", "code", name="uq_billing_codes_library_code"),
    )

    library_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_code_libraries.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    library: Mapped["BillingCodeLibrary"] = relationship("BillingCodeLibrary", lazy="joined")


class BillingEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "billing_entries"

    matter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    code_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_codes.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_charge: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    mileage: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    mileage_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    mileage_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    cost_incurred: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    hourly_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    time_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    source_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    billing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed")
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    invoice_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unbilled")
    duplicate_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    is_manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    matter = relationship("Matter", lazy="joined")
    code = relationship("BillingCode", lazy="joined")


class IntegrationConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "integration_connections"

    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    account_label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="disconnected")
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_successful_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failed_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Tokens stored encrypted in later phase — placeholder columns only
    token_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    connected_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

"""Matter and related reference models."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

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


class MatterType(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "matter_types"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MatterStatus(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "matter_statuses"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)


class BillingClassification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "billing_classifications"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    allows_proposed_billing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Matter(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "matters"

    matter_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    matter_type_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matter_types.id"), nullable=False
    )
    status_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matter_statuses.id"), nullable=False
    )
    billing_classification_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_classifications.id"), nullable=False
    )

    claim_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    policy_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    case_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    appraisal_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    property_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    date_of_loss: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_of_discovery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    open_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    closed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    hourly_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    billing_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    dropbox_folder_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_drive_folder_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_expense_sheet_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_confidential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_privileged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_personal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    search_keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_summary_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    matter_type: Mapped["MatterType"] = relationship("MatterType", lazy="joined")
    status: Mapped["MatterStatus"] = relationship("MatterStatus", lazy="joined")
    billing_classification: Mapped["BillingClassification"] = relationship(
        "BillingClassification", lazy="joined"
    )
    aliases: Mapped[List["MatterAlias"]] = relationship(
        "MatterAlias", back_populates="matter", cascade="all, delete-orphan", lazy="selectin"
    )


class MatterAlias(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "matter_aliases"
    __table_args__ = (
        UniqueConstraint("matter_id", "alias", name="uq_matter_aliases_matter_alias"),
    )

    matter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matters.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    matter: Mapped["Matter"] = relationship("Matter", back_populates="aliases")

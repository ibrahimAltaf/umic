"""Email and document records indexed from external sources."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class EmailRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint("gmail_message_id", "gmail_account", name="uq_emails_gmail_msg_account"),
    )

    gmail_message_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    gmail_thread_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    gmail_account: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(32), nullable=False, default="incoming")
    sender: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    to_recipients: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cc_recipients: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bcc_recipients: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    labels: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    attachment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gmail_message_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_matter_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    classification_confidence: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="indexed")
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    raw_headers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    primary_matter = relationship("Matter", lazy="joined")


class DocumentRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("source_system", "source_file_id", name="uq_documents_source_file"),
    )

    source_system: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_file_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    current_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_folder: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    direct_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_discovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synchronized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    primary_matter_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    document_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    billing_relevance: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    confidentiality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    classification_confidence: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    primary_matter = relationship("Matter", lazy="joined")

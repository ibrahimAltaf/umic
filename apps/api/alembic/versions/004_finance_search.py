"""Expenses, mileage tables + search indexes.

Revision ID: 004_finance_search
Revises: 003_comms_docs
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_finance_search"
down_revision: Union[str, None] = "003_comms_docs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor", sa.String(255), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("invoice_number", sa.String(128), nullable=True),
        sa.Column("category", sa.String(64), nullable=False, server_default="general"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax", sa.Numeric(12, 2), nullable=True),
        sa.Column("supporting_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payment_status", sa.String(32), nullable=False, server_default="unpaid"),
        sa.Column("reimbursable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("billing_code", sa.String(32), nullable=True),
        sa.Column("approval_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_expenses_matter_id", "expenses", ["matter_id"])

    op.create_table(
        "mileage_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("origin", sa.String(255), nullable=True),
        sa.Column("destination", sa.String(255), nullable=True),
        sa.Column("trip_type", sa.String(32), nullable=False, server_default="round_trip"),
        sa.Column("miles", sa.Numeric(10, 2), nullable=False),
        sa.Column("mileage_rate", sa.Numeric(10, 4), nullable=False, server_default="0.67"),
        sa.Column("mileage_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("travel_time_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("approval_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_mileage_entries_matter_id", "mileage_entries", ["matter_id"])

    # Trigram indexes for search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_matters_name_trgm ON matters USING gin (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_emails_subject_trgm ON emails USING gin (subject gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_name_trgm ON documents USING gin (file_name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entities_display_trgm ON entities USING gin (display_name gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entities_display_trgm")
    op.execute("DROP INDEX IF EXISTS ix_documents_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_emails_subject_trgm")
    op.execute("DROP INDEX IF EXISTS ix_matters_name_trgm")
    op.drop_table("mileage_entries")
    op.drop_table("expenses")

"""Expenses, mileage tables + search indexes.

Revision ID: 005_extraction_summaries
Revises: 004_finance_search
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_extraction_summaries"
down_revision: Union[str, None] = "004_finance_search"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("extracted_text", sa.Text(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("ocr_status", sa.String(32), nullable=False, server_default="pending"),
    )
    op.add_column("matters", sa.Column("ai_summary", sa.Text(), nullable=True))
    op.add_column(
        "matters",
        sa.Column("ai_summary_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("matters", "ai_summary_updated_at")
    op.drop_column("matters", "ai_summary")
    op.drop_column("documents", "ocr_status")
    op.drop_column("documents", "extracted_text")

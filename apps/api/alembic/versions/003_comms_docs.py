"""Emails and documents tables.

Revision ID: 003_comms_docs
Revises: 002_domain_core
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_comms_docs"
down_revision: Union[str, None] = "002_domain_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("gmail_message_id", sa.String(128), nullable=False),
        sa.Column("gmail_thread_id", sa.String(128), nullable=True),
        sa.Column("gmail_account", sa.String(320), nullable=False),
        sa.Column("direction", sa.String(32), nullable=False, server_default="incoming"),
        sa.Column("sender", sa.String(512), nullable=True),
        sa.Column("to_recipients", sa.Text(), nullable=True),
        sa.Column("cc_recipients", sa.Text(), nullable=True),
        sa.Column("bcc_recipients", sa.Text(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("labels", postgresql.JSONB(), nullable=True),
        sa.Column("attachment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gmail_message_link", sa.Text(), nullable=True),
        sa.Column("primary_matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("classification_confidence", sa.String(32), nullable=True),
        sa.Column("processing_status", sa.String(32), nullable=False, server_default="indexed"),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("raw_headers", postgresql.JSONB(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("gmail_message_id", "gmail_account", name="uq_emails_gmail_msg_account"),
    )
    op.create_index("ix_emails_gmail_message_id", "emails", ["gmail_message_id"])
    op.create_index("ix_emails_gmail_account", "emails", ["gmail_account"])
    op.create_index("ix_emails_sender", "emails", ["sender"])
    op.create_index("ix_emails_primary_matter_id", "emails", ["primary_matter_id"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_system", sa.String(32), nullable=False),
        sa.Column("source_file_id", sa.String(255), nullable=False),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("current_path", sa.Text(), nullable=True),
        sa.Column("parent_folder", sa.Text(), nullable=True),
        sa.Column("direct_link", sa.Text(), nullable=True),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synchronized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_hash", sa.String(128), nullable=True),
        sa.Column("primary_matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_category", sa.String(64), nullable=True),
        sa.Column("billing_relevance", sa.String(32), nullable=True),
        sa.Column("confidentiality_status", sa.String(32), nullable=False, server_default="standard"),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("classification_confidence", sa.String(32), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("source_system", "source_file_id", name="uq_documents_source_file"),
    )
    op.create_index("ix_documents_source_system", "documents", ["source_system"])
    op.create_index("ix_documents_source_file_id", "documents", ["source_file_id"])
    op.create_index("ix_documents_primary_matter_id", "documents", ["primary_matter_id"])


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("emails")

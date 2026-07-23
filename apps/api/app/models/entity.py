"""Entity and relationship models."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class EntityType(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "entity_types"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Entity(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "entities"

    entity_type_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("entity_types.id"), nullable=False
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    primary_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True, index=True)
    primary_phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    primary_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duplicate_review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="clear"
    )

    entity_type: Mapped["EntityType"] = relationship("EntityType", lazy="joined")
    aliases: Mapped[List["EntityAlias"]] = relationship(
        "EntityAlias", back_populates="entity", cascade="all, delete-orphan", lazy="selectin"
    )
    contacts: Mapped[List["EntityContact"]] = relationship(
        "EntityContact", back_populates="entity", cascade="all, delete-orphan", lazy="selectin"
    )


class EntityAlias(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "entity_aliases"
    __table_args__ = (
        UniqueConstraint("entity_id", "alias", name="uq_entity_aliases_entity_alias"),
    )

    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alias_type: Mapped[str] = mapped_column(String(32), nullable=False, default="aka")

    entity: Mapped["Entity"] = relationship("Entity", back_populates="aliases")


class EntityContact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "entity_contacts"

    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    contact_type: Mapped[str] = mapped_column(String(32), nullable=False)  # email|phone|url
    value: Mapped[str] = mapped_column(String(320), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    entity: Mapped["Entity"] = relationship("Entity", back_populates="contacts")


class MatterEntityRelationship(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "matter_entity_relationships"
    __table_args__ = (
        UniqueConstraint(
            "matter_id",
            "entity_id",
            "role",
            name="uq_matter_entity_rel_matter_entity_role",
        ),
    )

    matter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("matters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    organization_represented: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_user_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    matter = relationship("Matter", lazy="joined")
    entity = relationship("Entity", lazy="joined")

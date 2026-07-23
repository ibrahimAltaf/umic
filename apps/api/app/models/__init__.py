"""SQLAlchemy model exports for Alembic and application use."""

from app.db.base import Base
from app.models.auth import (
    AuditEvent,
    PasswordResetToken,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRole,
    UserSession,
)
from app.models.entity import (
    Entity,
    EntityAlias,
    EntityContact,
    EntityType,
    MatterEntityRelationship,
)
from app.models.matter import (
    BillingClassification,
    Matter,
    MatterAlias,
    MatterStatus,
    MatterType,
)
from app.models.communications import DocumentRecord, EmailRecord
from app.models.finance import Expense, MileageEntry
from app.models.workflow import (
    BillingCode,
    BillingCodeLibrary,
    BillingEntry,
    DiscrepancyAlert,
    IntegrationConnection,
    ReviewQueueItem,
)

__all__ = [
    "Base",
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "RefreshToken",
    "UserSession",
    "PasswordResetToken",
    "AuditEvent",
    "MatterType",
    "MatterStatus",
    "BillingClassification",
    "Matter",
    "MatterAlias",
    "EntityType",
    "Entity",
    "EntityAlias",
    "EntityContact",
    "MatterEntityRelationship",
    "ReviewQueueItem",
    "DiscrepancyAlert",
    "BillingCodeLibrary",
    "BillingCode",
    "BillingEntry",
    "IntegrationConnection",
    "EmailRecord",
    "DocumentRecord",
    "Expense",
    "MileageEntry",
]

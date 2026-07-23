"""Role and permission constants used across authorization checks."""

from enum import StrEnum


class SystemRole(StrEnum):
    SYSTEM_OWNER = "system_owner"
    BILLING_ADMINISTRATOR = "billing_administrator"
    MATTER_ADMINISTRATOR = "matter_administrator"
    STANDARD_USER = "standard_user"
    READ_ONLY_USER = "read_only_user"


class PermissionCode(StrEnum):
    # Users & roles
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_MANAGE = "users:manage"
    ROLES_READ = "roles:read"
    ROLES_MANAGE = "roles:manage"
    PERMISSIONS_READ = "permissions:read"

    # Matters
    MATTERS_READ = "matters:read"
    MATTERS_WRITE = "matters:write"
    MATTERS_DELETE = "matters:delete"
    MATTERS_MANAGE_ACCESS = "matters:manage_access"
    MATTERS_VIEW_PERSONAL = "matters:view_personal"
    MATTERS_VIEW_CONFIDENTIAL = "matters:view_confidential"
    MATTERS_VIEW_PRIVILEGED = "matters:view_privileged"

    # Entities
    ENTITIES_READ = "entities:read"
    ENTITIES_WRITE = "entities:write"
    ENTITIES_DELETE = "entities:delete"

    # Review & audit
    REVIEW_QUEUE_READ = "review_queue:read"
    REVIEW_QUEUE_WRITE = "review_queue:write"
    AUDIT_READ = "audit:read"

    # Integrations & settings
    INTEGRATIONS_READ = "integrations:read"
    INTEGRATIONS_MANAGE = "integrations:manage"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"

    # Billing (foundation)
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    BILLING_APPROVE = "billing:approve"


# Default role → permission mapping for seed data
ROLE_PERMISSION_MAP: dict[SystemRole, list[PermissionCode]] = {
    SystemRole.SYSTEM_OWNER: list(PermissionCode),
    SystemRole.BILLING_ADMINISTRATOR: [
        PermissionCode.USERS_READ,
        PermissionCode.ROLES_READ,
        PermissionCode.PERMISSIONS_READ,
        PermissionCode.MATTERS_READ,
        PermissionCode.MATTERS_WRITE,
        PermissionCode.ENTITIES_READ,
        PermissionCode.ENTITIES_WRITE,
        PermissionCode.REVIEW_QUEUE_READ,
        PermissionCode.REVIEW_QUEUE_WRITE,
        PermissionCode.AUDIT_READ,
        PermissionCode.INTEGRATIONS_READ,
        PermissionCode.SETTINGS_READ,
        PermissionCode.BILLING_READ,
        PermissionCode.BILLING_WRITE,
        PermissionCode.BILLING_APPROVE,
    ],
    SystemRole.MATTER_ADMINISTRATOR: [
        PermissionCode.USERS_READ,
        PermissionCode.ROLES_READ,
        PermissionCode.PERMISSIONS_READ,
        PermissionCode.MATTERS_READ,
        PermissionCode.MATTERS_WRITE,
        PermissionCode.MATTERS_DELETE,
        PermissionCode.MATTERS_MANAGE_ACCESS,
        PermissionCode.MATTERS_VIEW_PERSONAL,
        PermissionCode.MATTERS_VIEW_CONFIDENTIAL,
        PermissionCode.MATTERS_VIEW_PRIVILEGED,
        PermissionCode.ENTITIES_READ,
        PermissionCode.ENTITIES_WRITE,
        PermissionCode.ENTITIES_DELETE,
        PermissionCode.REVIEW_QUEUE_READ,
        PermissionCode.REVIEW_QUEUE_WRITE,
        PermissionCode.AUDIT_READ,
        PermissionCode.INTEGRATIONS_READ,
        PermissionCode.SETTINGS_READ,
        PermissionCode.BILLING_READ,
    ],
    SystemRole.STANDARD_USER: [
        PermissionCode.MATTERS_READ,
        PermissionCode.MATTERS_WRITE,
        PermissionCode.ENTITIES_READ,
        PermissionCode.ENTITIES_WRITE,
        PermissionCode.REVIEW_QUEUE_READ,
        PermissionCode.REVIEW_QUEUE_WRITE,
        PermissionCode.INTEGRATIONS_READ,
        PermissionCode.BILLING_READ,
        PermissionCode.BILLING_WRITE,
    ],
    SystemRole.READ_ONLY_USER: [
        PermissionCode.MATTERS_READ,
        PermissionCode.ENTITIES_READ,
        PermissionCode.REVIEW_QUEUE_READ,
        PermissionCode.AUDIT_READ,
        PermissionCode.INTEGRATIONS_READ,
        PermissionCode.BILLING_READ,
    ],
}

ROLE_DESCRIPTIONS: dict[SystemRole, str] = {
    SystemRole.SYSTEM_OWNER: "Full system access including user and role management",
    SystemRole.BILLING_ADMINISTRATOR: "Manage billing, rates, approvals, and financial data",
    SystemRole.MATTER_ADMINISTRATOR: "Administer matters, entities, and matter-level access",
    SystemRole.STANDARD_USER: "Create and edit assigned matters and related records",
    SystemRole.READ_ONLY_USER: "View authorized records without modification rights",
}

"""Database seed script for development.

Usage (from apps/api):
  python -m app.db.seed
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.permissions import (
    ROLE_DESCRIPTIONS,
    ROLE_PERMISSION_MAP,
    PermissionCode,
    SystemRole,
)
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.auth import Permission, Role, RolePermission, User, UserRole

setup_logging()
logger = get_logger(__name__)


def _permission_meta(code: PermissionCode) -> tuple[str, str, str]:
    resource, action = code.value.split(":", 1)
    name = code.value.replace(":", " ").replace("_", " ").title()
    return name, resource, action


def seed() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        # Permissions
        existing_perm_codes = set(db.scalars(select(Permission.code)).all())
        for code in PermissionCode:
            if code.value in existing_perm_codes:
                continue
            name, resource, action = _permission_meta(code)
            db.add(
                Permission(
                    id=uuid4(),
                    code=code.value,
                    name=name,
                    description=f"Allows {action} on {resource}",
                    resource=resource,
                    action=action,
                )
            )
        db.flush()

        perm_by_code = {
            p.code: p for p in db.scalars(select(Permission)).all()
        }

        # Roles
        for role_enum in SystemRole:
            role = db.scalar(select(Role).where(Role.code == role_enum.value))
            if role is None:
                role = Role(
                    id=uuid4(),
                    code=role_enum.value,
                    name=role_enum.value.replace("_", " ").title(),
                    description=ROLE_DESCRIPTIONS[role_enum],
                    is_system=True,
                    is_active=True,
                )
                db.add(role)
                db.flush()

            desired = {p.value for p in ROLE_PERMISSION_MAP[role_enum]}
            existing_links = {
                rp.permission_id
                for rp in db.scalars(
                    select(RolePermission).where(RolePermission.role_id == role.id)
                ).all()
            }
            existing_codes = {
                code
                for code, perm in perm_by_code.items()
                if perm.id in existing_links
            }
            for code in desired - existing_codes:
                db.add(
                    RolePermission(
                        id=uuid4(),
                        role_id=role.id,
                        permission_id=perm_by_code[code].id,
                    )
                )

        db.flush()

        # Sample users
        sample_users = [
            {
                "email": settings.seed_admin_email.lower(),
                "password": settings.seed_admin_password,
                "first_name": settings.seed_admin_first_name,
                "last_name": settings.seed_admin_last_name,
                "role": SystemRole.SYSTEM_OWNER.value,
            },
            {
                "email": "billing.admin@example.com",
                "password": "ChangeMeBilling123!",
                "first_name": "Billing",
                "last_name": "Admin",
                "role": SystemRole.BILLING_ADMINISTRATOR.value,
            },
            {
                "email": "matter.admin@example.com",
                "password": "ChangeMeMatter123!",
                "first_name": "Matter",
                "last_name": "Admin",
                "role": SystemRole.MATTER_ADMINISTRATOR.value,
            },
            {
                "email": "standard.user@example.com",
                "password": "ChangeMeUser123!",
                "first_name": "Standard",
                "last_name": "User",
                "role": SystemRole.STANDARD_USER.value,
            },
            {
                "email": "readonly.user@example.com",
                "password": "ChangeMeRead123!",
                "first_name": "Read",
                "last_name": "Only",
                "role": SystemRole.READ_ONLY_USER.value,
            },
        ]

        for item in sample_users:
            user = db.scalar(select(User).where(User.email == item["email"]))
            if user is None:
                user = User(
                    id=uuid4(),
                    email=item["email"],
                    password_hash=hash_password(item["password"]),
                    first_name=item["first_name"],
                    last_name=item["last_name"],
                    is_active=True,
                    is_email_verified=True,
                    password_changed_at=datetime.now(timezone.utc),
                )
                db.add(user)
                db.flush()

            role = db.scalar(select(Role).where(Role.code == item["role"]))
            assert role is not None
            link = db.scalar(
                select(UserRole).where(
                    UserRole.user_id == user.id, UserRole.role_id == role.id
                )
            )
            if link is None:
                db.add(
                    UserRole(
                        id=uuid4(),
                        user_id=user.id,
                        role_id=role.id,
                        assigned_by=None,
                    )
                )

        _seed_domain(db)

        db.commit()
        logger.info("Seed completed successfully")
        print("Seed completed successfully")
        print(f"  Admin login: {settings.seed_admin_email}")
        print("  Sample users: billing/matter/standard/readonly @example.com")
    except Exception:
        db.rollback()
        logger.exception("Seed failed")
        raise
    finally:
        db.close()


def _seed_domain(db) -> None:
    from datetime import date, timedelta
    from decimal import Decimal

    from app.models.entity import Entity, EntityType, MatterEntityRelationship
    from app.models.matter import (
        BillingClassification,
        Matter,
        MatterAlias,
        MatterStatus,
        MatterType,
    )
    from app.models.workflow import (
        BillingCode,
        BillingCodeLibrary,
        BillingEntry,
        DiscrepancyAlert,
        IntegrationConnection,
        ReviewQueueItem,
    )

    matter_types = [
        ("property_insurance_claim", "Property Insurance Claim"),
        ("insurance_appraisal", "Insurance Appraisal"),
        ("umpire_assignment", "Umpire Assignment"),
        ("litigation", "Litigation Matter"),
        ("consulting", "Consulting Engagement"),
        ("business_project", "Business Project"),
        ("corporate", "Corporate Matter"),
        ("product_development", "Product Development"),
        ("internal_admin", "Internal Administration"),
        ("personal", "Personal Matter"),
    ]
    for code, name in matter_types:
        if not db.scalar(select(MatterType).where(MatterType.code == code)):
            db.add(MatterType(id=uuid4(), code=code, name=name, is_active=True))

    statuses = [
        ("open", "Open", False, 1),
        ("active", "Active", False, 2),
        ("on_hold", "On Hold", False, 3),
        ("review", "In Review", False, 4),
        ("closed", "Closed", True, 5),
    ]
    for code, name, closed, order in statuses:
        if not db.scalar(select(MatterStatus).where(MatterStatus.code == code)):
            db.add(
                MatterStatus(
                    id=uuid4(), code=code, name=name, is_closed=closed, sort_order=order
                )
            )

    billing = [
        ("billable", "Billable", True),
        ("potentially_billable", "Potentially Billable", False),
        ("nonbillable", "Nonbillable", False),
        ("personal", "Personal", False),
        ("internal_administration", "Internal Administration", False),
        ("product_development", "Product Development", False),
        ("business_development", "Business Development", False),
        ("contingent_deferred", "Contingent or Deferred", False),
        ("closed_to_billing", "Closed to Additional Billing", False),
        ("requires_review", "Requires Review", False),
    ]
    for code, name, allow in billing:
        if not db.scalar(
            select(BillingClassification).where(BillingClassification.code == code)
        ):
            db.add(
                BillingClassification(
                    id=uuid4(),
                    code=code,
                    name=name,
                    allows_proposed_billing=allow,
                )
            )

    entity_types = [
        ("person", "Person", "people"),
        ("company", "Company", "org"),
        ("insurance_carrier", "Insurance Carrier", "org"),
        ("law_firm", "Law Firm", "org"),
        ("attorney", "Attorney", "people"),
        ("appraiser", "Appraiser", "people"),
        ("umpire", "Umpire", "people"),
        ("engineer", "Engineer", "people"),
        ("contractor", "Contractor", "org"),
        ("vendor", "Vendor", "org"),
        ("client", "Client", "org"),
        ("business_entity", "Business Entity", "org"),
    ]
    for code, name, cat in entity_types:
        if not db.scalar(select(EntityType).where(EntityType.code == code)):
            db.add(
                EntityType(id=uuid4(), code=code, name=name, category=cat, is_active=True)
            )

    db.flush()

    # Sample matters
    if not db.scalar(select(Matter).limit(1)):
        mt = db.scalar(select(MatterType).where(MatterType.code == "insurance_appraisal"))
        st = db.scalar(select(MatterStatus).where(MatterStatus.code == "active"))
        bc = db.scalar(select(BillingClassification).where(BillingClassification.code == "billable"))
        m1 = Matter(
            id=uuid4(),
            matter_number="M-2026-00001",
            name="Johnson Residence — Wind Appraisal",
            matter_type_id=mt.id,
            status_id=st.id,
            billing_classification_id=bc.id,
            claim_number="CLM-88421",
            policy_number="POL-22091",
            property_address="1420 Oak Lane, Tampa, FL",
            date_of_loss=date.today() - timedelta(days=45),
            open_date=date.today() - timedelta(days=40),
            hourly_rate=Decimal("200.00"),
            billing_method="hourly",
            is_personal=False,
        )
        db.add(m1)
        db.flush()
        db.add(MatterAlias(id=uuid4(), matter_id=m1.id, alias="Johnson wind", source="seed"))

        mt2 = db.scalar(select(MatterType).where(MatterType.code == "personal"))
        bc2 = db.scalar(select(BillingClassification).where(BillingClassification.code == "personal"))
        m2 = Matter(
            id=uuid4(),
            matter_number="M-2026-00002",
            name="Personal — Household Records",
            matter_type_id=mt2.id,
            status_id=st.id,
            billing_classification_id=bc2.id,
            open_date=date.today() - timedelta(days=10),
            is_personal=True,
            is_confidential=True,
        )
        db.add(m2)

        mt3 = db.scalar(select(MatterType).where(MatterType.code == "litigation"))
        bc3 = db.scalar(
            select(BillingClassification).where(BillingClassification.code == "potentially_billable")
        )
        m3 = Matter(
            id=uuid4(),
            matter_number="M-2026-00003",
            name="Rivera v. Coastal Mutual — Coverage",
            matter_type_id=mt3.id,
            status_id=st.id,
            billing_classification_id=bc3.id,
            case_number="2025-CA-4412",
            claim_number="CLM-90110",
            open_date=date.today() - timedelta(days=120),
            hourly_rate=Decimal("225.00"),
        )
        db.add(m3)
        db.flush()

        et_person = db.scalar(select(EntityType).where(EntityType.code == "person"))
        et_carrier = db.scalar(
            select(EntityType).where(EntityType.code == "insurance_carrier")
        )
        e1 = Entity(
            id=uuid4(),
            entity_type_id=et_person.id,
            legal_name="Sarah Johnson",
            display_name="Sarah Johnson",
            primary_email="sarah.johnson@example.com",
        )
        e2 = Entity(
            id=uuid4(),
            entity_type_id=et_carrier.id,
            legal_name="Coastal Mutual Insurance",
            display_name="Coastal Mutual",
            primary_domain="coastalmutual.example.com",
        )
        db.add_all([e1, e2])
        db.flush()
        db.add(
            MatterEntityRelationship(
                id=uuid4(),
                matter_id=m1.id,
                entity_id=e1.id,
                role="insured",
                is_primary=True,
                is_user_approved=True,
                source="seed",
                confidence="high",
            )
        )
        db.add(
            MatterEntityRelationship(
                id=uuid4(),
                matter_id=m1.id,
                entity_id=e2.id,
                role="insurer",
                is_primary=True,
                is_user_approved=True,
                source="seed",
                confidence="high",
            )
        )

        # Billing libraries
        lib1 = BillingCodeLibrary(
            id=uuid4(), code="litigation", name="Litigation / Work Product"
        )
        lib2 = BillingCodeLibrary(
            id=uuid4(), code="general", name="General Time Sheet"
        )
        db.add_all([lib1, lib2])
        db.flush()
        for code, desc in [
            ("EM", "Emails"),
            ("TC", "Telephone calls"),
            ("IN", "Inspection attendance"),
            ("TR", "Travel"),
            ("RP", "Report review"),
            ("ES", "Estimate preparation"),
        ]:
            db.add(
                BillingCode(id=uuid4(), library_id=lib2.id, code=code, description=desc)
            )
        for code, desc in [
            ("IC", "Initial conference with counsel"),
            ("DR", "Docket review"),
            ("PM", "Pleading and motion review"),
            ("CR", "Correspondence review"),
        ]:
            db.add(
                BillingCode(id=uuid4(), library_id=lib1.id, code=code, description=desc)
            )
        db.flush()
        em = db.scalar(
            select(BillingCode).where(BillingCode.code == "EM", BillingCode.library_id == lib2.id)
        )
        entry = BillingEntry(
            id=uuid4(),
            matter_id=m1.id,
            activity_date=date.today() - timedelta(days=2),
            code_id=em.id if em else None,
            description="Email from SC to JB",
            details="Follow-up regarding status of appraisal estimate.",
            time_charge=Decimal("0.20"),
            hourly_rate=Decimal("200.00"),
            time_amount=Decimal("40.00"),
            total_amount=Decimal("40.00"),
            billing_status="proposed",
            approval_status="pending",
            source_type="manual",
        )
        db.add(entry)
        db.add(
            BillingEntry(
                id=uuid4(),
                matter_id=m1.id,
                activity_date=date.today() - timedelta(days=5),
                description="Inspection attendance",
                details="On-site inspection of roof and exterior.",
                time_charge=Decimal("2.50"),
                hourly_rate=Decimal("200.00"),
                time_amount=Decimal("500.00"),
                total_amount=Decimal("500.00"),
                billing_status="approved",
                approval_status="approved",
                source_type="manual",
            )
        )

        # Review queue sample
        for col, title, itype, pri in [
            ("inbox", "Unassigned email — claim CLM-88421", "unassigned_email", "high"),
            ("inbox", "Low-confidence matter match on Drive file", "low_confidence_match", "medium"),
            ("in_progress", "Possible duplicate PDF estimate", "possible_duplicate", "medium"),
            ("review", "Date requires review — imported receipt", "date_review", "low"),
            ("done", "Sync error resolved — Dropbox token refresh", "sync_error", "low"),
        ]:
            db.add(
                ReviewQueueItem(
                    id=uuid4(),
                    item_type=itype,
                    priority=pri,
                    status="open" if col != "done" else "resolved",
                    title=title,
                    explanation="Seeded sample for Kanban board.",
                    suggested_action="Review and associate to matter",
                    matter_id=m1.id if col != "done" else None,
                    kanban_column=col,
                )
            )

        for provider, label in [
            ("gmail", "Primary Gmail"),
            ("google_drive", "Shared Drive"),
            ("dropbox", "Matter Dropbox"),
            ("google_sheets", "T&E FOR CHAT FINAL"),
        ]:
            db.add(
                IntegrationConnection(
                    id=uuid4(),
                    provider=provider,
                    account_label=label,
                    status="disconnected",
                )
            )

    if not db.scalar(select(DiscrepancyAlert).limit(1)):
        sample_matter = db.scalar(select(Matter).limit(1))
        if sample_matter:
            db.add(
                DiscrepancyAlert(
                    id=uuid4(),
                    matter_id=sample_matter.id,
                    field_name="claim_number",
                    approved_value=sample_matter.claim_number or "CLM-88421",
                    imported_value="CLM-88421-IMPORTED",
                    source="gmail",
                    status="open",
                    notes="Seeded sample — imported email claim number differs from approved matter.",
                )
            )


if __name__ == "__main__":
    seed()

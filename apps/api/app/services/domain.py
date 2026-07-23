"""Entity, review, billing, and dashboard services."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationAppError
from app.core.permissions import PermissionCode
from app.models.auth import AuditEvent, User
from app.models.entity import Entity, EntityAlias, EntityType, MatterEntityRelationship
from app.models.matter import BillingClassification, Matter, MatterStatus
from app.models.workflow import (
    BillingCode,
    BillingCodeLibrary,
    BillingEntry,
    IntegrationConnection,
    ReviewQueueItem,
)
from app.schemas.domain import (
    BillingEntryCreate,
    BillingEntryOut,
    DashboardStats,
    EntityCreate,
    EntityOut,
    EntityUpdate,
    RelationshipCreate,
    RelationshipOut,
    ReviewItemOut,
    ReviewItemUpdate,
)
from app.services.audit import AuditService


def _entity_out(e: Entity) -> EntityOut:
    return EntityOut(
        id=e.id,
        legal_name=e.legal_name,
        display_name=e.display_name,
        status=e.status,
        primary_email=e.primary_email,
        primary_phone=e.primary_phone,
        primary_domain=e.primary_domain,
        notes=e.notes,
        created_at=e.created_at,
        entity_type=e.entity_type,
        aliases=[a.alias for a in e.aliases],
    )


class EntityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def list_entities(
        self, *, user: User, page: int = 1, page_size: int = 20, search: Optional[str] = None
    ) -> dict:
        if not user.has_permission(PermissionCode.ENTITIES_READ):
            raise AuthorizationError("Cannot list entities")
        base = (
            select(Entity)
            .where(Entity.is_deleted.is_(False))
            .options(selectinload(Entity.aliases), selectinload(Entity.entity_type))
        )
        count = select(func.count()).select_from(Entity).where(Entity.is_deleted.is_(False))
        if search:
            pattern = f"%{search}%"
            filt = or_(
                Entity.legal_name.ilike(pattern),
                Entity.display_name.ilike(pattern),
                Entity.primary_email.ilike(pattern),
            )
            base = base.where(filt)
            count = count.where(filt)
        total = self.db.scalar(count) or 0
        rows = self.db.scalars(
            base.order_by(Entity.display_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return {
            "items": [_entity_out(e) for e in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size else 0,
        }

    def get(self, entity_id: UUID, *, user: User) -> EntityOut:
        if not user.has_permission(PermissionCode.ENTITIES_READ):
            raise AuthorizationError("Cannot view entities")
        return _entity_out(self._get(entity_id))

    def create(self, data: EntityCreate, *, user: User) -> EntityOut:
        if not user.has_permission(PermissionCode.ENTITIES_WRITE):
            raise AuthorizationError("Cannot create entities")
        etype = self.db.scalar(select(EntityType).where(EntityType.code == data.entity_type_code))
        if not etype:
            raise ValidationAppError("Invalid entity type")
        entity = Entity(
            id=uuid4(),
            entity_type_id=etype.id,
            legal_name=data.legal_name.strip(),
            display_name=(data.display_name or data.legal_name).strip(),
            primary_email=data.primary_email,
            primary_phone=data.primary_phone,
            primary_domain=data.primary_domain,
            notes=data.notes,
        )
        self.db.add(entity)
        self.db.flush()
        for alias in data.aliases:
            if alias.strip():
                self.db.add(
                    EntityAlias(id=uuid4(), entity_id=entity.id, alias=alias.strip())
                )
        self.audit.log(
            action="entity.created",
            actor_user_id=user.id,
            record_type="entity",
            record_id=entity.id,
            new_value={"display_name": entity.display_name},
        )
        self.db.commit()
        return _entity_out(self._get(entity.id))

    def update(self, entity_id: UUID, data: EntityUpdate, *, user: User) -> EntityOut:
        if not user.has_permission(PermissionCode.ENTITIES_WRITE):
            raise AuthorizationError("Cannot update entities")
        e = self._get(entity_id)
        for field in (
            "legal_name",
            "display_name",
            "primary_email",
            "primary_phone",
            "primary_domain",
            "notes",
            "status",
        ):
            val = getattr(data, field)
            if val is not None:
                setattr(e, field, val)
        self.db.add(e)
        self.audit.log(
            action="entity.updated",
            actor_user_id=user.id,
            record_type="entity",
            record_id=e.id,
        )
        self.db.commit()
        return _entity_out(self._get(e.id))

    def create_relationship(self, data: RelationshipCreate, *, user: User) -> RelationshipOut:
        if not user.has_permission(PermissionCode.ENTITIES_WRITE):
            raise AuthorizationError("Cannot create relationships")
        rel = MatterEntityRelationship(
            id=uuid4(),
            matter_id=data.matter_id,
            entity_id=data.entity_id,
            role=data.role,
            organization_represented=data.organization_represented,
            is_primary=data.is_primary,
            source=data.source,
            confidence=data.confidence,
            is_user_approved=data.is_user_approved,
            notes=data.notes,
        )
        self.db.add(rel)
        self.audit.log(
            action="relationship.created",
            actor_user_id=user.id,
            record_type="matter_entity_relationship",
            record_id=rel.id,
            matter_id=data.matter_id,
        )
        self.db.commit()
        self.db.refresh(rel)
        return RelationshipOut(
            id=rel.id,
            matter_id=rel.matter_id,
            entity_id=rel.entity_id,
            role=rel.role,
            organization_represented=rel.organization_represented,
            is_primary=rel.is_primary,
            source=rel.source,
            confidence=rel.confidence,
            is_user_approved=rel.is_user_approved,
            notes=rel.notes,
            matter_name=rel.matter.name if rel.matter else None,
            entity_name=rel.entity.display_name if rel.entity else None,
        )

    def delete_relationship(self, relationship_id: UUID, *, user: User) -> dict:
        if not user.has_permission(PermissionCode.ENTITIES_WRITE):
            raise AuthorizationError("Cannot delete relationships")
        rel = self.db.get(MatterEntityRelationship, relationship_id)
        if not rel:
            raise NotFoundError("Relationship not found")
        matter_id = rel.matter_id
        self.db.delete(rel)
        self.audit.log(
            action="relationship.deleted",
            actor_user_id=user.id,
            record_type="matter_entity_relationship",
            record_id=relationship_id,
            matter_id=matter_id,
        )
        self.db.commit()
        return {"status": "deleted", "id": str(relationship_id)}

    def list_types(self):
        return self.db.scalars(select(EntityType).where(EntityType.is_active.is_(True))).all()

    def _get(self, entity_id: UUID) -> Entity:
        e = self.db.scalar(
            select(Entity)
            .where(Entity.id == entity_id, Entity.is_deleted.is_(False))
            .options(selectinload(Entity.aliases), selectinload(Entity.entity_type))
        )
        if not e:
            raise NotFoundError("Entity not found")
        return e


class ReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def list_items(self, *, user: User, status: Optional[str] = None) -> list[ReviewItemOut]:
        if not user.has_permission(PermissionCode.REVIEW_QUEUE_READ):
            raise AuthorizationError("Cannot view review queue")
        stmt = select(ReviewQueueItem).order_by(ReviewQueueItem.created_at.desc())
        if status:
            stmt = stmt.where(ReviewQueueItem.status == status)
        return [ReviewItemOut.model_validate(i) for i in self.db.scalars(stmt).all()]

    def update(self, item_id: UUID, data: ReviewItemUpdate, *, user: User) -> ReviewItemOut:
        if not user.has_permission(PermissionCode.REVIEW_QUEUE_WRITE):
            raise AuthorizationError("Cannot update review queue")
        item = self.db.get(ReviewQueueItem, item_id)
        if not item:
            raise NotFoundError("Review item not found")
        if data.status is not None:
            item.status = data.status
            if data.status in {"resolved", "rejected"}:
                item.resolved_at = datetime.now(timezone.utc)
                item.resolved_by_id = user.id
        if data.kanban_column is not None:
            item.kanban_column = data.kanban_column
        if data.resolution is not None:
            item.resolution = data.resolution
        if data.assigned_user_id is not None:
            item.assigned_user_id = data.assigned_user_id
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return ReviewItemOut.model_validate(item)


class BillingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def list_entries(
        self, *, user: User, approval_status: Optional[str] = None, page: int = 1, page_size: int = 50
    ) -> dict:
        if not user.has_permission(PermissionCode.BILLING_READ):
            raise AuthorizationError("Cannot view billing")
        stmt = (
            select(BillingEntry)
            .where(BillingEntry.is_deleted.is_(False))
            .options(selectinload(BillingEntry.matter), selectinload(BillingEntry.code))
            .order_by(BillingEntry.activity_date.desc())
        )
        count = select(func.count()).select_from(BillingEntry).where(
            BillingEntry.is_deleted.is_(False)
        )
        if approval_status:
            stmt = stmt.where(BillingEntry.approval_status == approval_status)
            count = count.where(BillingEntry.approval_status == approval_status)
        total = self.db.scalar(count) or 0
        rows = self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        return {
            "items": [self._out(e) for e in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size else 0,
        }

    def create(self, data: BillingEntryCreate, *, user: User) -> BillingEntryOut:
        if not user.has_permission(PermissionCode.BILLING_WRITE):
            raise AuthorizationError("Cannot create billing entries")
        matter = self.db.get(Matter, data.matter_id)
        if not matter or matter.is_deleted:
            raise NotFoundError("Matter not found")
        classification = self.db.get(BillingClassification, matter.billing_classification_id)
        if classification and not classification.allows_proposed_billing and not data.is_manual_override:
            raise ValidationAppError(
                "Matter is not billable — only Billable matters generate proposed entries"
            )

        code_id = None
        if data.code:
            lib = self.db.scalar(
                select(BillingCodeLibrary).where(
                    BillingCodeLibrary.code == (data.library_code or "general")
                )
            )
            if lib:
                code_row = self.db.scalar(
                    select(BillingCode).where(
                        BillingCode.library_id == lib.id, BillingCode.code == data.code
                    )
                )
                if code_row:
                    code_id = code_row.id

        rate = data.hourly_rate or matter.hourly_rate or Decimal("200.00")
        time_amount = (
            (data.time_charge * rate).quantize(Decimal("0.01"))
            if data.time_charge is not None
            else None
        )
        total = Decimal("0.00")
        if time_amount:
            total += time_amount
        if data.cost_incurred:
            total += data.cost_incurred

        entry = BillingEntry(
            id=uuid4(),
            matter_id=data.matter_id,
            activity_date=data.activity_date,
            code_id=code_id,
            description=data.description,
            details=data.details,
            time_charge=data.time_charge,
            mileage=data.mileage,
            cost_incurred=data.cost_incurred,
            hourly_rate=rate,
            time_amount=time_amount,
            total_amount=total,
            billing_status="proposed",
            approval_status="pending",
            is_manual_override=data.is_manual_override,
            notes=data.notes,
            created_by_id=user.id,
        )
        self.db.add(entry)
        self.audit.log(
            action="billing_entry.proposed",
            actor_user_id=user.id,
            record_type="billing_entry",
            record_id=entry.id,
            matter_id=data.matter_id,
            approval_status="pending",
        )
        self.db.commit()
        return self._out(self.db.get(BillingEntry, entry.id))

    def approve(self, entry_id: UUID, *, user: User, reason: Optional[str] = None) -> BillingEntryOut:
        if not user.has_permission(PermissionCode.BILLING_APPROVE):
            raise AuthorizationError("Cannot approve billing")
        entry = self.db.get(BillingEntry, entry_id)
        if not entry:
            raise NotFoundError("Billing entry not found")
        entry.approval_status = "approved"
        entry.billing_status = "approved"
        entry.approved_at = datetime.now(timezone.utc)
        entry.approved_by_id = user.id
        self.db.add(entry)
        self.audit.log(
            action="billing_entry.approved",
            actor_user_id=user.id,
            record_type="billing_entry",
            record_id=entry.id,
            matter_id=entry.matter_id,
            reason=reason,
            approval_status="approved",
        )
        self.db.commit()
        return self._out(entry)

    def reject(self, entry_id: UUID, *, user: User, reason: Optional[str] = None) -> BillingEntryOut:
        if not user.has_permission(PermissionCode.BILLING_APPROVE):
            raise AuthorizationError("Cannot reject billing")
        entry = self.db.get(BillingEntry, entry_id)
        if not entry:
            raise NotFoundError("Billing entry not found")
        entry.approval_status = "rejected"
        entry.billing_status = "rejected"
        self.db.add(entry)
        self.audit.log(
            action="billing_entry.rejected",
            actor_user_id=user.id,
            record_type="billing_entry",
            record_id=entry.id,
            matter_id=entry.matter_id,
            reason=reason,
            approval_status="rejected",
        )
        self.db.commit()
        return self._out(entry)

    def list_codes(self, *, user: User) -> list[dict]:
        if not user.has_permission(PermissionCode.BILLING_READ):
            raise AuthorizationError("Cannot view billing codes")
        libs = self.db.scalars(select(BillingCodeLibrary)).all()
        result = []
        for lib in libs:
            codes = self.db.scalars(
                select(BillingCode).where(
                    BillingCode.library_id == lib.id, BillingCode.is_active.is_(True)
                )
            ).all()
            result.append(
                {
                    "library": {"code": lib.code, "name": lib.name},
                    "codes": [{"code": c.code, "description": c.description} for c in codes],
                }
            )
        return result

    def _out(self, e: BillingEntry) -> BillingEntryOut:
        return BillingEntryOut(
            id=e.id,
            matter_id=e.matter_id,
            activity_date=e.activity_date,
            description=e.description,
            details=e.details,
            time_charge=e.time_charge,
            mileage=e.mileage,
            cost_incurred=e.cost_incurred,
            hourly_rate=e.hourly_rate,
            time_amount=e.time_amount,
            total_amount=e.total_amount,
            billing_status=e.billing_status,
            approval_status=e.approval_status,
            invoice_status=e.invoice_status,
            created_at=e.created_at,
            matter_name=e.matter.name if e.matter else None,
            code=e.code.code if e.code else None,
        )


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def stats(self, *, user: User) -> DashboardStats:
        can_personal = user.has_permission(PermissionCode.MATTERS_VIEW_PERSONAL) or user.has_role(
            "system_owner"
        )
        matter_filter = [Matter.is_deleted.is_(False)]
        if not can_personal:
            matter_filter.append(Matter.is_personal.is_(False))

        active = self.db.scalar(
            select(func.count())
            .select_from(Matter)
            .join(MatterStatus)
            .where(*matter_filter, MatterStatus.is_closed.is_(False))
        ) or 0
        personal = self.db.scalar(
            select(func.count()).select_from(Matter).where(*matter_filter, Matter.is_personal.is_(True))
        ) or 0
        billable = self.db.scalar(
            select(func.count())
            .select_from(Matter)
            .join(BillingClassification)
            .where(*matter_filter, BillingClassification.code == "billable")
        ) or 0
        open_review = self.db.scalar(
            select(func.count())
            .select_from(ReviewQueueItem)
            .where(ReviewQueueItem.status == "open")
        ) or 0
        pending_billing = self.db.scalar(
            select(func.count())
            .select_from(BillingEntry)
            .where(
                BillingEntry.is_deleted.is_(False),
                BillingEntry.approval_status == "pending",
            )
        ) or 0
        approved_total = self.db.scalar(
            select(func.coalesce(func.sum(BillingEntry.total_amount), 0)).where(
                BillingEntry.is_deleted.is_(False),
                BillingEntry.approval_status == "approved",
            )
        ) or Decimal("0")
        entities_count = self.db.scalar(
            select(func.count()).select_from(Entity).where(Entity.is_deleted.is_(False))
        ) or 0
        integrations = self.db.scalar(
            select(func.count())
            .select_from(IntegrationConnection)
            .where(IntegrationConnection.status == "connected")
        ) or 0

        status_rows = self.db.execute(
            select(MatterStatus.name, func.count(Matter.id))
            .join(Matter, Matter.status_id == MatterStatus.id)
            .where(*matter_filter)
            .group_by(MatterStatus.name)
        ).all()
        review_rows = self.db.execute(
            select(ReviewQueueItem.kanban_column, func.count(ReviewQueueItem.id)).group_by(
                ReviewQueueItem.kanban_column
            )
        ).all()
        month_rows = self.db.execute(
            select(
                extract("month", BillingEntry.activity_date).label("month"),
                func.coalesce(func.sum(BillingEntry.total_amount), 0),
            )
            .where(
                BillingEntry.is_deleted.is_(False),
                extract("year", BillingEntry.activity_date) == date.today().year,
            )
            .group_by("month")
            .order_by("month")
        ).all()

        return DashboardStats(
            active_matters=active,
            personal_matters=personal,
            billable_matters=billable,
            open_review_items=open_review,
            pending_billing_entries=pending_billing,
            approved_billing_total=Decimal(str(approved_total)),
            entities_count=entities_count,
            integrations_connected=integrations,
            matters_by_status=[{"name": n, "value": int(v)} for n, v in status_rows],
            billing_by_month=[
                {"month": int(m), "total": float(t)} for m, t in month_rows
            ],
            review_by_column=[{"column": c, "value": int(v)} for c, v in review_rows],
        )


class AuditQueryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_events(self, *, user: User, page: int = 1, page_size: int = 50) -> dict:
        if not user.has_permission(PermissionCode.AUDIT_READ):
            raise AuthorizationError("Cannot view audit")
        total = self.db.scalar(select(func.count()).select_from(AuditEvent)) or 0
        rows = self.db.scalars(
            select(AuditEvent)
            .order_by(AuditEvent.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return {
            "items": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size else 0,
        }


class IntegrationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_connections(self, *, user: User):
        if not user.has_permission(PermissionCode.INTEGRATIONS_READ):
            raise AuthorizationError("Cannot view integrations")
        return self.db.scalars(
            select(IntegrationConnection).order_by(IntegrationConnection.provider)
        ).all()

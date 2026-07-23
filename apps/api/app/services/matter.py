"""Matter domain service."""

from datetime import date
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationAppError
from app.core.permissions import PermissionCode
from app.models.auth import User
from app.models.matter import (
    BillingClassification,
    Matter,
    MatterAlias,
    MatterStatus,
    MatterType,
)
from app.schemas.domain import MatterCreate, MatterOut, MatterUpdate
from app.services.audit import AuditService


def _matter_out(m: Matter) -> MatterOut:
    return MatterOut(
        id=m.id,
        matter_number=m.matter_number,
        name=m.name,
        claim_number=m.claim_number,
        policy_number=m.policy_number,
        case_number=m.case_number,
        appraisal_number=m.appraisal_number,
        property_address=m.property_address,
        date_of_loss=m.date_of_loss,
        open_date=m.open_date,
        closed_date=m.closed_date,
        hourly_rate=m.hourly_rate,
        billing_method=m.billing_method,
        is_confidential=m.is_confidential,
        is_privileged=m.is_privileged,
        is_personal=m.is_personal,
        notes=m.notes,
        created_at=m.created_at,
        matter_type=m.matter_type,
        status=m.status,
        billing_classification=m.billing_classification,
        aliases=[a.alias for a in m.aliases],
    )


class MatterService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def _can_view_personal(self, user: User) -> bool:
        return user.has_permission(PermissionCode.MATTERS_VIEW_PERSONAL) or user.has_role(
            "system_owner"
        )

    def _can_view_confidential(self, user: User) -> bool:
        return user.has_permission(PermissionCode.MATTERS_VIEW_CONFIDENTIAL) or user.has_role(
            "system_owner"
        )

    def _can_view_privileged(self, user: User) -> bool:
        return user.has_permission(PermissionCode.MATTERS_VIEW_PRIVILEGED) or user.has_role(
            "system_owner"
        )

    def _visible_filter(self, user: User):
        from sqlalchemy import and_

        parts = []
        if not self._can_view_personal(user):
            parts.append(Matter.is_personal.is_(False))
        if not self._can_view_confidential(user):
            parts.append(Matter.is_confidential.is_(False))
        if not self._can_view_privileged(user):
            parts.append(Matter.is_privileged.is_(False))
        if not parts:
            return True
        return and_(*parts)

    def assert_can_view(self, matter: Matter, user: User) -> None:
        if matter.is_personal and not self._can_view_personal(user):
            raise AuthorizationError("Personal matter access denied")
        if matter.is_confidential and not self._can_view_confidential(user):
            raise AuthorizationError("Confidential matter access denied")
        if matter.is_privileged and not self._can_view_privileged(user):
            raise AuthorizationError("Privileged matter access denied")

    def list_matters(
        self,
        *,
        user: User,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status_code: Optional[str] = None,
        billing_code: Optional[str] = None,
    ) -> dict:
        if not user.has_permission(PermissionCode.MATTERS_READ):
            raise AuthorizationError("Cannot list matters")

        base = (
            select(Matter)
            .where(Matter.is_deleted.is_(False), self._visible_filter(user))
            .options(
                selectinload(Matter.aliases),
                selectinload(Matter.matter_type),
                selectinload(Matter.status),
                selectinload(Matter.billing_classification),
            )
        )
        count = (
            select(func.count())
            .select_from(Matter)
            .where(Matter.is_deleted.is_(False), self._visible_filter(user))
        )

        if search:
            pattern = f"%{search}%"
            filt = or_(
                Matter.name.ilike(pattern),
                Matter.matter_number.ilike(pattern),
                Matter.claim_number.ilike(pattern),
                Matter.policy_number.ilike(pattern),
                Matter.case_number.ilike(pattern),
                Matter.property_address.ilike(pattern),
            )
            base = base.where(filt)
            count = count.where(filt)

        if status_code:
            base = base.join(MatterStatus).where(MatterStatus.code == status_code)
            count = count.join(MatterStatus).where(MatterStatus.code == status_code)
        if billing_code:
            base = base.join(BillingClassification).where(
                BillingClassification.code == billing_code
            )
            count = count.join(BillingClassification).where(
                BillingClassification.code == billing_code
            )

        total = self.db.scalar(count) or 0
        rows = self.db.scalars(
            base.order_by(Matter.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return {
            "items": [_matter_out(m) for m in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size else 0,
        }

    def get(self, matter_id: UUID, *, user: User) -> MatterOut:
        if not user.has_permission(PermissionCode.MATTERS_READ):
            raise AuthorizationError("Cannot view matters")
        m = self._get(matter_id)
        self.assert_can_view(m, user)
        return _matter_out(m)

    def create(self, data: MatterCreate, *, user: User) -> MatterOut:
        if not user.has_permission(PermissionCode.MATTERS_WRITE):
            raise AuthorizationError("Cannot create matters")
        if data.is_personal and not self._can_view_personal(user):
            raise AuthorizationError("Cannot create personal matters")

        mtype = self._type_by_code(data.matter_type_code)
        status = self._status_by_code(data.status_code)
        billing = self._billing_by_code(data.billing_classification_code)

        matter = Matter(
            id=uuid4(),
            matter_number=self._next_matter_number(),
            name=data.name.strip(),
            matter_type_id=mtype.id,
            status_id=status.id,
            billing_classification_id=billing.id,
            claim_number=data.claim_number,
            policy_number=data.policy_number,
            case_number=data.case_number,
            appraisal_number=data.appraisal_number,
            property_address=data.property_address,
            date_of_loss=data.date_of_loss,
            date_of_discovery=data.date_of_discovery,
            open_date=data.open_date or date.today(),
            hourly_rate=data.hourly_rate,
            billing_method=data.billing_method,
            is_confidential=data.is_confidential,
            is_privileged=data.is_privileged,
            is_personal=data.is_personal,
            notes=data.notes,
            search_keywords=data.search_keywords,
            created_by_id=user.id,
        )
        self.db.add(matter)
        self.db.flush()
        for alias in data.aliases:
            if alias.strip():
                self.db.add(
                    MatterAlias(id=uuid4(), matter_id=matter.id, alias=alias.strip(), source="manual")
                )
        self.audit.log(
            action="matter.created",
            actor_user_id=user.id,
            record_type="matter",
            record_id=matter.id,
            matter_id=matter.id,
            new_value={"name": matter.name, "matter_number": matter.matter_number},
        )
        self.db.commit()
        return _matter_out(self._get(matter.id))

    def update(self, matter_id: UUID, data: MatterUpdate, *, user: User) -> MatterOut:
        if not user.has_permission(PermissionCode.MATTERS_WRITE):
            raise AuthorizationError("Cannot update matters")
        m = self._get(matter_id)
        self.assert_can_view(m, user)

        previous = {"name": m.name, "status": m.status.code}
        if data.name is not None:
            m.name = data.name.strip()
        if data.status_code is not None:
            m.status_id = self._status_by_code(data.status_code).id
        if data.billing_classification_code is not None:
            m.billing_classification_id = self._billing_by_code(
                data.billing_classification_code
            ).id
        for field in (
            "claim_number",
            "policy_number",
            "case_number",
            "appraisal_number",
            "property_address",
            "date_of_loss",
            "date_of_discovery",
            "open_date",
            "closed_date",
            "hourly_rate",
            "billing_method",
            "is_confidential",
            "is_privileged",
            "is_personal",
            "notes",
            "search_keywords",
            "dropbox_folder_link",
            "google_drive_folder_link",
            "time_expense_sheet_link",
        ):
            val = getattr(data, field)
            if val is not None:
                setattr(m, field, val)

        self.db.add(m)
        self.audit.log(
            action="matter.updated",
            actor_user_id=user.id,
            record_type="matter",
            record_id=m.id,
            matter_id=m.id,
            previous_value=previous,
            new_value={"name": m.name},
        )
        self.db.commit()
        return _matter_out(self._get(m.id))

    def reference_data(self) -> dict:
        types = self.db.scalars(select(MatterType).where(MatterType.is_active.is_(True))).all()
        statuses = self.db.scalars(
            select(MatterStatus).order_by(MatterStatus.sort_order)
        ).all()
        billing = self.db.scalars(select(BillingClassification)).all()
        return {
            "matter_types": types,
            "statuses": statuses,
            "billing_classifications": billing,
        }

    def _get(self, matter_id: UUID) -> Matter:
        m = self.db.scalar(
            select(Matter)
            .where(Matter.id == matter_id, Matter.is_deleted.is_(False))
            .options(
                selectinload(Matter.aliases),
                selectinload(Matter.matter_type),
                selectinload(Matter.status),
                selectinload(Matter.billing_classification),
            )
        )
        if not m:
            raise NotFoundError("Matter not found")
        return m

    def _type_by_code(self, code: str) -> MatterType:
        row = self.db.scalar(select(MatterType).where(MatterType.code == code))
        if not row:
            raise ValidationAppError(f"Invalid matter type: {code}")
        return row

    def _status_by_code(self, code: str) -> MatterStatus:
        row = self.db.scalar(select(MatterStatus).where(MatterStatus.code == code))
        if not row:
            raise ValidationAppError(f"Invalid matter status: {code}")
        return row

    def _billing_by_code(self, code: str) -> BillingClassification:
        row = self.db.scalar(
            select(BillingClassification).where(BillingClassification.code == code)
        )
        if not row:
            raise ValidationAppError(f"Invalid billing classification: {code}")
        return row

    def _next_matter_number(self) -> str:
        count = self.db.scalar(select(func.count()).select_from(Matter)) or 0
        return f"M-{date.today().year}-{count + 1:05d}"

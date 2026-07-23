"""Discrepancy alerts service."""

from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.permissions import PermissionCode
from app.core.exceptions import AuthorizationError
from app.models.auth import User
from app.models.matter import Matter
from app.models.workflow import DiscrepancyAlert
from app.services.audit import AuditService


class DiscrepancyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def list_alerts(
        self, *, user: User, matter_id: Optional[UUID] = None, status: Optional[str] = "open"
    ) -> list[dict]:
        if not user.has_permission(PermissionCode.REVIEW_QUEUE_READ):
            raise AuthorizationError("Cannot view discrepancies")
        stmt = select(DiscrepancyAlert).order_by(DiscrepancyAlert.created_at.desc())
        if matter_id:
            stmt = stmt.where(DiscrepancyAlert.matter_id == matter_id)
        if status:
            stmt = stmt.where(DiscrepancyAlert.status == status)
        rows = self.db.scalars(stmt.limit(200)).all()
        out: list[dict] = []
        for r in rows:
            item = self._out(r)
            matter = self.db.get(Matter, r.matter_id)
            item["matter_name"] = matter.name if matter else None
            item["matter_number"] = matter.matter_number if matter else None
            out.append(item)
        return out

    def create(
        self,
        *,
        user: User,
        matter_id: UUID,
        field_name: str,
        approved_value: Optional[str],
        imported_value: Optional[str],
        source: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        matter = self.db.get(Matter, matter_id)
        if not matter or matter.is_deleted:
            raise NotFoundError("Matter not found")
        row = DiscrepancyAlert(
            id=uuid4(),
            matter_id=matter_id,
            field_name=field_name,
            approved_value=approved_value,
            imported_value=imported_value,
            source=source,
            status="open",
            notes=notes,
        )
        self.db.add(row)
        self.audit.log(
            action="discrepancy.created",
            actor_user_id=user.id,
            record_type="discrepancy_alert",
            record_id=row.id,
            matter_id=matter_id,
            new_value={"field": field_name, "imported": imported_value},
        )
        self.db.commit()
        self.db.refresh(row)
        return self._out(row)

    def resolve(self, alert_id: UUID, *, user: User, notes: Optional[str] = None) -> dict:
        if not user.has_permission(PermissionCode.REVIEW_QUEUE_WRITE):
            raise AuthorizationError("Cannot resolve discrepancies")
        row = self.db.get(DiscrepancyAlert, alert_id)
        if not row:
            raise NotFoundError("Discrepancy not found")
        row.status = "resolved"
        if notes:
            row.notes = ((row.notes or "") + "\n" + notes).strip()
        self.db.add(row)
        self.audit.log(
            action="discrepancy.resolved",
            actor_user_id=user.id,
            record_type="discrepancy_alert",
            record_id=row.id,
            matter_id=row.matter_id,
        )
        self.db.commit()
        self.db.refresh(row)
        return self._out(row)

    def check_matter_import_signals(
        self, *, matter_id: UUID, signals: dict[str, str], source: str, user_id=None
    ) -> int:
        """Create alerts when imported signal conflicts with approved matter fields."""
        matter = self.db.get(Matter, matter_id)
        if not matter:
            return 0
        created = 0
        pairs = [
            ("claim_number", matter.claim_number, signals.get("claim_number")),
            ("policy_number", matter.policy_number, signals.get("policy_number")),
            ("case_number", matter.case_number, signals.get("case_number")),
        ]
        for field, approved, imported in pairs:
            if not approved or not imported:
                continue
            if approved.strip().lower() == imported.strip().lower():
                continue
            existing = self.db.scalar(
                select(DiscrepancyAlert).where(
                    DiscrepancyAlert.matter_id == matter_id,
                    DiscrepancyAlert.field_name == field,
                    DiscrepancyAlert.status == "open",
                    DiscrepancyAlert.imported_value == imported,
                )
            )
            if existing:
                continue
            self.db.add(
                DiscrepancyAlert(
                    id=uuid4(),
                    matter_id=matter_id,
                    field_name=field,
                    approved_value=approved,
                    imported_value=imported,
                    source=source,
                    status="open",
                    notes="Imported value differs from approved matter record",
                )
            )
            created += 1
        if created:
            self.db.flush()
        return created

    @staticmethod
    def _out(r: DiscrepancyAlert) -> dict:
        return {
            "id": str(r.id),
            "matter_id": str(r.matter_id),
            "field_name": r.field_name,
            "approved_value": r.approved_value,
            "imported_value": r.imported_value,
            "source": r.source,
            "status": r.status,
            "notes": r.notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

"""Expenses, mileage, matter billing totals, Google Sheets T&E export."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.auth import User
from app.models.communications import DocumentRecord, EmailRecord
from app.models.finance import Expense, MileageEntry
from app.models.matter import Matter
from app.models.workflow import BillingEntry
from app.services.audit import AuditService
from app.services.integrations.google import GoogleIntegrationService

SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_CREATE = "https://www.googleapis.com/drive/v3/files"


class FinanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.google = GoogleIntegrationService(db)

    def matter_overview(self, matter_id: UUID, *, user: User) -> dict:
        """Full matter file dossier — emails, docs, billing, expenses, review, entities."""
        from app.models.entity import MatterEntityRelationship
        from app.models.workflow import DiscrepancyAlert, ReviewQueueItem

        matter = self.db.get(Matter, matter_id)
        if not matter or matter.is_deleted:
            raise NotFoundError("Matter not found")

        billing_total = self.db.scalar(
            select(func.coalesce(func.sum(BillingEntry.total_amount), 0)).where(
                BillingEntry.matter_id == matter_id,
                BillingEntry.approval_status == "approved",
                BillingEntry.is_deleted.is_(False),
            )
        ) or Decimal("0")
        billing_pending = self.db.scalar(
            select(func.coalesce(func.sum(BillingEntry.total_amount), 0)).where(
                BillingEntry.matter_id == matter_id,
                BillingEntry.approval_status == "pending",
                BillingEntry.is_deleted.is_(False),
            )
        ) or Decimal("0")
        expense_total = self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.matter_id == matter_id,
                Expense.approval_status == "approved",
                Expense.is_deleted.is_(False),
            )
        ) or Decimal("0")
        mileage_total = self.db.scalar(
            select(func.coalesce(func.sum(MileageEntry.mileage_amount), 0)).where(
                MileageEntry.matter_id == matter_id,
                MileageEntry.approval_status == "approved",
                MileageEntry.is_deleted.is_(False),
            )
        ) or Decimal("0")

        emails = self.db.scalars(
            select(EmailRecord)
            .where(
                EmailRecord.primary_matter_id == matter_id,
                EmailRecord.is_deleted.is_(False),
            )
            .order_by(EmailRecord.received_at.desc().nullslast())
            .limit(200)
        ).all()
        docs = self.db.scalars(
            select(DocumentRecord)
            .where(
                DocumentRecord.primary_matter_id == matter_id,
                DocumentRecord.is_deleted.is_(False),
            )
            .order_by(DocumentRecord.source_modified_at.desc().nullslast())
            .limit(200)
        ).all()
        billing = self.db.scalars(
            select(BillingEntry)
            .where(
                BillingEntry.matter_id == matter_id,
                BillingEntry.is_deleted.is_(False),
            )
            .order_by(BillingEntry.activity_date.desc())
            .limit(200)
        ).all()
        expenses = self.db.scalars(
            select(Expense)
            .where(Expense.matter_id == matter_id, Expense.is_deleted.is_(False))
            .order_by(Expense.created_at.desc())
            .limit(200)
        ).all()
        mileage = self.db.scalars(
            select(MileageEntry)
            .where(MileageEntry.matter_id == matter_id, MileageEntry.is_deleted.is_(False))
            .order_by(MileageEntry.activity_date.desc())
            .limit(200)
        ).all()
        review = self.db.scalars(
            select(ReviewQueueItem)
            .where(
                ReviewQueueItem.matter_id == matter_id,
                ReviewQueueItem.status != "resolved",
            )
            .order_by(ReviewQueueItem.created_at.desc())
            .limit(100)
        ).all()
        # also review items linked by related email/doc ids
        email_ids = [e.id for e in emails]
        doc_ids = [d.id for d in docs]
        related_review = []
        if email_ids or doc_ids:
            related_review = list(
                self.db.scalars(
                    select(ReviewQueueItem).where(
                        ReviewQueueItem.status == "open",
                        ReviewQueueItem.related_record_id.in_([*email_ids, *doc_ids]),
                    ).limit(50)
                ).all()
            )
        review_map = {r.id: r for r in [*review, *related_review]}

        relationships = self.db.scalars(
            select(MatterEntityRelationship)
            .where(MatterEntityRelationship.matter_id == matter_id)
            .limit(100)
        ).all()

        # Unassigned pool for attach-from-matter UI
        unassigned_emails = self.db.scalars(
            select(EmailRecord)
            .where(
                EmailRecord.is_deleted.is_(False),
                EmailRecord.primary_matter_id.is_(None),
            )
            .order_by(EmailRecord.received_at.desc().nullslast())
            .limit(30)
        ).all()
        unassigned_docs = self.db.scalars(
            select(DocumentRecord)
            .where(
                DocumentRecord.is_deleted.is_(False),
                DocumentRecord.primary_matter_id.is_(None),
            )
            .order_by(DocumentRecord.source_modified_at.desc().nullslast())
            .limit(30)
        ).all()
        discrepancies = self.db.scalars(
            select(DiscrepancyAlert)
            .where(
                DiscrepancyAlert.matter_id == matter_id,
                DiscrepancyAlert.status == "open",
            )
            .order_by(DiscrepancyAlert.created_at.desc())
            .limit(50)
        ).all()

        return {
            "matter_id": str(matter_id),
            "totals": {
                "approved_billing": float(billing_total),
                "pending_billing": float(billing_pending),
                "approved_expenses": float(expense_total),
                "approved_mileage": float(mileage_total),
                "grand_total": float(billing_total + expense_total + mileage_total),
            },
            "counts": {
                "emails": len(emails),
                "documents": len(docs),
                "billing": len(billing),
                "expenses": len(expenses),
                "mileage": len(mileage),
                "review": len(review_map),
                "entities": len(relationships),
                "discrepancies": len(discrepancies),
            },
            "discrepancies": [
                {
                    "id": str(d.id),
                    "field_name": d.field_name,
                    "approved_value": d.approved_value,
                    "imported_value": d.imported_value,
                    "source": d.source,
                    "status": d.status,
                    "notes": d.notes,
                }
                for d in discrepancies
            ],
            "emails": [
                {
                    "id": str(e.id),
                    "subject": e.subject,
                    "sender": e.sender,
                    "snippet": e.snippet,
                    "direction": e.direction,
                    "received_at": e.received_at.isoformat() if e.received_at else None,
                    "link": e.gmail_message_link,
                    "attachment_count": e.attachment_count,
                    "review_status": e.review_status,
                    "confidence": e.classification_confidence,
                }
                for e in emails
            ],
            "documents": [
                {
                    "id": str(d.id),
                    "file_name": d.file_name,
                    "source_system": d.source_system,
                    "path": d.current_path,
                    "mime_type": d.mime_type,
                    "file_size": d.file_size,
                    "link": d.direct_link,
                    "modified_at": d.source_modified_at.isoformat()
                    if d.source_modified_at
                    else None,
                    "review_status": d.review_status,
                    "has_text": bool(d.extracted_text),
                    "confidence": d.classification_confidence,
                }
                for d in docs
            ],
            "billing": [
                {
                    "id": str(b.id),
                    "activity_date": b.activity_date.isoformat(),
                    "description": b.description,
                    "time_charge": float(b.time_charge) if b.time_charge is not None else None,
                    "total_amount": float(b.total_amount) if b.total_amount is not None else None,
                    "approval_status": b.approval_status,
                    "billing_status": b.billing_status,
                    "code": b.code.code if b.code else None,
                }
                for b in billing
            ],
            "expenses": [self._expense_out(e) for e in expenses],
            "mileage": [self._mileage_out(m) for m in mileage],
            "review_items": [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "item_type": r.item_type,
                    "priority": r.priority,
                    "status": r.status,
                    "kanban_column": r.kanban_column,
                    "explanation": r.explanation,
                    "suggested_action": r.suggested_action,
                }
                for r in review_map.values()
            ],
            "entities": [
                {
                    "relationship_id": str(rel.id),
                    "id": str(rel.entity_id),
                    "display_name": rel.entity.display_name if rel.entity else None,
                    "role": rel.role,
                    "is_primary": rel.is_primary,
                }
                for rel in relationships
            ],
            "unassigned_emails": [
                {
                    "id": str(e.id),
                    "subject": e.subject,
                    "sender": e.sender,
                    "received_at": e.received_at.isoformat() if e.received_at else None,
                }
                for e in unassigned_emails
            ],
            "unassigned_documents": [
                {
                    "id": str(d.id),
                    "file_name": d.file_name,
                    "source_system": d.source_system,
                }
                for d in unassigned_docs
            ],
            # backwards compatible aliases
            "recent_emails": [
                {
                    "id": str(e.id),
                    "subject": e.subject,
                    "sender": e.sender,
                    "received_at": e.received_at.isoformat() if e.received_at else None,
                    "link": e.gmail_message_link,
                }
                for e in emails[:10]
            ],
            "recent_documents": [
                {
                    "id": str(d.id),
                    "file_name": d.file_name,
                    "source_system": d.source_system,
                    "link": d.direct_link,
                }
                for d in docs[:10]
            ],
        }

    def list_expenses(self, *, matter_id: Optional[UUID] = None, page: int = 1, page_size: int = 50) -> dict:
        q = select(Expense).where(Expense.is_deleted.is_(False))
        cq = select(func.count()).select_from(Expense).where(Expense.is_deleted.is_(False))
        if matter_id:
            q = q.where(Expense.matter_id == matter_id)
            cq = cq.where(Expense.matter_id == matter_id)
        total = self.db.scalar(cq) or 0
        rows = self.db.scalars(
            q.order_by(Expense.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return {
            "items": [self._expense_out(e) for e in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def create_expense(self, data: dict, *, user: User) -> dict:
        matter = self.db.get(Matter, data["matter_id"])
        if not matter or matter.is_deleted:
            raise NotFoundError("Matter not found")
        if not matter.billing_classification or not matter.billing_classification.allows_proposed_billing:
            # still allow expense records; flag note
            pass
        row = Expense(
            id=uuid4(),
            matter_id=data["matter_id"],
            vendor=data.get("vendor"),
            invoice_date=data.get("invoice_date"),
            invoice_number=data.get("invoice_number"),
            category=data.get("category") or "general",
            amount=Decimal(str(data["amount"])),
            tax=Decimal(str(data["tax"])) if data.get("tax") is not None else None,
            payment_status=data.get("payment_status") or "unpaid",
            reimbursable=bool(data.get("reimbursable", True)),
            billing_code=data.get("billing_code"),
            notes=data.get("notes"),
            created_by_id=user.id,
            approval_status="pending",
        )
        self.db.add(row)
        self.audit.log(
            action="expense.created",
            actor_user_id=user.id,
            record_type="expense",
            record_id=row.id,
            new_value={"amount": str(row.amount), "matter_id": str(row.matter_id)},
        )
        self.db.commit()
        self.db.refresh(row)
        return self._expense_out(row)

    def decide_expense(self, expense_id: UUID, *, approve: bool, user: User) -> dict:
        row = self.db.get(Expense, expense_id)
        if not row or row.is_deleted:
            raise NotFoundError("Expense not found")
        row.approval_status = "approved" if approve else "rejected"
        row.approved_by_id = user.id
        row.approved_at = datetime.now(timezone.utc)
        self.db.add(row)
        self.audit.log(
            action="expense.approved" if approve else "expense.rejected",
            actor_user_id=user.id,
            record_type="expense",
            record_id=row.id,
        )
        self.db.commit()
        self.db.refresh(row)
        return self._expense_out(row)

    def list_mileage(self, *, matter_id: Optional[UUID] = None, page: int = 1, page_size: int = 50) -> dict:
        q = select(MileageEntry).where(MileageEntry.is_deleted.is_(False))
        cq = select(func.count()).select_from(MileageEntry).where(MileageEntry.is_deleted.is_(False))
        if matter_id:
            q = q.where(MileageEntry.matter_id == matter_id)
            cq = cq.where(MileageEntry.matter_id == matter_id)
        total = self.db.scalar(cq) or 0
        rows = self.db.scalars(
            q.order_by(MileageEntry.activity_date.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return {
            "items": [self._mileage_out(m) for m in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def create_mileage(self, data: dict, *, user: User) -> dict:
        matter = self.db.get(Matter, data["matter_id"])
        if not matter or matter.is_deleted:
            raise NotFoundError("Matter not found")
        miles = Decimal(str(data["miles"]))
        rate = Decimal(str(data.get("mileage_rate") or "0.67"))
        amount = (miles * rate).quantize(Decimal("0.01"))
        row = MileageEntry(
            id=uuid4(),
            matter_id=data["matter_id"],
            activity_date=data["activity_date"],
            origin=data.get("origin"),
            destination=data.get("destination"),
            trip_type=data.get("trip_type") or "round_trip",
            miles=miles,
            mileage_rate=rate,
            mileage_amount=amount,
            travel_time_hours=Decimal(str(data["travel_time_hours"]))
            if data.get("travel_time_hours") is not None
            else None,
            notes=data.get("notes"),
            created_by_id=user.id,
            approval_status="pending",
        )
        self.db.add(row)
        self.audit.log(
            action="mileage.created",
            actor_user_id=user.id,
            record_type="mileage_entry",
            record_id=row.id,
            new_value={"miles": str(miles), "amount": str(amount)},
        )
        self.db.commit()
        self.db.refresh(row)
        return self._mileage_out(row)

    def decide_mileage(self, entry_id: UUID, *, approve: bool, user: User) -> dict:
        row = self.db.get(MileageEntry, entry_id)
        if not row or row.is_deleted:
            raise NotFoundError("Mileage entry not found")
        row.approval_status = "approved" if approve else "rejected"
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._mileage_out(row)

    def export_te_sheet(self, *, matter_id: UUID, user: User, spreadsheet_id: Optional[str] = None) -> dict:
        """Export approved time, expenses, mileage to Google Sheets."""
        matter = self.db.get(Matter, matter_id)
        if not matter or matter.is_deleted:
            raise NotFoundError("Matter not found")

        billing = self.db.scalars(
            select(BillingEntry).where(
                BillingEntry.matter_id == matter_id,
                BillingEntry.approval_status == "approved",
                BillingEntry.is_deleted.is_(False),
            )
        ).all()
        expenses = self.db.scalars(
            select(Expense).where(
                Expense.matter_id == matter_id,
                Expense.approval_status == "approved",
                Expense.is_deleted.is_(False),
            )
        ).all()
        mileage = self.db.scalars(
            select(MileageEntry).where(
                MileageEntry.matter_id == matter_id,
                MileageEntry.approval_status == "approved",
                MileageEntry.is_deleted.is_(False),
            )
        ).all()

        rows: list[list[str]] = [
            [
                "Type",
                "Date",
                "Description",
                "Code",
                "Hours/Miles",
                "Rate",
                "Amount",
                "Matter",
            ]
        ]
        for b in billing:
            rows.append(
                [
                    "Time",
                    b.activity_date.isoformat() if b.activity_date else "",
                    b.description or "",
                    b.code.code if b.code else "",
                    str(b.time_charge or ""),
                    str(b.hourly_rate or ""),
                    str(b.total_amount or b.time_amount or ""),
                    matter.matter_number,
                ]
            )
        for e in expenses:
            rows.append(
                [
                    "Expense",
                    e.invoice_date.isoformat() if e.invoice_date else "",
                    f"{e.vendor or ''} {e.notes or ''}".strip(),
                    e.billing_code or e.category,
                    "",
                    "",
                    str(e.amount),
                    matter.matter_number,
                ]
            )
        for m in mileage:
            rows.append(
                [
                    "Mileage",
                    m.activity_date.isoformat(),
                    f"{m.origin or ''} → {m.destination or ''}",
                    "MILEAGE",
                    str(m.miles),
                    str(m.mileage_rate),
                    str(m.mileage_amount),
                    matter.matter_number,
                ]
            )

        access = self.google.get_valid_access_token("google_sheets")
        with httpx.Client(timeout=60.0) as client:
            if not spreadsheet_id:
                create = client.post(
                    DRIVE_CREATE,
                    headers={
                        "Authorization": f"Bearer {access}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "name": f"UMIC T&E — {matter.matter_number} — {date.today().isoformat()}",
                        "mimeType": "application/vnd.google-apps.spreadsheet",
                    },
                )
                if create.status_code >= 400:
                    # try sheets scope via google_drive token as fallback
                    try:
                        access = self.google.get_valid_access_token("google_drive")
                    except Exception:  # noqa: BLE001
                        pass
                    create = client.post(
                        DRIVE_CREATE,
                        headers={
                            "Authorization": f"Bearer {access}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "name": f"UMIC T&E — {matter.matter_number} — {date.today().isoformat()}",
                            "mimeType": "application/vnd.google-apps.spreadsheet",
                        },
                    )
                if create.status_code >= 400:
                    raise ValidationAppError(
                        "Could not create spreadsheet. Reconnect Google Sheets with write access "
                        f"({create.status_code}): {create.text[:200]}"
                    )
                spreadsheet_id = create.json()["id"]

            update = client.put(
                f"{SHEETS_API}/{spreadsheet_id}/values/Sheet1!A1",
                params={"valueInputOption": "RAW"},
                headers={
                    "Authorization": f"Bearer {access}",
                    "Content-Type": "application/json",
                },
                json={"values": rows},
            )
            if update.status_code >= 400:
                raise ValidationAppError(
                    f"Sheets write failed ({update.status_code}): {update.text[:200]}"
                )

        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        self.audit.log(
            action="billing.te_export",
            actor_user_id=user.id,
            record_type="matter",
            record_id=matter_id,
            new_value={"spreadsheet_id": spreadsheet_id, "rows": len(rows) - 1},
            source="google_sheets",
        )
        self.db.commit()
        return {
            "status": "ok",
            "spreadsheet_id": spreadsheet_id,
            "url": url,
            "rows_exported": len(rows) - 1,
        }

    def find_duplicate_documents(self) -> dict:
        """Group documents that share the same file_hash."""
        hashed = self.db.scalars(
            select(DocumentRecord).where(
                DocumentRecord.is_deleted.is_(False),
                DocumentRecord.file_hash.isnot(None),
            )
        ).all()
        groups: dict[str, list] = {}
        for d in hashed:
            groups.setdefault(d.file_hash, []).append(d)
        duplicates = [
            {
                "file_hash": h,
                "count": len(items),
                "files": [
                    {
                        "id": str(d.id),
                        "file_name": d.file_name,
                        "source_system": d.source_system,
                        "path": d.current_path,
                    }
                    for d in items
                ],
            }
            for h, items in groups.items()
            if len(items) > 1
        ]
        return {"duplicate_groups": duplicates, "group_count": len(duplicates)}

    @staticmethod
    def _expense_out(e: Expense) -> dict:
        return {
            "id": str(e.id),
            "matter_id": str(e.matter_id),
            "matter_name": e.matter.name if e.matter else None,
            "vendor": e.vendor,
            "invoice_date": e.invoice_date.isoformat() if e.invoice_date else None,
            "invoice_number": e.invoice_number,
            "category": e.category,
            "amount": float(e.amount),
            "tax": float(e.tax) if e.tax is not None else None,
            "payment_status": e.payment_status,
            "reimbursable": e.reimbursable,
            "billing_code": e.billing_code,
            "approval_status": e.approval_status,
            "notes": e.notes,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }

    @staticmethod
    def _mileage_out(m: MileageEntry) -> dict:
        return {
            "id": str(m.id),
            "matter_id": str(m.matter_id),
            "matter_name": m.matter.name if m.matter else None,
            "activity_date": m.activity_date.isoformat(),
            "origin": m.origin,
            "destination": m.destination,
            "trip_type": m.trip_type,
            "miles": float(m.miles),
            "mileage_rate": float(m.mileage_rate),
            "mileage_amount": float(m.mileage_amount),
            "travel_time_hours": float(m.travel_time_hours) if m.travel_time_hours is not None else None,
            "approval_status": m.approval_status,
            "notes": m.notes,
        }

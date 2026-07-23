"""Matter AI summaries + document re-extraction endpoints."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.core.permissions import PermissionCode
from app.dependencies.auth import DbSession, require_permissions
from app.models.auth import User
from app.models.communications import DocumentRecord, EmailRecord
from app.models.finance import Expense, MileageEntry
from app.models.matter import Matter
from app.models.workflow import BillingEntry
from app.services.ai.provider import SummarizationRequest, get_ai_provider
from app.services.audit import AuditService

router = APIRouter(tags=["Intelligence"])


@router.post("/matters/{matter_id}/summary")
async def generate_matter_summary(
    matter_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
) -> dict:
    matter = db.get(Matter, matter_id)
    if not matter or matter.is_deleted:
        raise NotFoundError("Matter not found")

    emails = db.scalars(
        select(EmailRecord)
        .where(
            EmailRecord.primary_matter_id == matter_id,
            EmailRecord.is_deleted.is_(False),
        )
        .order_by(EmailRecord.received_at.desc().nullslast())
        .limit(15)
    ).all()
    docs = db.scalars(
        select(DocumentRecord)
        .where(
            DocumentRecord.primary_matter_id == matter_id,
            DocumentRecord.is_deleted.is_(False),
        )
        .limit(15)
    ).all()
    billing_n = db.scalar(
        select(BillingEntry).where(
            BillingEntry.matter_id == matter_id,
            BillingEntry.is_deleted.is_(False),
        ).limit(1)
    )
    expense_n = len(
        db.scalars(
            select(Expense).where(
                Expense.matter_id == matter_id,
                Expense.is_deleted.is_(False),
            ).limit(20)
        ).all()
    )
    mileage_n = len(
        db.scalars(
            select(MileageEntry).where(
                MileageEntry.matter_id == matter_id,
                MileageEntry.is_deleted.is_(False),
            ).limit(20)
        ).all()
    )

    chunks = [
        f"Matter {matter.matter_number}: {matter.name}",
        f"Type: {matter.matter_type.name if matter.matter_type else 'n/a'}; "
        f"Status: {matter.status.name if matter.status else 'n/a'}; "
        f"Billing: {matter.billing_classification.name if matter.billing_classification else 'n/a'}",
    ]
    if matter.claim_number:
        chunks.append(f"Claim: {matter.claim_number}")
    if matter.policy_number:
        chunks.append(f"Policy: {matter.policy_number}")
    if matter.notes:
        chunks.append(f"Notes: {matter.notes}")
    chunks.append(f"Linked emails: {len(emails)}; documents: {len(docs)}; "
                  f"expenses: {expense_n}; mileage rows: {mileage_n}; "
                  f"has billing entries: {'yes' if billing_n else 'no'}")
    for e in emails[:8]:
        chunks.append(
            f"Email: {(e.subject or '(no subject)')[:120]} — {(e.snippet or e.body_text or '')[:180]}"
        )
    for d in docs[:8]:
        body = (d.extracted_text or "")[:180]
        chunks.append(f"Document ({d.source_system}): {d.file_name} — {body}")

    blob = "\n".join(chunks)
    result = get_ai_provider().summarize(
        SummarizationRequest(
            text=blob,
            context={"matter_id": str(matter_id), "matter_number": matter.matter_number},
        )
    )
    matter.ai_summary = result.summary
    matter.ai_summary_updated_at = datetime.now(timezone.utc)
    db.add(matter)
    AuditService(db).log(
        action="matter.summary_generated",
        actor_user_id=user.id,
        record_type="matter",
        record_id=matter.id,
        new_value={"provider": result.provider, "chars": len(result.summary)},
    )
    db.commit()
    return {
        "matter_id": str(matter_id),
        "summary": result.summary,
        "provider": result.provider,
        "model": result.model,
        "updated_at": matter.ai_summary_updated_at.isoformat(),
        "sources": {"emails": len(emails), "documents": len(docs)},
    }


@router.get("/matters/{matter_id}/summary")
async def get_matter_summary(
    matter_id: UUID,
    db: DbSession,
    _: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
) -> dict:
    matter = db.get(Matter, matter_id)
    if not matter or matter.is_deleted:
        raise NotFoundError("Matter not found")
    return {
        "matter_id": str(matter_id),
        "summary": matter.ai_summary,
        "updated_at": matter.ai_summary_updated_at.isoformat()
        if matter.ai_summary_updated_at
        else None,
    }


@router.post("/documents/{document_id}/extract")
async def extract_document(
    document_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_WRITE))],
) -> dict:
    """Re-run text extraction for a Drive document when possible."""
    import httpx

    from app.services.extraction import extract_drive_file_text
    from app.services.integrations.google import GoogleIntegrationService

    doc = db.get(DocumentRecord, document_id)
    if not doc or doc.is_deleted:
        raise NotFoundError("Document not found")
    if doc.source_system != "google_drive":
        doc.ocr_status = "unsupported"
        db.add(doc)
        db.commit()
        return {
            "id": str(doc.id),
            "ocr_status": "unsupported",
            "message": "Only Google Drive files support on-demand extract currently",
        }

    google = GoogleIntegrationService(db)
    access = google.get_valid_access_token("google_drive")
    meta = {
        "id": doc.source_file_id,
        "mimeType": doc.mime_type,
        "name": doc.file_name,
    }
    with httpx.Client(timeout=90.0) as client:
        text = extract_drive_file_text(client, access, meta)
    if not text:
        doc.ocr_status = "failed"
        db.add(doc)
        db.commit()
        return {"id": str(doc.id), "ocr_status": "failed", "chars": 0}

    doc.extracted_text = text
    doc.ocr_status = "extracted"
    db.add(doc)
    AuditService(db).log(
        action="document.extracted",
        actor_user_id=user.id,
        record_type="document",
        record_id=doc.id,
        new_value={"chars": len(text)},
    )
    db.commit()
    return {"id": str(doc.id), "ocr_status": "extracted", "chars": len(text), "preview": text[:400]}


@router.post("/documents/extract-batch")
async def extract_documents_batch(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_WRITE))],
    limit: int = 40,
) -> dict:
    """Extract text for Drive documents that still need OCR/text."""
    import httpx
    from sqlalchemy import select

    from app.services.extraction import extract_drive_file_text
    from app.services.integrations.google import GoogleIntegrationService

    docs = db.scalars(
        select(DocumentRecord)
        .where(
            DocumentRecord.is_deleted.is_(False),
            DocumentRecord.source_system == "google_drive",
            DocumentRecord.ocr_status.in_(["pending", "failed"]),
        )
        .limit(limit)
    ).all()
    if not docs:
        return {"status": "ok", "scanned": 0, "extracted": 0, "failed": 0}

    google = GoogleIntegrationService(db)
    access = google.get_valid_access_token("google_drive")
    extracted = 0
    failed = 0
    with httpx.Client(timeout=90.0) as client:
        for doc in docs:
            meta = {
                "id": doc.source_file_id,
                "mimeType": doc.mime_type,
                "name": doc.file_name,
            }
            text = extract_drive_file_text(client, access, meta)
            if text:
                doc.extracted_text = text
                doc.ocr_status = "extracted"
                extracted += 1
            else:
                doc.ocr_status = "failed"
                failed += 1
            db.add(doc)
    AuditService(db).log(
        action="documents.extract_batch",
        actor_user_id=user.id,
        record_type="document",
        new_value={"extracted": extracted, "failed": failed, "scanned": len(docs)},
    )
    db.commit()
    return {
        "status": "ok",
        "scanned": len(docs),
        "extracted": extracted,
        "failed": failed,
    }

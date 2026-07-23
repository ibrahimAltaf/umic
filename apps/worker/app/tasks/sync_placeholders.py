"""Background sync tasks — call SyncService / extraction services."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure apps/api is importable when worker runs locally
_ROOT = Path(__file__).resolve().parents[4]
_API = _ROOT / "apps" / "api"
for candidate in (os.environ.get("API_APP_PATH"), str(_API), "/app/api"):
    if candidate and candidate not in sys.path and Path(candidate).is_dir():
        sys.path.insert(0, candidate)
        break

from app.celery_app.celery import celery


@celery.task(name="integrations.gmail.sync", bind=True, max_retries=5)
def sync_gmail(self, connection_id: str | None = None, max_results: int = 100) -> dict:
    from app.db.session import SessionLocal
    from app.services.sync import SyncService

    db = SessionLocal()
    try:
        return SyncService(db).sync_gmail(max_results=max_results)
    finally:
        db.close()


@celery.task(name="integrations.dropbox.sync", bind=True, max_retries=5)
def sync_dropbox(self, connection_id: str | None = None, limit: int = 200) -> dict:
    from app.db.session import SessionLocal
    from app.services.sync import SyncService

    db = SessionLocal()
    try:
        return SyncService(db).sync_dropbox(limit=limit)
    finally:
        db.close()


@celery.task(name="integrations.google_drive.sync", bind=True, max_retries=5)
def sync_google_drive(self, connection_id: str | None = None, max_results: int = 100) -> dict:
    from app.db.session import SessionLocal
    from app.services.sync import SyncService

    db = SessionLocal()
    try:
        return SyncService(db).sync_google_drive(max_results=max_results)
    finally:
        db.close()


@celery.task(name="documents.extract_text", bind=True, max_retries=5)
def extract_document_text(self, document_id: str) -> dict:
    import httpx
    from uuid import UUID

    from app.db.session import SessionLocal
    from app.models.communications import DocumentRecord
    from app.services.extraction import extract_drive_file_text, extract_pdf_bytes
    from app.services.integrations.google import GoogleIntegrationService

    db = SessionLocal()
    try:
        doc = db.get(DocumentRecord, UUID(document_id))
        if not doc or doc.is_deleted:
            return {"status": "missing", "document_id": document_id}
        text = None
        if doc.source_system == "google_drive" and doc.source_file_id:
            google = GoogleIntegrationService(db)
            access = google.get_valid_access_token("google_drive")
            meta = {"id": doc.source_file_id, "mimeType": doc.mime_type, "name": doc.file_name}
            with httpx.Client(timeout=90.0) as client:
                text = extract_drive_file_text(client, access, meta)
        if not text and doc.mime_type == "application/pdf" and doc.direct_link:
            # Best-effort: nothing more without bytes
            pass
        if text:
            doc.extracted_text = text
            doc.ocr_status = "extracted"
            db.add(doc)
            db.commit()
            return {"status": "extracted", "document_id": document_id, "chars": len(text)}
        doc.ocr_status = "failed"
        db.add(doc)
        db.commit()
        return {"status": "failed", "document_id": document_id}
    finally:
        db.close()


@celery.task(name="matters.associate", bind=True, max_retries=3)
def associate_matter(self, record_type: str, record_id: str) -> dict:
    from uuid import UUID

    from app.db.session import SessionLocal
    from app.services.sync import SyncService

    db = SessionLocal()
    try:
        svc = SyncService(db)
        if record_type == "email":
            # Re-run association suggestions via sync helper if present
            return {
                "status": "ok",
                "record_type": record_type,
                "record_id": record_id,
                "message": "Use POST /integrations/emails/{id}/associate for apply",
                "hint": getattr(svc, "suggest_matter_for_email", lambda *_: None)(UUID(record_id)),
            }
        return {
            "status": "ok",
            "record_type": record_type,
            "record_id": record_id,
            "message": "Use POST /integrations/documents/{id}/associate for apply",
        }
    finally:
        db.close()

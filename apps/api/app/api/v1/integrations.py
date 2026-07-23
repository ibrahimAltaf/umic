"""External integration + sync API routes."""

from typing import Annotated, Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.permissions import PermissionCode
from app.dependencies.auth import DbSession, require_permissions
from app.models.auth import User
from app.models.communications import DocumentRecord, EmailRecord
from app.models.matter import Matter
from app.models.workflow import ReviewQueueItem
from app.schemas.domain import IntegrationOut
from app.services.audit import AuditService
from app.services.integrations.google import GoogleIntegrationService
from app.services.sync import SyncService

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class DropboxTokenBody(BaseModel):
    access_token: str = Field(..., min_length=10)


class AssociateBody(BaseModel):
    matter_id: UUID
    confidence: str = "manual"


@router.get("", response_model=list[IntegrationOut])
async def list_integrations(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_READ))],
) -> list[IntegrationOut]:
    rows = GoogleIntegrationService(db).list_connections(user=user)
    return [IntegrationOut.model_validate(c) for c in rows]


@router.get("/google/status")
async def google_status(
    _: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_READ))],
) -> dict:
    settings = get_settings()
    return {
        "configured": settings.google_configured,
        "api_key_configured": bool(settings.google_api_key),
        "redirect_uri": settings.google_redirect_uri,
        "dropbox_configured": settings.dropbox_configured,
        "dropbox_oauth_configured": bool(
            settings.dropbox_app_key and settings.dropbox_app_secret
        ),
    }


@router.post("/google/connect")
async def google_connect(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_MANAGE))],
    provider: str = Query("gmail", pattern="^(gmail|google_drive|google_sheets|google)$"),
) -> dict:
    return GoogleIntegrationService(db).start_oauth(user=user, provider=provider)


@router.get("/google/callback")
async def google_callback(
    db: DbSession,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
) -> RedirectResponse:
    frontend = get_settings().cors_origin_list[0] if get_settings().cors_origin_list else "http://localhost:3000"
    if error:
        return RedirectResponse(f"{frontend}/integrations?google=error&message={quote(error)}")
    if not code or not state:
        return RedirectResponse(f"{frontend}/integrations?google=error&message={quote('missing_code')}")
    try:
        result = GoogleIntegrationService(db).handle_callback(code=code, state=state)
        return RedirectResponse(
            f"{frontend}/integrations?google=connected&provider={quote(result['provider'])}"
            f"&email={quote(result.get('email') or '')}"
        )
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(
            f"{frontend}/integrations?google=error&message={quote(str(exc)[:180])}"
        )


@router.post("/google/{provider}/disconnect")
async def google_disconnect(
    provider: str,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_MANAGE))],
) -> IntegrationOut:
    conn = GoogleIntegrationService(db).disconnect(user=user, provider=provider)
    return IntegrationOut.model_validate(conn)


@router.post("/google/{provider}/test")
async def google_test(
    provider: str,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_READ))],
) -> dict:
    return GoogleIntegrationService(db).test_connection(user=user, provider=provider)


@router.post("/google/gmail/sync")
async def gmail_sync_now(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_MANAGE))],
    max_results: int = Query(100, ge=1, le=2000),
    full: bool = Query(False, description="Paginate through mailbox history up to max_results"),
) -> dict:
    return SyncService(db).sync_gmail(user_id=user.id, max_results=max_results, full=full)


@router.post("/google/drive/sync")
async def drive_sync_now(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_MANAGE))],
    max_results: int = Query(100, ge=1, le=2000),
    full: bool = Query(False, description="Paginate Drive listing up to max_results"),
) -> dict:
    return SyncService(db).sync_google_drive(user_id=user.id, max_results=max_results, full=full)


@router.post("/dropbox/connect-token")
async def dropbox_connect_token(
    body: DropboxTokenBody,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_MANAGE))],
) -> dict:
    return SyncService(db).connect_dropbox_token(user_id=user.id, access_token=body.access_token)


@router.post("/dropbox/oauth/start")
async def dropbox_oauth_start(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_MANAGE))],
) -> dict:
    return SyncService(db).start_dropbox_oauth(user_id=user.id)


@router.get("/dropbox/callback")
async def dropbox_oauth_callback(
    db: DbSession,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
) -> RedirectResponse:
    settings = get_settings()
    web = settings.cors_origin_list[0] if settings.cors_origin_list else "http://localhost:3000"
    if error or not code or not state:
        return RedirectResponse(
            f"{web}/integrations?dropbox=error&message={quote(error or 'missing_code')}"
        )
    try:
        SyncService(db).finish_dropbox_oauth(code=code, state=state)
        return RedirectResponse(f"{web}/integrations?dropbox=connected")
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(
            f"{web}/integrations?dropbox=error&message={quote(str(exc)[:200])}"
        )


@router.post("/dropbox/connect-env")
async def dropbox_connect_env(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_MANAGE))],
) -> dict:
    """Use DROPBOX_ACCESS_TOKEN from server environment."""
    settings = get_settings()
    if not settings.dropbox_access_token:
        from app.core.exceptions import ValidationAppError

        raise ValidationAppError("DROPBOX_ACCESS_TOKEN is not set on the server")
    return SyncService(db).connect_dropbox_token(
        user_id=user.id, access_token=settings.dropbox_access_token
    )


@router.post("/dropbox/sync")
async def dropbox_sync_now(
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.INTEGRATIONS_MANAGE))],
    limit: int = Query(200, ge=1, le=2000),
    full: bool = Query(False),
) -> dict:
    cap = 2000 if full else limit
    return SyncService(db).sync_dropbox(user_id=user.id, limit=cap)


@router.get("/emails")
async def list_emails(
    db: DbSession,
    _: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    total = db.scalar(
        select(func.count()).select_from(EmailRecord).where(EmailRecord.is_deleted.is_(False))
    ) or 0
    rows = db.scalars(
        select(EmailRecord)
        .where(EmailRecord.is_deleted.is_(False))
        .order_by(EmailRecord.received_at.desc().nullslast(), EmailRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": str(e.id),
                "subject": e.subject,
                "sender": e.sender,
                "snippet": e.snippet,
                "direction": e.direction,
                "gmail_account": e.gmail_account,
                "received_at": e.received_at.isoformat() if e.received_at else None,
                "review_status": e.review_status,
                "classification_confidence": e.classification_confidence,
                "primary_matter_id": str(e.primary_matter_id) if e.primary_matter_id else None,
                "matter_name": e.primary_matter.name if e.primary_matter else None,
                "gmail_message_link": e.gmail_message_link,
                "attachment_count": e.attachment_count,
            }
            for e in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/documents")
async def list_documents(
    db: DbSession,
    _: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_READ))],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    source_system: Optional[str] = None,
) -> dict:
    base = select(DocumentRecord).where(DocumentRecord.is_deleted.is_(False))
    count = select(func.count()).select_from(DocumentRecord).where(
        DocumentRecord.is_deleted.is_(False)
    )
    if source_system:
        base = base.where(DocumentRecord.source_system == source_system)
        count = count.where(DocumentRecord.source_system == source_system)
    total = db.scalar(count) or 0
    rows = db.scalars(
        base.order_by(DocumentRecord.source_modified_at.desc().nullslast(), DocumentRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": str(d.id),
                "file_name": d.file_name,
                "source_system": d.source_system,
                "current_path": d.current_path,
                "mime_type": d.mime_type,
                "file_size": d.file_size,
                "direct_link": d.direct_link,
                "review_status": d.review_status,
                "classification_confidence": d.classification_confidence,
                "primary_matter_id": str(d.primary_matter_id) if d.primary_matter_id else None,
                "matter_name": d.primary_matter.name if d.primary_matter else None,
                "file_hash": d.file_hash,
                "has_text": bool(d.extracted_text and d.extracted_text.strip()),
                "source_modified_at": d.source_modified_at.isoformat()
                if d.source_modified_at
                else None,
            }
            for d in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/emails/{email_id}/associate")
async def associate_email(
    email_id: UUID,
    body: AssociateBody,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_WRITE))],
) -> dict:
    email = db.get(EmailRecord, email_id)
    if not email or email.is_deleted:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Email not found")
    matter = db.get(Matter, body.matter_id)
    if not matter or matter.is_deleted:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Matter not found")
    email.primary_matter_id = body.matter_id
    email.classification_confidence = body.confidence
    email.review_status = "approved"
    db.add(email)
    # Discrepancy check from email body/subject vs matter fields
    from app.services.discrepancy import DiscrepancyService
    import re

    blob = f"{email.subject or ''} {email.body_text or ''} {email.snippet or ''}"
    signals = {}
    for key, pattern in (
        ("claim_number", r"(?:claim|clm)[#:\s-]*([A-Z0-9-]{4,})"),
        ("policy_number", r"(?:policy|pol)[#:\s-]*([A-Z0-9-]{4,})"),
        ("case_number", r"(?:case)[#:\s-]*([A-Z0-9-]{4,})"),
    ):
        m = re.search(pattern, blob, re.I)
        if m:
            signals[key] = m.group(1)
    DiscrepancyService(db).check_matter_import_signals(
        matter_id=matter.id, signals=signals, source="gmail", user_id=user.id
    )
    # close related review items
    for item in db.scalars(
        select(ReviewQueueItem).where(
            ReviewQueueItem.related_record_id == email_id,
            ReviewQueueItem.item_type == "unassigned_email",
            ReviewQueueItem.status == "open",
        )
    ).all():
        item.status = "resolved"
        item.resolution = f"Associated to matter {matter.matter_number}"
        item.matter_id = matter.id
        item.resolved_by_id = user.id
        db.add(item)
    AuditService(db).log(
        action="email.associated",
        actor_user_id=user.id,
        record_type="email",
        record_id=email.id,
        new_value={"matter_id": str(body.matter_id)},
    )
    db.commit()
    return {
        "id": str(email.id),
        "primary_matter_id": str(email.primary_matter_id),
        "matter_name": matter.name,
        "review_status": email.review_status,
    }


@router.post("/documents/{document_id}/associate")
async def associate_document(
    document_id: UUID,
    body: AssociateBody,
    db: DbSession,
    user: Annotated[User, Depends(require_permissions(PermissionCode.MATTERS_WRITE))],
) -> dict:
    doc = db.get(DocumentRecord, document_id)
    if not doc or doc.is_deleted:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Document not found")
    matter = db.get(Matter, body.matter_id)
    if not matter or matter.is_deleted:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Matter not found")
    doc.primary_matter_id = body.matter_id
    doc.classification_confidence = body.confidence
    doc.review_status = "approved"
    db.add(doc)
    for item in db.scalars(
        select(ReviewQueueItem).where(
            ReviewQueueItem.related_record_id == document_id,
            ReviewQueueItem.item_type == "unassigned_document",
            ReviewQueueItem.status == "open",
        )
    ).all():
        item.status = "resolved"
        item.resolution = f"Associated to matter {matter.matter_number}"
        item.matter_id = matter.id
        item.resolved_by_id = user.id
        db.add(item)
    AuditService(db).log(
        action="document.associated",
        actor_user_id=user.id,
        record_type="document",
        record_id=doc.id,
        new_value={"matter_id": str(body.matter_id)},
    )
    db.commit()
    return {
        "id": str(doc.id),
        "primary_matter_id": str(doc.primary_matter_id),
        "matter_name": matter.name,
        "review_status": doc.review_status,
    }

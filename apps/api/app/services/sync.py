"""Sync engines: Gmail import, Dropbox import, Drive listing, matter association."""

from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import encrypt_secret
from app.core.exceptions import ConflictError, ValidationAppError
from app.core.logging import get_logger
from app.models.communications import DocumentRecord, EmailRecord
from app.models.matter import Matter
from app.models.workflow import IntegrationConnection, ReviewQueueItem
from app.services.ai.provider import get_ai_provider
from app.services.audit import AuditService
from app.services.integrations.google import GoogleIntegrationService

logger = get_logger(__name__)

DROPBOX_LIST_URL = "https://api.dropboxapi.com/2/files/list_folder"
DROPBOX_CONTINUE_URL = "https://api.dropboxapi.com/2/files/list_folder/continue"
DROPBOX_ACCOUNT_URL = "https://api.dropboxapi.com/2/users/get_current_account"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
GMAIL_MSG_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


def _header_map(payload_headers: list[dict]) -> dict[str, str]:
    return {h.get("name", "").lower(): h.get("value", "") for h in payload_headers or []}


def _extract_body(payload: dict) -> str:
    """Prefer text/plain; fall back to stripped HTML snippet."""
    if not payload:
        return ""
    mime = payload.get("mimeType", "")
    body = payload.get("body") or {}
    data = body.get("data")
    if data and mime.startswith("text/plain"):
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
    parts = payload.get("parts") or []
    plain = ""
    html = ""
    for part in parts:
        plain = plain or _extract_body(part) if part.get("mimeType", "").startswith("text/plain") else plain
        if part.get("mimeType", "").startswith("text/html") and not html:
            b = (part.get("body") or {}).get("data")
            if b:
                html = base64.urlsafe_b64decode(b.encode("utf-8")).decode("utf-8", errors="ignore")
        # nested multipart
        if part.get("parts"):
            nested = _extract_body(part)
            plain = plain or nested
    if plain:
        return plain
    if html:
        return re.sub(r"<[^>]+>", " ", html)[:8000]
    if data:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
    return ""


def _count_attachments(payload: dict) -> int:
    count = 0
    if not payload:
        return 0
    filename = payload.get("filename")
    if filename:
        count += 1
    for part in payload.get("parts") or []:
        count += _count_attachments(part)
    return count


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:  # noqa: BLE001
        return None


class SyncService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.google = GoogleIntegrationService(db)
        self.settings = get_settings()

    # ------------------------------------------------------------------ Gmail
    def sync_gmail(self, *, user_id=None, max_results: int = 100, full: bool = False) -> dict:
        """Import Gmail messages. full=True paginates until max_results (up to 2000)."""
        access = self.google.get_valid_access_token("gmail")
        account = self._gmail_account_email(access)
        imported = 0
        updated = 0
        review_created = 0
        scanned = 0
        page_token: Optional[str] = None
        hard_cap = min(max(max_results, 1), 2000 if full else 500)
        page_size = 100 if full else min(hard_cap, 100)

        with httpx.Client(timeout=90.0) as client:
            while scanned < hard_cap:
                params: dict[str, Any] = {"maxResults": min(page_size, hard_cap - scanned)}
                if page_token:
                    params["pageToken"] = page_token
                list_resp = client.get(
                    GMAIL_MSG_URL,
                    params=params,
                    headers={"Authorization": f"Bearer {access}"},
                )
                list_resp.raise_for_status()
                payload = list_resp.json()
                message_refs = payload.get("messages") or []
                if not message_refs:
                    break

                for ref in message_refs:
                    if scanned >= hard_cap:
                        break
                    mid = ref["id"]
                    detail = client.get(
                        f"{GMAIL_MSG_URL}/{mid}",
                        params={"format": "full"},
                        headers={"Authorization": f"Bearer {access}"},
                    )
                    detail.raise_for_status()
                    msg = detail.json()
                    result = self._upsert_email(msg, account=account)
                    scanned += 1
                    if result == "created":
                        imported += 1
                        if self._maybe_queue_email_review(mid, account):
                            review_created += 1
                    elif result == "updated":
                        updated += 1

                page_token = payload.get("nextPageToken")
                if not page_token or not full:
                    break
                # commit mid-flight so progress is durable on long full syncs
                self.db.commit()

        self.google.mark_sync_result(
            "gmail",
            success=True,
            extra={"imported": imported, "updated": updated, "scanned": scanned, "full": full},
        )
        self.audit.log(
            action="synchronization.completed",
            actor_user_id=user_id,
            record_type="integration_connection",
            source="gmail",
            new_value={
                "imported": imported,
                "updated": updated,
                "review_items": review_created,
                "full": full,
            },
        )
        self.db.commit()
        return {
            "status": "ok",
            "provider": "gmail",
            "account": account,
            "scanned": scanned,
            "imported": imported,
            "updated": updated,
            "review_items_created": review_created,
            "full": full,
        }

    def _gmail_account_email(self, access: str) -> str:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                headers={"Authorization": f"Bearer {access}"},
            )
            resp.raise_for_status()
            return resp.json().get("emailAddress") or "unknown"

    def _upsert_email(self, msg: dict, *, account: str) -> str:
        mid = msg["id"]
        existing = self.db.scalar(
            select(EmailRecord).where(
                EmailRecord.gmail_message_id == mid,
                EmailRecord.gmail_account == account,
            )
        )
        payload = msg.get("payload") or {}
        headers = _header_map(payload.get("headers") or [])
        subject = headers.get("subject")
        sender = headers.get("from")
        to_r = headers.get("to")
        cc_r = headers.get("cc")
        bcc_r = headers.get("bcc")
        date_hdr = headers.get("date")
        label_ids = msg.get("labelIds") or []
        direction = "outgoing" if "SENT" in label_ids else "incoming"
        if "DRAFT" in label_ids:
            direction = "draft"
        body = _extract_body(payload)
        # keep body truncated for storage safety in MVP
        body = (body or "")[:20000]
        association = self._associate_text(
            {
                "subject": subject or "",
                "body": body[:2000],
                "sender": sender or "",
            }
        )
        matter_id = association.get("matter_id")
        confidence = association.get("confidence")

        link = f"https://mail.google.com/mail/u/0/#inbox/{mid}"
        values = dict(
            gmail_thread_id=msg.get("threadId"),
            direction=direction,
            sender=sender,
            to_recipients=to_r,
            cc_recipients=cc_r,
            bcc_recipients=bcc_r,
            subject=subject,
            snippet=msg.get("snippet"),
            body_text=body,
            sent_at=_parse_date(date_hdr),
            received_at=_parse_date(date_hdr),
            labels={"labelIds": label_ids},
            attachment_count=_count_attachments(payload),
            gmail_message_link=link,
            primary_matter_id=matter_id,
            classification_confidence=confidence,
            processing_status="indexed",
            review_status="approved" if matter_id and confidence == "high" else "pending",
            raw_headers={k: headers[k] for k in ("from", "to", "cc", "subject", "date") if k in headers},
        )

        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
            self.db.add(existing)
            return "updated"

        row = EmailRecord(
            id=uuid4(),
            gmail_message_id=mid,
            gmail_account=account,
            **values,
        )
        self.db.add(row)
        self.db.flush()
        return "created"

    def _maybe_queue_email_review(self, gmail_message_id: str, account: str) -> bool:
        email = self.db.scalar(
            select(EmailRecord).where(
                EmailRecord.gmail_message_id == gmail_message_id,
                EmailRecord.gmail_account == account,
            )
        )
        if not email or email.primary_matter_id:
            return False
        if email.classification_confidence in {"high"}:
            return False
        existing = self.db.scalar(
            select(ReviewQueueItem).where(
                ReviewQueueItem.related_record_id == email.id,
                ReviewQueueItem.item_type == "unassigned_email",
                ReviewQueueItem.status == "open",
            )
        )
        if existing:
            return False
        self.db.add(
            ReviewQueueItem(
                id=uuid4(),
                item_type="unassigned_email",
                priority="medium",
                status="open",
                title=f"Unassigned email: {(email.subject or '(no subject)')[:120]}",
                explanation="Imported from Gmail without a high-confidence matter match.",
                suggested_action="Associate to a matter or mark nonbillable/personal",
                related_record_type="email",
                related_record_id=email.id,
                kanban_column="inbox",
            )
        )
        return True

    # --------------------------------------------------------------- Dropbox
    def start_dropbox_oauth(self, *, user_id) -> dict:
        import secrets
        from urllib.parse import urlencode

        if not (self.settings.dropbox_app_key and self.settings.dropbox_app_secret):
            raise ValidationAppError(
                "Set DROPBOX_APP_KEY and DROPBOX_APP_SECRET for OAuth, or paste an access token."
            )
        state = secrets.token_urlsafe(24)
        conn = self.db.scalar(
            select(IntegrationConnection).where(IntegrationConnection.provider == "dropbox")
        )
        if conn is None:
            conn = IntegrationConnection(
                id=uuid4(),
                provider="dropbox",
                account_label="Dropbox",
                status="pending",
            )
            self.db.add(conn)
        meta = dict(conn.token_metadata or {})
        meta["oauth_state"] = state
        meta["initiated_by"] = str(user_id)
        conn.token_metadata = meta
        conn.status = "pending"
        conn.connected_by_id = user_id
        self.db.add(conn)
        self.db.commit()
        params = {
            "client_id": self.settings.dropbox_app_key,
            "response_type": "code",
            "token_access_type": "offline",
            "redirect_uri": self.settings.dropbox_redirect_uri,
            "state": state,
        }
        return {
            "authorize_url": f"https://www.dropbox.com/oauth2/authorize?{urlencode(params)}",
            "state": state,
        }

    def finish_dropbox_oauth(self, *, code: str, state: str) -> dict:
        conn = self.db.scalar(
            select(IntegrationConnection).where(IntegrationConnection.provider == "dropbox")
        )
        if not conn or (conn.token_metadata or {}).get("oauth_state") != state:
            raise ValidationAppError("Invalid Dropbox OAuth state")
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://api.dropboxapi.com/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.settings.dropbox_redirect_uri,
                },
                auth=(self.settings.dropbox_app_key, self.settings.dropbox_app_secret),
            )
            if resp.status_code >= 400:
                raise ValidationAppError(f"Dropbox OAuth failed: {resp.text[:300]}")
            payload = resp.json()
        access = payload.get("access_token")
        if not access:
            raise ValidationAppError("Dropbox OAuth did not return access_token")
        result = self.connect_dropbox_token(user_id=conn.connected_by_id, access_token=access)
        # Persist refresh if present
        conn = self.db.scalar(
            select(IntegrationConnection).where(IntegrationConnection.provider == "dropbox")
        )
        if conn and payload.get("refresh_token"):
            meta = dict(conn.token_metadata or {})
            tokens = dict(meta.get("tokens") or {})
            tokens["refresh_token_enc"] = encrypt_secret(payload["refresh_token"])
            meta["tokens"] = tokens
            conn.token_metadata = meta
            self.db.add(conn)
            self.db.commit()
        return result

    def connect_dropbox_token(self, *, user_id, access_token: str) -> dict:
        token = access_token.strip()
        if not token:
            raise ValidationAppError("Dropbox access token required")
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                DROPBOX_ACCOUNT_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code >= 400:
                raise ValidationAppError(
                    f"Dropbox token rejected ({resp.status_code}). Generate a new access token."
                )
            account = resp.json()
        email = account.get("email") or account.get("name", {}).get("display_name") or "Dropbox"
        conn = self.db.scalar(
            select(IntegrationConnection).where(IntegrationConnection.provider == "dropbox")
        )
        if conn is None:
            conn = IntegrationConnection(
                id=uuid4(),
                provider="dropbox",
                account_label=email,
                status="connected",
            )
            self.db.add(conn)
        conn.status = "connected"
        conn.account_label = email
        conn.connected_by_id = user_id
        conn.last_error = None
        conn.token_metadata = {
            "email": email,
            "account_id": account.get("account_id"),
            "tokens": {"access_token_enc": encrypt_secret(token)},
        }
        self.db.add(conn)
        self.audit.log(
            action="integration.connected",
            actor_user_id=user_id,
            record_type="integration_connection",
            record_id=conn.id,
            new_value={"provider": "dropbox", "email": email},
            source="dropbox_token",
        )
        self.db.commit()
        return {"status": "connected", "email": email, "provider": "dropbox"}

    def sync_dropbox(self, *, user_id=None, limit: int = 100) -> dict:
        from app.core.crypto import decrypt_secret

        token = self._dropbox_token()
        imported = 0
        updated = 0
        scanned = 0
        entries: list[dict] = []
        cursor = None
        has_more = True

        with httpx.Client(timeout=60.0) as client:
            while has_more and scanned < limit:
                if cursor:
                    resp = client.post(
                        DROPBOX_CONTINUE_URL,
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        json={"cursor": cursor},
                    )
                else:
                    resp = client.post(
                        DROPBOX_LIST_URL,
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        json={
                            "path": "",
                            "recursive": True,
                            "include_media_info": False,
                            "include_deleted": False,
                            "limit": min(100, limit - scanned),
                        },
                    )
                if resp.status_code >= 400:
                    self._mark_dropbox_failed(resp.text[:500])
                    raise ConflictError(f"Dropbox list failed: {resp.status_code}")
                data = resp.json()
                batch = data.get("entries") or []
                entries.extend(batch)
                scanned += len(batch)
                cursor = data.get("cursor")
                has_more = bool(data.get("has_more"))
                if scanned >= limit:
                    break

            for entry in entries:
                if entry.get(".tag") != "file":
                    continue
                result = self._upsert_document_from_dropbox(entry)
                if result == "created":
                    imported += 1
                elif result == "updated":
                    updated += 1

        conn = self.db.scalar(
            select(IntegrationConnection).where(IntegrationConnection.provider == "dropbox")
        )
        if conn:
            conn.last_successful_sync_at = datetime.now(timezone.utc)
            conn.last_error = None
            conn.status = "connected"
            meta = dict(conn.token_metadata or {})
            meta["last_sync"] = {"imported": imported, "updated": updated, "scanned": scanned}
            conn.token_metadata = meta
            self.db.add(conn)
        self.audit.log(
            action="synchronization.completed",
            actor_user_id=user_id,
            record_type="integration_connection",
            source="dropbox",
            new_value={"imported": imported, "updated": updated, "scanned": scanned},
        )
        self.db.commit()
        return {
            "status": "ok",
            "provider": "dropbox",
            "scanned": scanned,
            "imported": imported,
            "updated": updated,
        }

    def _dropbox_token(self) -> str:
        from app.core.crypto import decrypt_secret

        conn = self.db.scalar(
            select(IntegrationConnection).where(
                IntegrationConnection.provider == "dropbox",
                IntegrationConnection.status == "connected",
            )
        )
        if conn and conn.token_metadata:
            enc = ((conn.token_metadata or {}).get("tokens") or {}).get("access_token_enc")
            if enc:
                return decrypt_secret(enc)
        # fallback env token
        if self.settings.dropbox_access_token:
            return self.settings.dropbox_access_token
        raise ConflictError("Dropbox is not connected")

    def _mark_dropbox_failed(self, error: str) -> None:
        conn = self.db.scalar(
            select(IntegrationConnection).where(IntegrationConnection.provider == "dropbox")
        )
        if conn:
            conn.last_failed_sync_at = datetime.now(timezone.utc)
            conn.last_error = error
            self.db.add(conn)
            self.db.commit()

    def _upsert_document_from_dropbox(self, entry: dict) -> str:
        file_id = entry.get("id") or entry.get("path_lower")
        path = entry.get("path_display") or entry.get("path_lower") or ""
        name = entry.get("name") or path.split("/")[-1]
        existing = self.db.scalar(
            select(DocumentRecord).where(
                DocumentRecord.source_system == "dropbox",
                DocumentRecord.source_file_id == file_id,
            )
        )
        association = self._associate_text({"subject": name, "body": path, "sender": ""})
        modified = entry.get("server_modified") or entry.get("client_modified")
        modified_dt = None
        if modified:
            try:
                modified_dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
            except ValueError:
                modified_dt = None
        values = dict(
            file_name=name,
            mime_type=None,
            file_size=entry.get("size"),
            current_path=path,
            parent_folder="/".join(path.split("/")[:-1]) if path else None,
            direct_link=None,
            source_modified_at=modified_dt,
            last_synchronized_at=datetime.now(timezone.utc),
            file_hash=(entry.get("content_hash") or None),
            primary_matter_id=association.get("matter_id"),
            classification_confidence=association.get("confidence"),
            review_status="approved"
            if association.get("matter_id") and association.get("confidence") == "high"
            else "pending",
            extra_metadata={"dropbox": {"rev": entry.get("rev"), "path_lower": entry.get("path_lower")}},
        )
        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
            self.db.add(existing)
            return "updated"
        row = DocumentRecord(
            id=uuid4(),
            source_system="dropbox",
            source_file_id=file_id,
            first_discovered_at=datetime.now(timezone.utc),
            **values,
        )
        self.db.add(row)
        self.db.flush()
        if not row.primary_matter_id:
            self.db.add(
                ReviewQueueItem(
                    id=uuid4(),
                    item_type="unassigned_document",
                    priority="medium",
                    status="open",
                    title=f"Unassigned Dropbox file: {name[:120]}",
                    explanation=f"Path: {path}",
                    suggested_action="Associate to a matter",
                    related_record_type="document",
                    related_record_id=row.id,
                    kanban_column="inbox",
                )
            )
        return "created"

    # ----------------------------------------------------------------- Drive
    def sync_google_drive(self, *, user_id=None, max_results: int = 100, full: bool = False) -> dict:
        """Import Drive files with optional pagination (full history up to cap)."""
        access = self.google.get_valid_access_token("google_drive")
        imported = 0
        updated = 0
        extracted = 0
        scanned = 0
        page_token: Optional[str] = None
        hard_cap = min(max(max_results, 1), 2000 if full else 500)
        page_size = 100 if full else min(hard_cap, 100)

        with httpx.Client(timeout=90.0) as client:
            while scanned < hard_cap:
                params: dict[str, Any] = {
                    "pageSize": min(page_size, hard_cap - scanned),
                    "fields": (
                        "nextPageToken,files(id,name,mimeType,size,createdTime,"
                        "modifiedTime,webViewLink,parents,md5Checksum)"
                    ),
                    "q": "trashed=false",
                }
                if page_token:
                    params["pageToken"] = page_token
                resp = client.get(
                    DRIVE_FILES_URL,
                    params=params,
                    headers={"Authorization": f"Bearer {access}"},
                )
                resp.raise_for_status()
                payload = resp.json()
                files = payload.get("files") or []
                if not files:
                    break
                for f in files:
                    if scanned >= hard_cap:
                        break
                    result = self._upsert_document_from_drive(f)
                    scanned += 1
                    if result == "created":
                        imported += 1
                    elif result == "updated":
                        updated += 1
                    if self._maybe_extract_drive_text(client, access, f):
                        extracted += 1
                page_token = payload.get("nextPageToken")
                if not page_token or not full:
                    break
                self.db.commit()

        self.google.mark_sync_result(
            "google_drive",
            success=True,
            extra={
                "imported": imported,
                "updated": updated,
                "scanned": scanned,
                "extracted": extracted,
                "full": full,
            },
        )
        self.audit.log(
            action="synchronization.completed",
            actor_user_id=user_id,
            record_type="integration_connection",
            source="google_drive",
            new_value={"imported": imported, "updated": updated, "extracted": extracted, "full": full},
        )
        self.db.commit()
        return {
            "status": "ok",
            "provider": "google_drive",
            "scanned": scanned,
            "imported": imported,
            "updated": updated,
            "text_extracted": extracted,
            "full": full,
        }

    def _maybe_extract_drive_text(self, client: httpx.Client, access: str, f: dict) -> bool:
        """Pull plain text for Docs / text files into extracted_text (OCR-lite)."""
        from app.services.extraction import extract_drive_file_text

        file_id = f.get("id")
        if not file_id:
            return False
        doc = self.db.scalar(
            select(DocumentRecord).where(
                DocumentRecord.source_system == "google_drive",
                DocumentRecord.source_file_id == file_id,
            )
        )
        if not doc:
            return False
        text = extract_drive_file_text(client, access, f)
        if not text:
            return False
        doc.extracted_text = text[:50000]
        doc.ocr_status = "extracted"
        doc.extra_metadata = {
            **(doc.extra_metadata or {}),
            "extraction": {"status": "ok", "chars": len(text), "method": "drive_export"},
        }
        self.db.add(doc)
        return True

    def _upsert_document_from_drive(self, f: dict) -> str:
        file_id = f["id"]
        existing = self.db.scalar(
            select(DocumentRecord).where(
                DocumentRecord.source_system == "google_drive",
                DocumentRecord.source_file_id == file_id,
            )
        )
        name = f.get("name") or file_id
        association = self._associate_text({"subject": name, "body": "", "sender": ""})
        created = f.get("createdTime")
        modified = f.get("modifiedTime")

        def _iso(v):
            if not v:
                return None
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return None

        values = dict(
            file_name=name,
            mime_type=f.get("mimeType"),
            file_size=int(f["size"]) if f.get("size") else None,
            current_path=name,
            direct_link=f.get("webViewLink"),
            source_created_at=_iso(created),
            source_modified_at=_iso(modified),
            last_synchronized_at=datetime.now(timezone.utc),
            # Prefer Drive md5 when present; else stable fingerprint
            file_hash=f.get("md5Checksum")
            or f"drive:{file_id}:{f.get('size') or 0}:{f.get('modifiedTime') or ''}",
            primary_matter_id=association.get("matter_id"),
            classification_confidence=association.get("confidence"),
            review_status="pending",
            extra_metadata={"parents": f.get("parents")},
        )
        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
            self.db.add(existing)
            return "updated"
        row = DocumentRecord(
            id=uuid4(),
            source_system="google_drive",
            source_file_id=file_id,
            first_discovered_at=datetime.now(timezone.utc),
            **values,
        )
        self.db.add(row)
        return "created"

    # ----------------------------------------------------------- Association
    def _associate_text(self, signals_text: dict[str, str]) -> dict[str, Any]:
        matters = self.db.scalars(
            select(Matter).where(Matter.is_deleted.is_(False)).limit(200)
        ).all()
        candidates = [
            {
                "id": str(m.id),
                "claim_number": m.claim_number,
                "policy_number": m.policy_number,
                "case_number": m.case_number,
                "appraisal_number": m.appraisal_number,
                "name": m.name,
            }
            for m in matters
        ]
        blob = " ".join(signals_text.values()).lower()
        # enrich signals with extracted claim/policy-like tokens
        signals: dict[str, Any] = {}
        for key in ("claim_number", "policy_number", "case_number", "appraisal_number"):
            for c in candidates:
                val = (c.get(key) or "").strip()
                if val and val.lower() in blob:
                    signals[key] = val
        # also try subject exact matter name fragments
        provider = get_ai_provider()
        result = provider.associate_matter(signals, candidates)
        matter_id = None
        if result.suggested_primary_matter_id:
            try:
                from uuid import UUID

                matter_id = UUID(result.suggested_primary_matter_id)
            except ValueError:
                matter_id = None
        return {
            "matter_id": matter_id,
            "confidence": result.confidence_level.value if result.confidence_level else None,
            "score": result.confidence_score,
        }

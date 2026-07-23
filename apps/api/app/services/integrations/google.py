"""Google OAuth 2.0 + Gmail / Drive / Sheets integration service."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.exceptions import AuthorizationError, ConflictError, ValidationAppError
from app.core.logging import get_logger
from app.core.permissions import PermissionCode
from app.models.auth import User
from app.models.workflow import IntegrationConnection
from app.services.audit import AuditService

logger = get_logger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
DRIVE_ABOUT_URL = "https://www.googleapis.com/drive/v3/about"

GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


class GoogleIntegrationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.audit = AuditService(db)

    def ensure_configured(self) -> None:
        if not self.settings.google_configured:
            raise ValidationAppError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )

    def list_connections(self, *, user: User) -> list[IntegrationConnection]:
        if not user.has_permission(PermissionCode.INTEGRATIONS_READ):
            raise AuthorizationError("Cannot view integrations")
        return list(
            self.db.scalars(
                select(IntegrationConnection).order_by(IntegrationConnection.provider)
            ).all()
        )

    def start_oauth(self, *, user: User, provider: str = "gmail") -> dict[str, str]:
        """Return Google consent URL. provider: gmail | google_drive | google_sheets | google."""
        if not user.has_permission(PermissionCode.INTEGRATIONS_MANAGE):
            raise AuthorizationError("Cannot manage integrations")
        self.ensure_configured()

        state = secrets.token_urlsafe(24)
        # Persist pending connection shell for callback binding
        label_map = {
            "gmail": "Primary Gmail",
            "google_drive": "Shared Drive",
            "google_sheets": "T&E FOR CHAT FINAL",
            "google": "Google Workspace",
        }
        conn = self.db.scalar(
            select(IntegrationConnection).where(
                IntegrationConnection.provider == provider
            )
        )
        if conn is None:
            conn = IntegrationConnection(
                id=uuid4(),
                provider=provider,
                account_label=label_map.get(provider, provider),
                status="pending",
            )
            self.db.add(conn)
        else:
            conn.status = "pending"
        meta = dict(conn.token_metadata or {})
        meta["oauth_state"] = state
        meta["initiated_by"] = str(user.id)
        meta["initiated_at"] = datetime.now(timezone.utc).isoformat()
        conn.token_metadata = meta
        conn.connected_by_id = user.id
        self.db.add(conn)
        self.db.commit()

        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": f"{provider}:{state}",
        }
        return {"authorize_url": f"{GOOGLE_AUTH_URL}?{urlencode(params)}", "state": state}

    def handle_callback(self, *, code: str, state: str) -> dict[str, Any]:
        self.ensure_configured()
        if ":" not in state:
            raise ValidationAppError("Invalid OAuth state")
        provider, raw_state = state.split(":", 1)
        conn = self.db.scalar(
            select(IntegrationConnection).where(IntegrationConnection.provider == provider)
        )
        if conn is None:
            raise ValidationAppError("Unknown integration provider for callback")
        meta = dict(conn.token_metadata or {})
        if meta.get("oauth_state") != raw_state:
            raise ValidationAppError("OAuth state mismatch — restart connect flow")

        tokens = self._exchange_code(code)
        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        expires_in = int(tokens.get("expires_in", 3600))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        profile = self._fetch_userinfo(access_token)
        email = profile.get("email") or "unknown"

        # If Google did not return refresh_token (repeat consent), keep previous
        previous = meta.get("tokens") or {}
        if not refresh_token and previous.get("refresh_token_enc"):
            refresh_token_enc = previous["refresh_token_enc"]
        elif refresh_token:
            refresh_token_enc = encrypt_secret(refresh_token)
        else:
            refresh_token_enc = None

        conn.status = "connected"
        conn.account_label = email
        conn.scopes = " ".join(GOOGLE_SCOPES)
        conn.last_successful_sync_at = None
        conn.last_error = None
        conn.token_metadata = {
            "email": email,
            "google_user_id": profile.get("id"),
            "tokens": {
                "access_token_enc": encrypt_secret(access_token),
                "refresh_token_enc": refresh_token_enc,
                "expires_at": expires_at.isoformat(),
                "token_type": tokens.get("token_type", "Bearer"),
                "scope": tokens.get("scope"),
            },
            "api_key_hint": "GOOGLE_API_KEY configured" if self.settings.google_api_key else None,
        }
        self.db.add(conn)
        actor = UUID(meta["initiated_by"]) if meta.get("initiated_by") else None
        self.audit.log(
            action="integration.connected",
            actor_user_id=actor,
            record_type="integration_connection",
            record_id=conn.id,
            new_value={"provider": provider, "email": email},
            source="google_oauth",
        )
        self.db.commit()
        return {
            "provider": provider,
            "email": email,
            "status": "connected",
            "connection_id": str(conn.id),
        }

    def disconnect(self, *, user: User, provider: str) -> IntegrationConnection:
        if not user.has_permission(PermissionCode.INTEGRATIONS_MANAGE):
            raise AuthorizationError("Cannot manage integrations")
        conn = self.db.scalar(
            select(IntegrationConnection).where(IntegrationConnection.provider == provider)
        )
        if not conn:
            raise ValidationAppError("Integration not found")
        conn.status = "disconnected"
        conn.token_metadata = None
        conn.scopes = None
        conn.last_error = None
        self.db.add(conn)
        self.audit.log(
            action="integration.disconnected",
            actor_user_id=user.id,
            record_type="integration_connection",
            record_id=conn.id,
            new_value={"provider": provider},
        )
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def get_valid_access_token(self, provider: str = "gmail") -> str:
        # Try exact provider, then shared Google connections that carry the same scopes
        candidates = [provider]
        if provider != "gmail":
            candidates.extend(["gmail", "google", "google_drive", "google_sheets"])
        else:
            candidates.extend(["google"])

        conn = None
        for cand in candidates:
            row = self.db.scalar(
                select(IntegrationConnection).where(
                    IntegrationConnection.provider == cand,
                    IntegrationConnection.status == "connected",
                )
            )
            if not row or not row.token_metadata:
                continue
            tokens_probe = (row.token_metadata or {}).get("tokens") or {}
            if tokens_probe.get("access_token_enc") or tokens_probe.get("refresh_token_enc"):
                conn = row
                break
        if not conn or not conn.token_metadata:
            raise ConflictError("Google account is not connected")

        tokens = (conn.token_metadata or {}).get("tokens") or {}
        expires_at_raw = tokens.get("expires_at")
        access_enc = tokens.get("access_token_enc")
        refresh_enc = tokens.get("refresh_token_enc")
        if not access_enc:
            raise ConflictError("Stored Google access token missing — reconnect")

        expires_at = (
            datetime.fromisoformat(expires_at_raw)
            if expires_at_raw
            else datetime.now(timezone.utc)
        )
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
            return decrypt_secret(access_enc)

        if not refresh_enc:
            raise ConflictError("Google refresh token missing — reconnect with consent")

        refreshed = self._refresh_access_token(decrypt_secret(refresh_enc))
        new_access = refreshed["access_token"]
        new_expires = datetime.now(timezone.utc) + timedelta(
            seconds=int(refreshed.get("expires_in", 3600))
        )
        tokens["access_token_enc"] = encrypt_secret(new_access)
        tokens["expires_at"] = new_expires.isoformat()
        meta = dict(conn.token_metadata)
        meta["tokens"] = tokens
        conn.token_metadata = meta
        self.db.add(conn)
        self.db.commit()
        return new_access

    def test_connection(self, *, user: User, provider: str = "gmail") -> dict[str, Any]:
        if not user.has_permission(PermissionCode.INTEGRATIONS_READ):
            raise AuthorizationError("Cannot view integrations")
        access = self.get_valid_access_token(provider)
        with httpx.Client(timeout=30.0) as client:
            if provider in {"gmail", "google"}:
                resp = client.get(
                    GMAIL_PROFILE_URL,
                    headers={"Authorization": f"Bearer {access}"},
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "ok": True,
                    "provider": "gmail",
                    "email_address": data.get("emailAddress"),
                    "messages_total": data.get("messagesTotal"),
                    "threads_total": data.get("threadsTotal"),
                    "api_key_in_use": bool(self.settings.google_api_key),
                }
            if provider == "google_drive":
                resp = client.get(
                    DRIVE_ABOUT_URL,
                    params={"fields": "user,storageQuota"},
                    headers={"Authorization": f"Bearer {access}"},
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "ok": True,
                    "provider": "google_drive",
                    "user": data.get("user"),
                    "storage_quota": data.get("storageQuota"),
                }
        raise ValidationAppError(f"Unsupported provider test: {provider}")

    def list_gmail_message_ids(self, *, max_results: int = 25) -> list[str]:
        access = self.get_valid_access_token("gmail")
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                GMAIL_MESSAGES_URL,
                params={"maxResults": max_results},
                headers={"Authorization": f"Bearer {access}"},
            )
            resp.raise_for_status()
            return [m["id"] for m in resp.json().get("messages", [])]

    def mark_sync_result(
        self,
        provider: str,
        *,
        success: bool,
        error: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> None:
        conn = self.db.scalar(
            select(IntegrationConnection).where(IntegrationConnection.provider == provider)
        )
        if not conn:
            return
        if success:
            conn.last_successful_sync_at = datetime.now(timezone.utc)
            conn.last_error = None
            conn.status = "connected"
        else:
            conn.last_failed_sync_at = datetime.now(timezone.utc)
            conn.last_error = (error or "sync failed")[:2000]
        if extra:
            meta = dict(conn.token_metadata or {})
            meta["last_sync"] = extra
            conn.token_metadata = meta
        self.db.add(conn)
        self.db.commit()

    def _exchange_code(self, code: str) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code >= 400:
                logger.warning("Google token exchange failed: %s", resp.text[:300])
                raise ValidationAppError(
                    "Google token exchange failed. Check Client ID/Secret and redirect URI."
                )
            return resp.json()

    def _refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            if resp.status_code >= 400:
                raise ConflictError("Google token refresh failed — reconnect account")
            return resp.json()

    def _fetch_userinfo(self, access_token: str) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

"""Append-only audit ledger service."""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.auth import AuditEvent


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        *,
        action: str,
        actor_user_id: Optional[UUID] = None,
        actor_type: str = "user",
        record_type: Optional[str] = None,
        record_id: Optional[UUID] = None,
        matter_id: Optional[UUID] = None,
        previous_value: Optional[dict[str, Any]] = None,
        new_value: Optional[dict[str, Any]] = None,
        reason: Optional[str] = None,
        source: Optional[str] = "api",
        confidence: Optional[str] = None,
        approval_status: Optional[str] = None,
        request_metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEvent:
        # Strip sensitive keys from metadata
        safe_meta = self._sanitize_metadata(request_metadata)
        event = AuditEvent(
            action=action,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            record_type=record_type,
            record_id=record_id,
            matter_id=matter_id,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason,
            source=source,
            confidence=confidence,
            approval_status=approval_status,
            request_metadata=safe_meta,
        )
        self.db.add(event)
        self.db.flush()
        return event

    @staticmethod
    def _sanitize_metadata(
        metadata: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        if not metadata:
            return None
        blocked = {
            "password",
            "token",
            "access_token",
            "refresh_token",
            "authorization",
            "secret",
        }
        return {
            k: ("***REDACTED***" if k.lower() in blocked else v)
            for k, v in metadata.items()
        }

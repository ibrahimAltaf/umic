"""Authentication service: login, logout, refresh, registration."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.auth import RefreshToken, User, UserRole, UserSession
from app.repositories.user import RefreshTokenRepository, RoleRepository, UserRepository
from app.schemas.auth import TokenResponse, UserCreate, UserOut, UserUpdate
from app.services.audit import AuditService

logger = get_logger(__name__)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        roles=[{"id": r.id, "code": r.code, "name": r.name} for r in user.roles],
        permissions=sorted(user.permission_codes),
    )


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.audit = AuditService(db)
        self.settings = get_settings()

    def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        user = self.users.get_by_email(email.lower().strip())
        if user is None:
            raise AuthenticationError("Invalid email or password")

        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise AuthenticationError("Account is temporarily locked")

        if not user.is_active or user.is_deleted:
            raise AuthenticationError("Account is disabled")

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 10:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
            self.users.save(user)
            self.db.commit()
            raise AuthenticationError("Invalid email or password")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        self.users.save(user)

        tokens = self._issue_tokens(user, ip_address=ip_address, user_agent=user_agent)
        self.audit.log(
            action="user.login",
            actor_user_id=user.id,
            record_type="user",
            record_id=user.id,
            request_metadata={"ip_address": ip_address, "user_agent": user_agent},
        )
        self.db.commit()
        return tokens

    def refresh(
        self,
        *,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        payload = decode_token(refresh_token, expected_type="refresh")
        jti = payload.get("jti")
        if not jti:
            raise AuthenticationError("Invalid refresh token")

        stored = self.refresh_tokens.get_by_jti(jti)
        if stored is None or stored.is_revoked or stored.is_expired:
            raise AuthenticationError("Refresh token revoked or expired")

        if stored.token_hash != _hash_token(refresh_token):
            raise AuthenticationError("Invalid refresh token")

        user = self.users.get_by_id(stored.user_id)
        if user is None or not user.is_active or user.is_deleted:
            raise AuthenticationError("Account is disabled")

        # Rotate refresh token
        self.refresh_tokens.revoke(stored)
        tokens = self._issue_tokens(user, ip_address=ip_address, user_agent=user_agent)
        self.audit.log(
            action="user.token_refresh",
            actor_user_id=user.id,
            record_type="user",
            record_id=user.id,
        )
        self.db.commit()
        return tokens

    def logout(self, *, refresh_token: str, user_id: Optional[UUID] = None) -> None:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except AuthenticationError:
            return

        jti = payload.get("jti")
        if not jti:
            return
        stored = self.refresh_tokens.get_by_jti(jti)
        if stored and not stored.is_revoked:
            self.refresh_tokens.revoke(stored)
            self.audit.log(
                action="user.logout",
                actor_user_id=user_id or stored.user_id,
                record_type="user",
                record_id=stored.user_id,
            )
            self.db.commit()

    def logout_all(self, user: User) -> int:
        count = self.refresh_tokens.revoke_all_for_user(user.id)
        self.audit.log(
            action="user.logout_all",
            actor_user_id=user.id,
            record_type="user",
            record_id=user.id,
            new_value={"revoked_tokens": count},
        )
        self.db.commit()
        return count

    def register_user(
        self,
        data: UserCreate,
        *,
        actor: User,
    ) -> UserOut:
        if not actor.has_permission("users:manage") and not actor.has_permission(
            "users:write"
        ):
            raise AuthorizationError("You cannot create users")

        existing = self.users.get_by_email(data.email.lower())
        if existing:
            raise ConflictError("A user with this email already exists")

        role_codes = data.role_codes or ["standard_user"]
        roles = list(self.roles.get_by_codes(role_codes))
        if len(roles) != len(set(role_codes)):
            raise ValidationAppError("One or more role codes are invalid")

        user = User(
            email=data.email.lower().strip(),
            password_hash=hash_password(data.password),
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            is_active=data.is_active,
            is_email_verified=False,
            password_changed_at=datetime.now(timezone.utc),
        )
        self.users.create(user)
        for role in roles:
            self.db.add(
                UserRole(user_id=user.id, role_id=role.id, assigned_by=actor.id)
            )
        self.db.flush()

        # Reload with relationships
        created = self.users.get_by_id(user.id)
        assert created is not None
        self.audit.log(
            action="user.created",
            actor_user_id=actor.id,
            record_type="user",
            record_id=created.id,
            new_value={
                "email": created.email,
                "roles": role_codes,
                "is_active": created.is_active,
            },
        )
        self.db.commit()
        return _user_to_out(created)

    def update_user(
        self,
        user_id: UUID,
        data: UserUpdate,
        *,
        actor: User,
    ) -> UserOut:
        if not actor.has_permission("users:manage") and not actor.has_permission(
            "users:write"
        ):
            raise AuthorizationError("You cannot update users")

        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        previous = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "roles": [r.code for r in user.roles],
        }

        if data.first_name is not None:
            user.first_name = data.first_name.strip()
        if data.last_name is not None:
            user.last_name = data.last_name.strip()
        if data.is_active is not None:
            user.is_active = data.is_active
            if not data.is_active:
                self.refresh_tokens.revoke_all_for_user(user.id)

        if data.role_codes is not None:
            if not actor.has_permission("roles:manage") and not actor.has_permission(
                "users:manage"
            ):
                raise AuthorizationError("You cannot change user roles")
            roles = list(self.roles.get_by_codes(data.role_codes))
            if len(roles) != len(set(data.role_codes)):
                raise ValidationAppError("One or more role codes are invalid")
            # Replace roles
            for ur in list(user.user_roles):
                self.db.delete(ur)
            self.db.flush()
            for role in roles:
                self.db.add(
                    UserRole(user_id=user.id, role_id=role.id, assigned_by=actor.id)
                )

        self.users.save(user)
        self.db.flush()
        updated = self.users.get_by_id(user.id)
        assert updated is not None
        self.audit.log(
            action="user.updated",
            actor_user_id=actor.id,
            record_type="user",
            record_id=updated.id,
            previous_value=previous,
            new_value={
                "first_name": updated.first_name,
                "last_name": updated.last_name,
                "is_active": updated.is_active,
                "roles": [r.code for r in updated.roles],
            },
        )
        self.db.commit()
        return _user_to_out(updated)

    def request_password_reset(self, email: str) -> dict:
        """Create reset token if user exists. Always safe for enumeration."""
        from uuid import uuid4

        from app.models.auth import PasswordResetToken

        user = self.users.get_by_email(email.lower().strip())
        raw_token = None
        if user and user.is_active and not user.is_deleted:
            raw_token = secrets.token_urlsafe(32)
            self.db.add(
                PasswordResetToken(
                    id=uuid4(),
                    user_id=user.id,
                    token_hash=_hash_token(raw_token),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
                )
            )
            self.audit.log(
                action="auth.password_reset_requested",
                actor_user_id=user.id,
                record_type="user",
                record_id=user.id,
            )
            self.db.commit()
            # Dev/local: log token so ops can reset without SMTP
            if not self.settings.is_production:
                logger.info(
                    "password_reset_token_issued",
                    extra={"email": user.email, "token": raw_token},
                )
        return {
            "message": "If an account exists for that email, reset instructions will be sent.",
            "dev_token": raw_token if (raw_token and not self.settings.is_production) else None,
        }

    def confirm_password_reset(self, *, token: str, new_password: str) -> None:
        from app.models.auth import PasswordResetToken
        from sqlalchemy import select

        token_hash = _hash_token(token)
        row = self.db.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        if not row or row.used_at is not None:
            raise ValidationAppError("Invalid or expired reset token")
        if row.expires_at < datetime.now(timezone.utc):
            raise ValidationAppError("Invalid or expired reset token")
        user = self.users.get_by_id(row.user_id)
        if not user or not user.is_active or user.is_deleted:
            raise ValidationAppError("Invalid or expired reset token")
        user.password_hash = hash_password(new_password)
        row.used_at = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.add(row)
        self.refresh_tokens.revoke_all_for_user(user.id)
        self.audit.log(
            action="auth.password_reset_completed",
            actor_user_id=user.id,
            record_type="user",
            record_id=user.id,
        )
        self.db.commit()

    def get_current_user_out(self, user: User) -> UserOut:
        return _user_to_out(user)

    def list_users(
        self, *, actor: User, page: int = 1, page_size: int = 20, search: Optional[str] = None
    ) -> dict:
        if not actor.has_permission("users:read"):
            raise AuthorizationError("You cannot list users")
        items, total = self.users.list_users(
            offset=(page - 1) * page_size, limit=page_size, search=search
        )
        return {
            "items": [_user_to_out(u) for u in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size else 0,
        }

    def _issue_tokens(
        self,
        user: User,
        *,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        jti = secrets.token_urlsafe(32)
        access = create_access_token(
            subject=user.id,
            extra_claims={
                "email": user.email,
                "roles": [r.code for r in user.roles],
            },
        )
        refresh = create_refresh_token(subject=user.id, jti=jti)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self.settings.refresh_token_expire_days
        )
        stored = RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=_hash_token(refresh),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(stored)
        self.db.flush()
        session = UserSession(
            user_id=user.id,
            refresh_token_id=stored.id,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
        )
        self.db.add(session)
        self.db.flush()
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.settings.access_token_expire_minutes * 60,
        )

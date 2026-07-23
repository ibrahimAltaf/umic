"""User and role data access."""

from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.auth import Permission, Role, User, UserRole


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.id == user_id, User.is_deleted.is_(False))
            .options(
                selectinload(User.user_roles).selectinload(UserRole.role).selectinload(Role.permissions)
            )
        )
        return self.db.scalar(stmt)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.email == email.lower(), User.is_deleted.is_(False))
            .options(
                selectinload(User.user_roles).selectinload(UserRole.role).selectinload(Role.permissions)
            )
        )
        return self.db.scalar(stmt)

    def list_users(
        self, *, offset: int, limit: int, search: Optional[str] = None
    ) -> tuple[Sequence[User], int]:
        base = select(User).where(User.is_deleted.is_(False))
        count_stmt = select(func.count()).select_from(User).where(User.is_deleted.is_(False))
        if search:
            pattern = f"%{search}%"
            filt = (
                User.email.ilike(pattern)
                | User.first_name.ilike(pattern)
                | User.last_name.ilike(pattern)
            )
            base = base.where(filt)
            count_stmt = count_stmt.where(filt)

        total = self.db.scalar(count_stmt) or 0
        stmt = (
            base.options(
                selectinload(User.user_roles).selectinload(UserRole.role)
            )
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.scalars(stmt).all(), total

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_code(self, code: str) -> Optional[Role]:
        stmt = (
            select(Role)
            .where(Role.code == code)
            .options(selectinload(Role.permissions))
        )
        return self.db.scalar(stmt)

    def get_by_codes(self, codes: list[str]) -> Sequence[Role]:
        if not codes:
            return []
        stmt = (
            select(Role)
            .where(Role.code.in_(codes), Role.is_active.is_(True))
            .options(selectinload(Role.permissions))
        )
        return self.db.scalars(stmt).all()

    def list_all(self) -> Sequence[Role]:
        stmt = (
            select(Role)
            .where(Role.is_active.is_(True))
            .options(selectinload(Role.permissions))
            .order_by(Role.name)
        )
        return self.db.scalars(stmt).all()

    def list_permissions(self) -> Sequence[Permission]:
        stmt = select(Permission).order_by(Permission.resource, Permission.action)
        return self.db.scalars(stmt).all()


class RefreshTokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_jti(self, jti: str):
        from app.models.auth import RefreshToken

        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        return self.db.scalar(stmt)

    def revoke(self, token) -> None:
        token.revoked_at = datetime.now(timezone.utc)
        self.db.add(token)
        self.db.flush()

    def revoke_all_for_user(self, user_id: UUID) -> int:
        from app.models.auth import RefreshToken

        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        tokens = self.db.scalars(stmt).all()
        now = datetime.now(timezone.utc)
        for t in tokens:
            t.revoked_at = now
            self.db.add(t)
        self.db.flush()
        return len(tokens)

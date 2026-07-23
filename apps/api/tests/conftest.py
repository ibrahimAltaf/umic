"""Pytest fixtures for API tests."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure settings load before app import
os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key-must-be-at-least-32-characters-long-xx",
)
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-jwt-secret-key-must-be-at-least-32-characters-xx",
)
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "true")

from app.core.permissions import (  # noqa: E402
    ROLE_DESCRIPTIONS,
    ROLE_PERMISSION_MAP,
    PermissionCode,
    SystemRole,
)
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.auth import Permission, Role, RolePermission, User, UserRole  # noqa: E402


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite does not support some PG types; JSONB maps fine via SQLAlchemy for tests
    # if we use generic JSON — but our models use JSONB dialect. Override with JSON.
    from sqlalchemy import JSON
    from sqlalchemy.dialects.postgresql import JSONB, UUID

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Compile UUID/JSONB for SQLite
    from sqlalchemy.ext.compiler import compiles

    @compiles(UUID, "sqlite")
    def compile_uuid_sqlite(_type, _compiler, **_kw):
        return "CHAR(36)"

    @compiles(JSONB, "sqlite")
    def compile_jsonb_sqlite(_type, _compiler, **_kw):
        return "JSON"

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db(db_engine) -> Generator[Session, None, None]:
    TestingSessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_rbac(session: Session) -> dict[str, Role]:
    perm_by_code: dict[str, Permission] = {}
    for code in PermissionCode:
        resource, action = code.value.split(":", 1)
        perm = Permission(
            id=uuid4(),
            code=code.value,
            name=code.value,
            resource=resource,
            action=action,
        )
        session.add(perm)
        perm_by_code[code.value] = perm
    session.flush()

    roles: dict[str, Role] = {}
    for role_enum in SystemRole:
        role = Role(
            id=uuid4(),
            code=role_enum.value,
            name=role_enum.value,
            description=ROLE_DESCRIPTIONS[role_enum],
            is_system=True,
            is_active=True,
        )
        session.add(role)
        session.flush()
        for pcode in ROLE_PERMISSION_MAP[role_enum]:
            session.add(
                RolePermission(
                    id=uuid4(),
                    role_id=role.id,
                    permission_id=perm_by_code[pcode.value].id,
                )
            )
        roles[role_enum.value] = role
    session.flush()
    return roles


def _create_user(
    session: Session,
    *,
    email: str,
    password: str,
    role: Role,
    is_active: bool = True,
) -> User:
    user = User(
        id=uuid4(),
        email=email.lower(),
        password_hash=hash_password(password),
        first_name="Test",
        last_name="User",
        is_active=is_active,
        is_email_verified=True,
        password_changed_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.flush()
    session.add(UserRole(id=uuid4(), user_id=user.id, role_id=role.id))
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture()
def seeded(db: Session) -> dict:
    roles = _seed_rbac(db)
    admin = _create_user(
        db,
        email="admin@example.com",
        password="AdminPass123!",
        role=roles[SystemRole.SYSTEM_OWNER.value],
    )
    readonly = _create_user(
        db,
        email="readonly@example.com",
        password="ReadPass123!",
        role=roles[SystemRole.READ_ONLY_USER.value],
    )
    disabled = _create_user(
        db,
        email="disabled@example.com",
        password="DisabledPass123!",
        role=roles[SystemRole.STANDARD_USER.value],
        is_active=False,
    )
    return {
        "roles": roles,
        "admin": admin,
        "readonly": readonly,
        "disabled": disabled,
    }


@pytest.fixture()
def client(db: Session, seeded: dict) -> Generator[TestClient, None, None]:
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

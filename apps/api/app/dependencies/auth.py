"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated, Callable, Optional
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.auth import User
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authentication required")

    payload = decode_token(credentials.credentials, expected_type="access")
    sub = payload.get("sub")
    if not sub:
        raise AuthenticationError("Invalid token subject")

    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise AuthenticationError("Invalid token subject") from exc

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active or user.is_deleted:
        raise AuthenticationError("Account is disabled or not found")

    request.state.user_id = str(user.id)
    return user


def get_optional_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
) -> Optional[User]:
    if credentials is None:
        return None
    try:
        return get_current_user(request, db, credentials)
    except AuthenticationError:
        return None


def require_permissions(*permission_codes: str) -> Callable:
    """Dependency factory: require ALL listed permissions."""

    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        missing = [p for p in permission_codes if not user.has_permission(p)]
        if missing:
            raise AuthorizationError(
                "Insufficient permissions",
                details={"missing": missing},
            )
        return user

    return dependency


def require_any_permission(*permission_codes: str) -> Callable:
    """Dependency factory: require ANY of the listed permissions."""

    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not user.has_any_permission(*permission_codes):
            raise AuthorizationError(
                "Insufficient permissions",
                details={"required_any": list(permission_codes)},
            )
        return user

    return dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]

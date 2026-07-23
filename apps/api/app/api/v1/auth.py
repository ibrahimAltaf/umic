"""Authentication API routes."""

from fastapi import APIRouter, Request, status

from app.core.rate_limit import limiter
from app.dependencies.auth import CurrentUser, DbSession, get_client_ip
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
    UserMeOut,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: DbSession,
) -> TokenResponse:
    service = AuthService(db)
    return service.login(
        email=body.email,
        password=body.password,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh(
    request: Request,
    body: RefreshRequest,
    db: DbSession,
) -> TokenResponse:
    service = AuthService(db)
    return service.refresh(
        refresh_token=body.refresh_token,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: LogoutRequest,
    db: DbSession,
    user: CurrentUser,
) -> MessageResponse:
    AuthService(db).logout(refresh_token=body.refresh_token, user_id=user.id)
    return MessageResponse(message="Logged out successfully")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(db: DbSession, user: CurrentUser) -> MessageResponse:
    count = AuthService(db).logout_all(user)
    return MessageResponse(message=f"Revoked {count} session(s)")


@router.get("/me", response_model=UserMeOut)
async def me(db: DbSession, user: CurrentUser) -> UserMeOut:
    return AuthService(db).get_current_user_out(user)  # type: ignore[return-value]


@router.post(
    "/password-reset/request",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    db: DbSession,
) -> dict:
    """Request reset. In non-production, may include dev_token for local testing."""
    _ = request
    return AuthService(db).request_password_reset(body.email)


@router.post("/password-reset/confirm", response_model=MessageResponse)
@limiter.limit("5/minute")
async def confirm_password_reset(
    request: Request,
    body: PasswordResetConfirm,
    db: DbSession,
) -> MessageResponse:
    _ = request
    AuthService(db).confirm_password_reset(token=body.token, new_password=body.new_password)
    return MessageResponse(message="Password updated successfully")

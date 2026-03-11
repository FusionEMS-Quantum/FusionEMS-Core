from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.core.security import create_access_token
from core_app.repositories.user_repository import UserRepository
from core_app.schemas.auth import (
    CurrentUser,
    InviteAcceptRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserInviteCreate,
    UserInviteResponse,
    UserRegisterRequest,
    UserRegisterResponse,
)
from core_app.services.auth_service import (
    AccountLockedError,
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_cookie_max_age_seconds,
        domain=settings.session_cookie_domain or None,
        path="/",
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(db_session_dependency),
) -> TokenResponse:
    service = AuthService(UserRepository(db), db)
    try:
        result = service.login(payload, ip_address=_get_client_ip(request))
        _set_auth_cookie(response, result.access_token)
        db.commit()
        return result
    except AccountLockedError as exc:
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidCredentialsError as exc:
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserRegisterRequest,
    db: Session = Depends(db_session_dependency),
) -> UserRegisterResponse:
    """
    Self-registration endpoint. Protected by tenant provisioning in production
    via PHILockMiddleware — additional access controls should be applied at the
    infrastructure layer (e.g., invite-only mode via feature flag).
    """
    service = AuthService(UserRepository(db), db)
    try:
        result = service.register_user(payload)
        db.commit()
        return result
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/invite", response_model=UserInviteResponse, status_code=status.HTTP_201_CREATED)
def invite_user(
    payload: UserInviteCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> UserInviteResponse:
    """Send an invitation to a new user. Agency admins and founders only."""
    if current.role not in ("founder", "agency_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges to invite users")

    service = AuthService(UserRepository(db), db)
    try:
        invite_response, _raw_token = service.create_invite(
            tenant_id=current.tenant_id,
            invited_by_user_id=current.user_id,
            payload=payload,
        )
        db.commit()
        # NOTE: In production, _raw_token must be dispatched via a secure email
        # channel here (e.g., SES, SendGrid). Out-of-scope for current integration.
        return invite_response
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/invite/accept", response_model=TokenResponse)
def accept_invite(
    payload: InviteAcceptRequest,
    request: Request,
    response: Response,
    db: Session = Depends(db_session_dependency),
) -> TokenResponse:
    """Accept an invitation and set a password to activate the account."""
    service = AuthService(UserRepository(db), db)
    try:
        result = service.accept_invite(payload, ip_address=_get_client_ip(request))
        _set_auth_cookie(response, result.access_token)
        db.commit()
        return result
    except TokenExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except (TokenInvalidError, EmailAlreadyRegisteredError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/password-reset", status_code=status.HTTP_204_NO_CONTENT)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> None:
    """
    Initiate a password reset. Always returns 204 regardless of whether the
    email exists — prevents account enumeration.
    """
    service = AuthService(UserRepository(db), db)
    service.request_password_reset(payload, ip_address=_get_client_ip(request))
    db.commit()


@router.post("/password-reset/confirm", response_model=TokenResponse)
def confirm_password_reset(
    payload: PasswordResetConfirm,
    request: Request,
    response: Response,
    db: Session = Depends(db_session_dependency),
) -> TokenResponse:
    """Complete password reset using the token from the reset email."""
    service = AuthService(UserRepository(db), db)
    try:
        result = service.confirm_password_reset(payload, ip_address=_get_client_ip(request))
        _set_auth_cookie(response, result.access_token)
        db.commit()
        return result
    except TokenExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except TokenInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, current: CurrentUser = Depends(get_current_user)) -> TokenResponse:
    token = create_access_token(str(current.user_id), str(current.tenant_id), current.role or "")
    _set_auth_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout(response: Response, current: CurrentUser = Depends(get_current_user)) -> dict:
    # Session revocation is handled client-side (drop token);
    # the dependency validates the token, ensuring only active sessions can call this.
    _ = current
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        domain=settings.session_cookie_domain or None,
        path="/",
    )
    return {"status": "ok"}


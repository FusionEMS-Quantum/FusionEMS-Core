from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import logging
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.core.security import create_access_token
from core_app.integrations.graph_service import GraphNotConfigured, GraphClient
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _get_graph_service() -> GraphClient | None:
    """Build GraphClient from settings; returns None and logs a warning if not configured."""
    s = get_settings()
    try:
        return GraphClient(
            tenant_id=s.graph_tenant_id,
            client_id=s.graph_client_id,
            client_secret=s.graph_client_secret,
            founder_email=s.graph_founder_email,
        )
    except GraphNotConfigured as exc:
        logger.warning(
            "Graph email not configured — transactional email will not be sent",
            extra={"error": str(exc)},
        )
        return None


def _dispatch_email_best_effort(to: str, subject: str, body_html: str) -> None:
    """Send an email via Microsoft Graph. Logs and silences all failures."""
    graph = _get_graph_service()
    if graph is None:
        return
    try:
        graph.send_mail(to=[to], subject=subject, body_html=body_html)
        logger.info("Transactional email sent", extra={"to": to, "subject": subject})
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to dispatch transactional email — manual intervention required",
            extra={"to": to, "subject": subject, "error": str(exc)},
        )


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
        settings = get_settings()
        accept_url = f"{settings.resolved_frontend_base_url}/auth/accept-invite?token={_raw_token}"
        _dispatch_email_best_effort(
            to=str(payload.email),
            subject="You've been invited to FusionEMS Quantum",
            body_html=(
                f"<p>You have been invited to join FusionEMS Quantum as <strong>{payload.role}</strong>.</p>"
                f"<p><a href='{accept_url}'>Accept Invitation</a></p>"
                f"<p>This link expires in 72 hours.</p>"
            ),
        )
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
    result = service.request_password_reset(payload, ip_address=_get_client_ip(request))
    db.commit()
    if result is not None:
        raw_token, user_email = result
        settings = get_settings()
        reset_url = f"{settings.resolved_frontend_base_url}/auth/reset-password?token={raw_token}"
        _dispatch_email_best_effort(
            to=user_email,
            subject="FusionEMS Quantum — Password Reset",
            body_html=(
                f"<p>A password reset was requested for your FusionEMS Quantum account.</p>"
                f"<p><a href='{reset_url}'>Reset Password</a></p>"
                f"<p>This link expires in 2 hours. If you did not request this, ignore this email.</p>"
            ),
        )


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


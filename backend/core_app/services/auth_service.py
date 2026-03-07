import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from core_app.core.security import create_access_token, hash_password, verify_password
from core_app.models.governance import (
    AuthenticationEvent,
    AuthenticationEventType,
    PasswordResetToken,
    UserInvite,
    UserSession,
)
from core_app.models.user import User
from core_app.repositories.user_repository import UserRepository
from core_app.schemas.auth import (
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

# Maximum failed login attempts before automatic lockout
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_WINDOW_MINUTES = 15
_INVITE_TTL_HOURS = 48
_RESET_TOKEN_TTL_HOURS = 2


class InvalidCredentialsError(ValueError):
    pass


class AccountLockedError(ValueError):
    pass


class TokenExpiredError(ValueError):
    pass


class TokenInvalidError(ValueError):
    pass


class EmailAlreadyRegisteredError(ValueError):
    pass


def _token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class AuthService:
    def __init__(self, user_repo: UserRepository, db: Session | None = None) -> None:
        self.user_repo = user_repo
        self.db: Session = db or user_repo.db

    # ─── Login ────────────────────────────────────────────────────────────────

    def login(self, payload: LoginRequest, ip_address: str | None = None) -> TokenResponse:
        user = self.user_repo.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            if user is not None:
                self._record_auth_event(user.tenant_id, user.id, AuthenticationEventType.LOGIN_FAILED, ip_address=ip_address)
                self._check_and_apply_lockout(user)
            raise InvalidCredentialsError("Invalid email or password")

        if user.role == "locked":
            raise AccountLockedError("Account is locked. Contact your administrator.")

        self._record_auth_event(user.tenant_id, user.id, AuthenticationEventType.LOGIN, ip_address=ip_address)
        token = create_access_token(str(user.id), str(user.tenant_id), user.role)
        return TokenResponse(access_token=token)

    # ─── Register ─────────────────────────────────────────────────────────────

    def register_user(self, payload: UserRegisterRequest) -> UserRegisterResponse:
        existing = self.user_repo.get_by_email_and_tenant(payload.email, payload.tenant_id)
        if existing is not None:
            raise EmailAlreadyRegisteredError("Email already registered for this tenant")

        user = self.user_repo.create(
            tenant_id=payload.tenant_id,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=payload.role,
        )
        self._record_auth_event(user.tenant_id, user.id, AuthenticationEventType.INVITE_ACCEPTED)
        return UserRegisterResponse.model_validate(user)

    # ─── Invite ───────────────────────────────────────────────────────────────

    def create_invite(
        self,
        tenant_id: uuid.UUID,
        invited_by_user_id: uuid.UUID,
        payload: UserInviteCreate,
    ) -> tuple[UserInviteResponse, str]:
        """Returns (invite_response, raw_token). Raw token must be sent via email."""
        raw_token = secrets.token_urlsafe(48)
        invite = UserInvite(
            tenant_id=tenant_id,
            email=payload.email,
            role=payload.role,
            invited_by_user_id=invited_by_user_id,
            token_hash=_token_hash(raw_token),
            expires_at=datetime.now(UTC) + timedelta(hours=_INVITE_TTL_HOURS),
        )
        self.db.add(invite)
        self.db.flush()
        self._record_auth_event(tenant_id, invited_by_user_id, AuthenticationEventType.INVITE_SENT)
        return UserInviteResponse.model_validate(invite), raw_token

    def accept_invite(self, payload: InviteAcceptRequest, ip_address: str | None = None) -> TokenResponse:
        token_h = _token_hash(payload.token)
        stmt = select(UserInvite).where(
            UserInvite.token_hash == token_h,
            UserInvite.is_consumed == False,  # noqa: E712
        )
        invite = self.db.scalar(stmt)
        if invite is None:
            raise TokenInvalidError("Invite token is invalid")
        if invite.expires_at < datetime.now(UTC):
            raise TokenExpiredError("Invite token has expired")

        existing = self.user_repo.get_by_email_and_tenant(invite.email, invite.tenant_id)
        if existing is not None:
            raise EmailAlreadyRegisteredError("Email already registered for this tenant")

        user = self.user_repo.create(
            tenant_id=invite.tenant_id,
            email=invite.email,
            hashed_password=hash_password(payload.password),
            role=invite.role,
        )
        invite.is_consumed = True
        invite.accepted_at = datetime.now(UTC)
        self.db.flush()

        self._record_auth_event(invite.tenant_id, user.id, AuthenticationEventType.INVITE_ACCEPTED, ip_address=ip_address)
        token = create_access_token(str(user.id), str(invite.tenant_id), invite.role)
        return TokenResponse(access_token=token)

    # ─── Password reset ───────────────────────────────────────────────────────

    def request_password_reset(self, payload: PasswordResetRequest, ip_address: str | None = None) -> None:
        """
        Always returns without error even if email not found — prevents enumeration.
        Caller is responsible for sending the email with the raw token.
        """
        user = self.user_repo.get_by_email(payload.email)
        if user is None:
            return  # intentional — no enumeration

        raw_token = secrets.token_urlsafe(48)
        reset = PasswordResetToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=_token_hash(raw_token),
            expires_at=datetime.now(UTC) + timedelta(hours=_RESET_TOKEN_TTL_HOURS),
        )
        self.db.add(reset)
        self.db.flush()
        self._record_auth_event(user.tenant_id, user.id, AuthenticationEventType.PASSWORD_RESET_REQUEST, ip_address=ip_address)
        # NOTE: caller must dispatch email with raw_token out-of-band

    def confirm_password_reset(self, payload: PasswordResetConfirm, ip_address: str | None = None) -> TokenResponse:
        token_h = _token_hash(payload.token)
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_h,
            PasswordResetToken.is_consumed == False,  # noqa: E712
        )
        reset = self.db.scalar(stmt)
        if reset is None:
            raise TokenInvalidError("Reset token is invalid")
        if reset.expires_at < datetime.now(UTC):
            raise TokenExpiredError("Reset token has expired")

        user = self.db.get(User, reset.user_id)
        if user is None:
            raise TokenInvalidError("User no longer exists")

        user.hashed_password = hash_password(payload.new_password)
        reset.is_consumed = True
        self.db.flush()

        self._record_auth_event(user.tenant_id, user.id, AuthenticationEventType.PASSWORD_RESET_COMPLETED, ip_address=ip_address)
        token = create_access_token(str(user.id), str(user.tenant_id), user.role)
        return TokenResponse(access_token=token)

    # ─── Session revocation ───────────────────────────────────────────────────

    def revoke_session(self, session_id: uuid.UUID, reason: str = "logout") -> None:
        session = self.db.get(UserSession, session_id)
        if session and not session.is_revoked:
            session.is_revoked = True
            session.revoked_reason = reason
            self.db.flush()

    # ─── Lockout ──────────────────────────────────────────────────────────────

    def _check_and_apply_lockout(self, user: User) -> None:
        window_start = datetime.now(UTC) - timedelta(minutes=_LOCKOUT_WINDOW_MINUTES)
        stmt = select(AuthenticationEvent).where(
            AuthenticationEvent.user_id == user.id,
            AuthenticationEvent.event_type == AuthenticationEventType.LOGIN_FAILED,
            AuthenticationEvent.created_at >= window_start,
        )
        failures = list(self.db.scalars(stmt))
        if len(failures) >= _MAX_FAILED_ATTEMPTS:
            user.role = "locked"
            self.db.flush()
            self._record_auth_event(user.tenant_id, user.id, AuthenticationEventType.ACCOUNT_LOCKED)

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _record_auth_event(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        event_type: AuthenticationEventType,
        ip_address: str | None = None,
    ) -> None:
        event = AuthenticationEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            metadata_json={},
        )
        self.db.add(event)
        self.db.flush()


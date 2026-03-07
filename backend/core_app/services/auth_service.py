from core_app.core.security import create_access_token, verify_password
from core_app.models.governance import AuthenticationEvent, AuthenticationEventType
from core_app.repositories.user_repository import UserRepository
from core_app.schemas.auth import LoginRequest, TokenResponse


class InvalidCredentialsError(ValueError):
    pass


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    def login(
        self,
        payload: LoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        user = self.user_repo.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            # Log failed auth event if user exists
            if user is not None:
                self._log_auth_event(
                    user.tenant_id, user.id,
                    AuthenticationEventType.LOGIN_FAILED,
                    ip_address, user_agent,
                )
            raise InvalidCredentialsError("Invalid email or password")

        self._log_auth_event(
            user.tenant_id, user.id,
            AuthenticationEventType.LOGIN,
            ip_address, user_agent,
        )
        token = create_access_token(str(user.id), str(user.tenant_id), user.role)
        return TokenResponse(access_token=token)

    def _log_auth_event(
        self,
        tenant_id: object,
        user_id: object,
        event_type: AuthenticationEventType,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        db = self.user_repo.db
        event = AuthenticationEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json={},
        )
        db.add(event)
        db.flush()

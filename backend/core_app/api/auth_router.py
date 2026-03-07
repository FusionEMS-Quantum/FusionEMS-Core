from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.security import create_access_token
from core_app.repositories.user_repository import UserRepository
from core_app.schemas.auth import CurrentUser, LoginRequest, TokenResponse
from core_app.services.auth_service import AuthService, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> TokenResponse:
    service = AuthService(UserRepository(db))
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    try:
        return service.login(payload, ip_address=ip_address, user_agent=user_agent)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


@router.post("/refresh", response_model=TokenResponse)
def refresh(current: CurrentUser = Depends(get_current_user)) -> TokenResponse:
    token = create_access_token(
        str(current.user_id), str(current.tenant_id), current.role or ""
    )
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout(current: CurrentUser = Depends(get_current_user)) -> dict:
    return {"status": "ok"}

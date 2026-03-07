from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    user_id: UUID
    tenant_id: UUID
    role: str


# ─── Registration ────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    role: str = Field(default="ems", pattern=r"^(founder|agency_admin|billing|clinical_provider|ems|dispatcher|compliance|supervisor|viewer)$")
    tenant_id: UUID

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserRegisterResponse(BaseModel):
    id: UUID
    email: str
    role: str
    tenant_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Invite flow ─────────────────────────────────────────────────────────────

class UserInviteCreate(BaseModel):
    email: EmailStr
    role: str = Field(pattern=r"^(agency_admin|billing|clinical_provider|ems|dispatcher|compliance|supervisor|viewer)$")


class UserInviteResponse(BaseModel):
    id: UUID
    email: str
    role: str
    tenant_id: UUID
    expires_at: datetime
    is_consumed: bool

    model_config = {"from_attributes": True}


class InviteAcceptRequest(BaseModel):
    token: str
    password: str = Field(min_length=12)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ─── Password reset ───────────────────────────────────────────────────────────

class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=12)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

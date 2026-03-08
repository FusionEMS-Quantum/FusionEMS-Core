from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

OperationalMode = Literal[
    "HEMS_TRANSPORT",
    "EMS_TRANSPORT",
    "MEDICAL_TRANSPORT",
    "EXTERNAL_911_CAD",
]
BillingMode = Literal["FUSION_RCM", "THIRD_PARTY_EXPORT"]


class OnboardingStartRequest(BaseModel):
    email: EmailStr
    agency_name: str = Field(min_length=2, max_length=255)
    zip_code: str = Field(min_length=3, max_length=16)
    agency_type: str = Field(pattern=r"^(EMS|Fire|HEMS)$")
    annual_call_volume: int = Field(ge=1, le=1000000)
    current_billing_percent: float = Field(ge=0.0, le=30.0)
    payer_mix: dict[str, float] = Field(default_factory=dict)
    level_mix: dict[str, float] = Field(default_factory=dict)
    selected_modules: list[str] = Field(default_factory=list)
    npi_number: str | None = Field(default=None, max_length=20)
    operational_mode: OperationalMode = "EMS_TRANSPORT"
    billing_mode: BillingMode = "FUSION_RCM"
    primary_tail_number: str | None = Field(default=None, max_length=32)
    base_icao: str | None = Field(default=None, max_length=8)
    billing_contact_name: str | None = Field(default=None, max_length=255)
    billing_contact_email: EmailStr | None = None
    implementation_owner_name: str | None = Field(default=None, max_length=255)
    implementation_owner_email: EmailStr | None = None
    identity_sso_preference: str | None = Field(default=None, max_length=64)
    policy_flags: dict[str, Any] = Field(default_factory=dict)


class OnboardingStartResponse(BaseModel):
    application_id: str
    roi_snapshot_hash: str
    status: str
    next_steps: list[str] = Field(default_factory=list)


class ProposalResponse(BaseModel):
    application_id: str
    proposal_pdf_s3_key: str
    proposal_xlsx_s3_key: str
    roi_snapshot_hash: str


class NPPESLookupResponse(BaseModel):
    npi_number: str
    legal_organization_name: str | None = None
    address_line_1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    taxonomy_code: str | None = None
    taxonomy_desc: str | None = None

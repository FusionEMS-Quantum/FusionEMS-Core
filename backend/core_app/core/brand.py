"""
Centralized Brand Identity Configuration
==========================================
Single source of truth for all outbound/inbound patient billing communications
across voice, SMS, fax, email, physical mail, and digital portal experiences.

Default brand: **FusionEMS Quantum**

Multi-tenant Override
---------------------
Each tenant may override any brand field via ``billing_phone_policies.policy_json``
under the ``"brand_overrides"`` key.  Missing keys fall back to platform defaults.

Example ``policy_json``::

    {
        "brand_overrides": {
            "display_name": "Acme Ambulance",
            "sender_email": "billing@acmeambulance.com",
            "billing_phone_e164": "+18005559999",
            "sms_sender_name": "Acme Billing",
            "lob_from_name": "Acme Ambulance Billing"
        }
    }
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.core.config import get_settings

logger = logging.getLogger(__name__)

# Maximum CNAM display name length per LIDB standard
_MAX_CNAM_LEN = 15


def _format_us_phone(e164: str) -> str:
    """Format E.164 US number as (XXX) XXX-XXXX."""
    digits = re.sub(r"\D", "", e164)
    national = digits[1:] if len(digits) == 11 and digits.startswith("1") else digits
    if len(national) != 10:
        return e164
    return f"({national[:3]}) {national[3:6]}-{national[6:]}"


@dataclass(frozen=True)
class BrandIdentity:
    """Immutable brand identity for a single communication context."""

    display_name: str
    """Platform/agency display name (e.g. 'FusionEMS Quantum')."""

    cnam_name: str
    """CNAM caller ID name (≤15 chars per LIDB)."""

    sender_email: str
    """Email 'From' address (e.g. 'noreply@fusionemsquantum.com')."""

    sender_email_display: str
    """Email 'From' display name (e.g. 'FusionEMS Quantum Billing')."""

    billing_phone_e164: str
    """Centralized billing phone in E.164 (e.g. '+18005551234')."""

    billing_phone_display: str
    """Human-readable billing phone (e.g. '(800) 555-1234')."""

    sms_sender_name: str
    """Brand name used in SMS message signatures."""

    lob_from_name: str
    """Return address name on physical LOB mail."""

    domain: str
    """Primary web domain (e.g. 'fusionemsquantum.com')."""

    pdf_header_name: str
    """Header brand name rendered on PDF statements."""

    tenant_id: str | None = field(default=None)
    """Tenant UUID if this identity was resolved for a specific tenant."""


def get_default_brand() -> BrandIdentity:
    """Return platform-default FusionEMS Quantum brand identity from settings."""
    settings = get_settings()
    phone = settings.central_billing_phone_e164 or ""
    return BrandIdentity(
        display_name="FusionEMS Quantum",
        cnam_name=settings.cnam_display_name or "FusionEMS Quantum",
        sender_email=settings.ses_from_email or "noreply@fusionemsquantum.com",
        sender_email_display="FusionEMS Quantum Billing",
        billing_phone_e164=phone,
        billing_phone_display=_format_us_phone(phone),
        sms_sender_name="FusionEMS Quantum",
        lob_from_name="FusionEMS Quantum Billing",
        domain="fusionemsquantum.com",
        pdf_header_name="FusionEMS QUANTUM",
        tenant_id=None,
    )


def resolve_tenant_brand(db: Session, tenant_id: str) -> BrandIdentity:
    """
    Resolve brand identity for a specific tenant.

    Checks ``billing_phone_policies.policy_json['brand_overrides']`` for
    per-tenant customizations, falling back to platform defaults for any
    unset fields.
    """
    default = get_default_brand()

    row = db.execute(
        text(
            "SELECT policy_json FROM billing_phone_policies "
            "WHERE tenant_id = :tid LIMIT 1"
        ),
        {"tid": tenant_id},
    ).mappings().first()

    if not row:
        return BrandIdentity(
            display_name=default.display_name,
            cnam_name=default.cnam_name,
            sender_email=default.sender_email,
            sender_email_display=default.sender_email_display,
            billing_phone_e164=default.billing_phone_e164,
            billing_phone_display=default.billing_phone_display,
            sms_sender_name=default.sms_sender_name,
            lob_from_name=default.lob_from_name,
            domain=default.domain,
            pdf_header_name=default.pdf_header_name,
            tenant_id=tenant_id,
        )

    policy = row.get("policy_json") or {}
    overrides: dict[str, str] = {}
    if isinstance(policy, dict):
        raw_overrides = policy.get("brand_overrides")
        if isinstance(raw_overrides, dict):
            overrides = raw_overrides

    phone_override = str(overrides.get("billing_phone_e164") or "").strip()
    phone = phone_override or default.billing_phone_e164
    cnam_raw = str(overrides.get("cnam_name") or "").strip()
    cnam = cnam_raw[:_MAX_CNAM_LEN] if cnam_raw else default.cnam_name

    return BrandIdentity(
        display_name=str(overrides.get("display_name") or "").strip() or default.display_name,
        cnam_name=cnam,
        sender_email=str(overrides.get("sender_email") or "").strip() or default.sender_email,
        sender_email_display=str(overrides.get("sender_email_display") or "").strip() or default.sender_email_display,
        billing_phone_e164=phone,
        billing_phone_display=_format_us_phone(phone) if phone else default.billing_phone_display,
        sms_sender_name=str(overrides.get("sms_sender_name") or "").strip() or default.sms_sender_name,
        lob_from_name=str(overrides.get("lob_from_name") or "").strip() or default.lob_from_name,
        domain=str(overrides.get("domain") or "").strip() or default.domain,
        pdf_header_name=str(overrides.get("pdf_header_name") or "").strip() or default.pdf_header_name,
        tenant_id=tenant_id,
    )

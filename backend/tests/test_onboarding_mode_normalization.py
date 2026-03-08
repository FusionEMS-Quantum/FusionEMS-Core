"""Sovereign onboarding mode normalization tests.

Ensures billing and operational fork values are constrained to supported enums.
"""
from __future__ import annotations

from core_app.api.onboarding_router import (
    _normalize_billing_mode,
    _normalize_operational_mode,
)


def test_normalize_operational_mode_valid() -> None:
    assert _normalize_operational_mode("hems_transport") == "HEMS_TRANSPORT"
    assert _normalize_operational_mode("EXTERNAL_911_CAD") == "EXTERNAL_911_CAD"


def test_normalize_operational_mode_default() -> None:
    assert _normalize_operational_mode("unknown") == "EMS_TRANSPORT"


def test_normalize_billing_mode_valid() -> None:
    assert _normalize_billing_mode("fusion_rcm") == "FUSION_RCM"
    assert _normalize_billing_mode("THIRD_PARTY_EXPORT") == "THIRD_PARTY_EXPORT"


def test_normalize_billing_mode_default() -> None:
    assert _normalize_billing_mode("legacy_vendor") == "FUSION_RCM"

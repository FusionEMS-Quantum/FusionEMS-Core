from __future__ import annotations

import pytest

from core_app.pricing.catalog import (
    ADDONS,
    BILLING_MODES,
    BILLING_TIERS,
    PLANS,
    SCHEDULING_TIERS,
    calculate_quote,
    get_catalog,
    lookup_key_to_cents,
    resolve_selected_modules,
)


def test_calculate_quote_scheduling_only_s1() -> None:
    quote = calculate_quote(plan_code="SCHEDULING_ONLY", tier_code="S1")
    assert quote.requires_quote is False
    assert quote.base_monthly_cents == 19900
    assert quote.total_monthly_cents == 19900
    assert quote.addon_monthly_cents == 0
    assert len(quote.stripe_line_items) == 1
    assert quote.stripe_line_items[0]["lookup_key"] == "SCHEDULING_ONLY_S1_V1_MONTHLY"


def test_calculate_quote_scheduling_only_all_tiers() -> None:
    expected = {"S1": 19900, "S2": 39900, "S3": 69900}
    for tier_code, cents in expected.items():
        quote = calculate_quote(plan_code="SCHEDULING_ONLY", tier_code=tier_code)
        assert quote.total_monthly_cents == cents, f"Tier {tier_code}: expected {cents}"


def test_calculate_quote_core_plans_are_self_serve() -> None:
    expected = {
        "OPS_CORE": 129900,
        "CLINICAL_CORE": 149900,
        "FULL_STACK": 249900,
    }
    for plan_code, cents in expected.items():
        quote = calculate_quote(plan_code=plan_code)
        assert quote.requires_quote is False
        assert quote.total_monthly_cents == cents
        assert quote.stripe_line_items[0]["lookup_key"] == PLANS[plan_code].lookup_key


def test_calculate_quote_billing_automation_requires_billing_tier() -> None:
    with pytest.raises(ValueError, match="billing_tier_code is required"):
        calculate_quote(
            plan_code="SCHEDULING_ONLY",
            tier_code="S1",
            addon_codes=["BILLING_AUTOMATION"],
        )


def test_calculate_quote_fusion_rcm_billing_automation() -> None:
    quote = calculate_quote(
        plan_code="SCHEDULING_ONLY",
        tier_code="S1",
        addon_codes=["BILLING_AUTOMATION"],
        billing_tier_code="B1",
        billing_mode="FUSION_RCM",
    )
    assert quote.addon_monthly_cents == 39900
    assert quote.total_monthly_cents == 19900 + 39900
    lookup_keys = [item["lookup_key"] for item in quote.stripe_line_items]
    assert "BILLING_AUTOMATION_B1_BASE_V1_MONTHLY" in lookup_keys
    assert "BILLING_AUTOMATION_B1_PER_CLAIM_V1" in lookup_keys
    assert "central_billing" in quote.module_codes
    assert "patient_statements" in quote.module_codes


def test_calculate_quote_third_party_billing_automation() -> None:
    quote = calculate_quote(
        plan_code="SCHEDULING_ONLY",
        tier_code="S1",
        addon_codes=["BILLING_AUTOMATION"],
        billing_tier_code="TPB1",
        billing_mode="THIRD_PARTY_EXPORT",
    )
    assert quote.addon_monthly_cents == 14900
    assert quote.total_monthly_cents == 19900 + 14900
    lookup_keys = [item["lookup_key"] for item in quote.stripe_line_items]
    assert "THIRD_PARTY_EXPORT_B1_BASE_V1_MONTHLY" in lookup_keys
    assert "THIRD_PARTY_EXPORT_B1_PER_CLAIM_V1" in lookup_keys
    assert "third_party_billing_export" in quote.module_codes
    assert "data_portability" in quote.module_codes


def test_calculate_quote_rejects_mismatched_billing_mode_and_tier() -> None:
    with pytest.raises(ValueError, match="is not valid for billing_mode"):
        calculate_quote(
            plan_code="SCHEDULING_ONLY",
            tier_code="S1",
            addon_codes=["BILLING_AUTOMATION"],
            billing_tier_code="TPB1",
            billing_mode="FUSION_RCM",
        )


def test_resolve_selected_modules_includes_operational_and_agency_overrides() -> None:
    modules = resolve_selected_modules(
        plan_code="OPS_CORE",
        addon_codes=["NERIS_FIRE", "HEMS_OPS"],
        billing_mode="THIRD_PARTY_EXPORT",
        billing_tier_code="TPB2",
        operational_mode="HEMS_TRANSPORT",
        agency_type="Fire EMS",
    )
    assert "operations_command" in modules
    assert "hems" in modules
    assert "aviation_missions" in modules
    assert "neris" in modules
    assert "fire_module" in modules
    assert "third_party_billing_export" in modules
    assert "data_export" in modules


def test_lookup_key_to_cents_supports_all_catalog_paths() -> None:
    assert lookup_key_to_cents("OPS_CORE_V1_MONTHLY") == 129900
    assert lookup_key_to_cents("SCHEDULING_ONLY_S2_V1_MONTHLY") == 39900
    assert lookup_key_to_cents("BILLING_AUTOMATION_B2_BASE_V1_MONTHLY") == 59900
    assert lookup_key_to_cents("THIRD_PARTY_EXPORT_B3_PER_CLAIM_V1") == 95
    assert lookup_key_to_cents("PATIENT_STATEMENTS_AI_V1_MONTHLY") == 14900


def test_get_catalog_structure() -> None:
    catalog = get_catalog()
    assert "plans" in catalog
    assert "scheduling_tiers" in catalog
    assert "billing_tiers" in catalog
    assert "addons" in catalog
    assert "billing_modes" in catalog
    assert len(catalog["plans"]) == len(PLANS)
    assert len(catalog["scheduling_tiers"]) == len(SCHEDULING_TIERS)
    assert len(catalog["billing_tiers"]) == len(BILLING_TIERS)
    assert len(catalog["addons"]) == len(ADDONS)
    assert len(catalog["billing_modes"]) == len(BILLING_MODES)


def test_get_catalog_plan_fields() -> None:
    catalog = get_catalog()
    for plan in catalog["plans"]:
        assert "code" in plan
        assert "label" in plan
        assert "contact_sales" in plan
        assert "price_display" in plan
        assert "included_modules" in plan


def test_get_catalog_scheduling_tier_price_display() -> None:
    catalog = get_catalog()
    tiers = {tier["code"]: tier for tier in catalog["scheduling_tiers"]}
    assert tiers["S1"]["price_display"] == "$199/mo"
    assert tiers["S2"]["price_display"] == "$399/mo"
    assert tiers["S3"]["price_display"] == "$699/mo"

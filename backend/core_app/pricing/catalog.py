from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SchedulingTier:
    code: str
    label: str
    monthly_cents: int
    lookup_key: str


@dataclass(frozen=True)
class BillingTier:
    code: str
    label: str
    base_monthly_cents: int
    per_claim_cents: int
    base_lookup_key: str
    per_claim_lookup_key: str
    billing_mode: str


@dataclass(frozen=True)
class BillingMode:
    code: str
    label: str
    description: str
    tier_prefix: str
    included_modules: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    code: str
    label: str
    desc: str
    contact_sales: bool
    color: str
    monthly_cents: int
    lookup_key: str
    included_modules: tuple[str, ...]


@dataclass(frozen=True)
class Addon:
    code: str
    label: str
    monthly_cents: int
    gov_only: bool
    uses_billing_tier: bool
    lookup_key: str
    included_modules: tuple[str, ...]


@dataclass
class QuoteResult:
    plan_code: str
    tier_code: str | None
    billing_tier_code: str | None
    addon_codes: list[str]
    base_monthly_cents: int
    addon_monthly_cents: int
    total_monthly_cents: int
    requires_quote: bool
    stripe_line_items: list[dict[str, Any]] = field(default_factory=list)
    module_codes: list[str] = field(default_factory=list)


SCHEDULING_TIERS: dict[str, SchedulingTier] = {
    "S1": SchedulingTier(
        code="S1",
        label="1–25 active users",
        monthly_cents=19900,
        lookup_key="SCHEDULING_ONLY_S1_V1_MONTHLY",
    ),
    "S2": SchedulingTier(
        code="S2",
        label="26–75 active users",
        monthly_cents=39900,
        lookup_key="SCHEDULING_ONLY_S2_V1_MONTHLY",
    ),
    "S3": SchedulingTier(
        code="S3",
        label="76–150 active users",
        monthly_cents=69900,
        lookup_key="SCHEDULING_ONLY_S3_V1_MONTHLY",
    ),
}

BILLING_MODES: dict[str, BillingMode] = {
    "FUSION_RCM": BillingMode(
        code="FUSION_RCM",
        label="FusionEMS Revenue Cycle Management",
        description="Centralized FusionEMS billing operations and patient statement handling.",
        tier_prefix="B",
        included_modules=("central_billing", "patient_statements"),
    ),
    "THIRD_PARTY_EXPORT": BillingMode(
        code="THIRD_PARTY_EXPORT",
        label="Third-Party Billing Export",
        description="Export-ready billing workflows for agency-selected external billing partners.",
        tier_prefix="TPB",
        included_modules=("third_party_billing_export", "data_export", "data_portability"),
    ),
}

BILLING_TIERS: dict[str, BillingTier] = {
    "B1": BillingTier(
        code="B1",
        label="0–150 claims/mo",
        base_monthly_cents=39900,
        per_claim_cents=600,
        base_lookup_key="BILLING_AUTOMATION_B1_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B1_PER_CLAIM_V1",
        billing_mode="FUSION_RCM",
    ),
    "B2": BillingTier(
        code="B2",
        label="151–400 claims/mo",
        base_monthly_cents=59900,
        per_claim_cents=500,
        base_lookup_key="BILLING_AUTOMATION_B2_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B2_PER_CLAIM_V1",
        billing_mode="FUSION_RCM",
    ),
    "B3": BillingTier(
        code="B3",
        label="401–1,000 claims/mo",
        base_monthly_cents=99900,
        per_claim_cents=400,
        base_lookup_key="BILLING_AUTOMATION_B3_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B3_PER_CLAIM_V1",
        billing_mode="FUSION_RCM",
    ),
    "B4": BillingTier(
        code="B4",
        label="1,001+ claims/mo",
        base_monthly_cents=149900,
        per_claim_cents=325,
        base_lookup_key="BILLING_AUTOMATION_B4_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B4_PER_CLAIM_V1",
        billing_mode="FUSION_RCM",
    ),
    "TPB1": BillingTier(
        code="TPB1",
        label="0–150 claims/mo",
        base_monthly_cents=14900,
        per_claim_cents=125,
        base_lookup_key="THIRD_PARTY_EXPORT_B1_BASE_V1_MONTHLY",
        per_claim_lookup_key="THIRD_PARTY_EXPORT_B1_PER_CLAIM_V1",
        billing_mode="THIRD_PARTY_EXPORT",
    ),
    "TPB2": BillingTier(
        code="TPB2",
        label="151–400 claims/mo",
        base_monthly_cents=19900,
        per_claim_cents=110,
        base_lookup_key="THIRD_PARTY_EXPORT_B2_BASE_V1_MONTHLY",
        per_claim_lookup_key="THIRD_PARTY_EXPORT_B2_PER_CLAIM_V1",
        billing_mode="THIRD_PARTY_EXPORT",
    ),
    "TPB3": BillingTier(
        code="TPB3",
        label="401–1,000 claims/mo",
        base_monthly_cents=24900,
        per_claim_cents=95,
        base_lookup_key="THIRD_PARTY_EXPORT_B3_BASE_V1_MONTHLY",
        per_claim_lookup_key="THIRD_PARTY_EXPORT_B3_PER_CLAIM_V1",
        billing_mode="THIRD_PARTY_EXPORT",
    ),
    "TPB4": BillingTier(
        code="TPB4",
        label="1,001+ claims/mo",
        base_monthly_cents=29900,
        per_claim_cents=85,
        base_lookup_key="THIRD_PARTY_EXPORT_B4_BASE_V1_MONTHLY",
        per_claim_lookup_key="THIRD_PARTY_EXPORT_B4_PER_CLAIM_V1",
        billing_mode="THIRD_PARTY_EXPORT",
    ),
}

PLANS: dict[str, Plan] = {
    "SCHEDULING_ONLY": Plan(
        code="SCHEDULING_ONLY",
        label="Scheduling Only",
        desc="Calendar, shifts, crew, bids, scheduling PWA",
        contact_sales=False,
        color="var(--color-status-info)",
        monthly_cents=0,
        lookup_key="",
        included_modules=("scheduling", "crewlink"),
    ),
    "OPS_CORE": Plan(
        code="OPS_CORE",
        label="Ops Core",
        desc="TransportLink + CAD + CrewLink + Scheduling",
        contact_sales=False,
        color="var(--q-green)",
        monthly_cents=129900,
        lookup_key="OPS_CORE_V1_MONTHLY",
        included_modules=("operations_command", "transportlink", "crewlink", "scheduling"),
    ),
    "CLINICAL_CORE": Plan(
        code="CLINICAL_CORE",
        label="Clinical Core",
        desc="ePCR + NEMSIS/WI validation + Scheduling",
        contact_sales=False,
        color="var(--color-system-compliance)",
        monthly_cents=149900,
        lookup_key="CLINICAL_CORE_V1_MONTHLY",
        included_modules=("epcr", "clinical_documentation", "nemsis_export", "scheduling"),
    ),
    "FULL_STACK": Plan(
        code="FULL_STACK",
        label="Full Stack",
        desc="Everything — Ops + Clinical + HEMS + NERIS",
        contact_sales=False,
        color="var(--q-orange)",
        monthly_cents=249900,
        lookup_key="FULL_STACK_V1_MONTHLY",
        included_modules=(
            "operations_command",
            "transportlink",
            "crewlink",
            "scheduling",
            "epcr",
            "clinical_documentation",
            "nemsis_export",
            "hems",
            "aviation_missions",
            "neris",
            "fire_module",
        ),
    ),
}

ADDONS: dict[str, Addon] = {
    "CCT_TRANSPORT_OPS": Addon(
        code="CCT_TRANSPORT_OPS",
        label="CCT / Transport Ops",
        monthly_cents=39900,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="CCT_TRANSPORT_OPS_V1_MONTHLY",
        included_modules=("critical_care_transport",),
    ),
    "HEMS_OPS": Addon(
        code="HEMS_OPS",
        label="HEMS Ops (rotor + fixed-wing)",
        monthly_cents=75000,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="HEMS_OPS_V1_MONTHLY",
        included_modules=("hems", "aviation_missions"),
    ),
    "BILLING_AUTOMATION": Addon(
        code="BILLING_AUTOMATION",
        label="Billing Automation",
        monthly_cents=0,
        gov_only=False,
        uses_billing_tier=True,
        lookup_key="",
        included_modules=("billing",),
    ),
    "PATIENT_STATEMENTS_AI": Addon(
        code="PATIENT_STATEMENTS_AI",
        label="Patient Statements AI",
        monthly_cents=14900,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="PATIENT_STATEMENTS_AI_V1_MONTHLY",
        included_modules=("patient_statements_ai",),
    ),
    "NERIS_FIRE": Addon(
        code="NERIS_FIRE",
        label="NERIS Fire Operations",
        monthly_cents=29900,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="NERIS_FIRE_V1_MONTHLY",
        included_modules=("neris", "fire_module"),
    ),
    "TRIP_PACK": Addon(
        code="TRIP_PACK",
        label="Wisconsin TRIP Pack (gov agencies only)",
        monthly_cents=19900,
        gov_only=True,
        uses_billing_tier=False,
        lookup_key="TRIP_PACK_V1_MONTHLY",
        included_modules=("trip_pack",),
    ),
}


def _fmt_cents(cents: int) -> str:
    dollars, remainder = divmod(cents, 100)
    if remainder == 0:
        return f"${dollars}"
    return f"${dollars}.{remainder:02d}"


def _billing_mode_for_tier(
    billing_mode: str | None, billing_tier_code: str | None, addon_codes: list[str]
) -> str | None:
    if "BILLING_AUTOMATION" not in addon_codes and not billing_mode and not billing_tier_code:
        return None
    normalized_mode = (billing_mode or "FUSION_RCM").strip().upper()
    if normalized_mode not in BILLING_MODES:
        raise ValueError(f"Unknown billing_mode: {billing_mode!r}")
    if billing_tier_code:
        tier = BILLING_TIERS.get(billing_tier_code)
        if tier is None:
            raise ValueError(f"Unknown billing_tier_code: {billing_tier_code!r}")
        if tier.billing_mode != normalized_mode:
            raise ValueError(
                f"billing_tier_code {billing_tier_code!r} is not valid for billing_mode {normalized_mode!r}"
            )
    return normalized_mode


def resolve_selected_modules(
    plan_code: str,
    addon_codes: list[str] | None = None,
    billing_mode: str | None = None,
    billing_tier_code: str | None = None,
    operational_mode: str | None = None,
    agency_type: str | None = None,
) -> list[str]:
    if plan_code not in PLANS:
        raise ValueError(f"Unknown plan_code: {plan_code!r}")

    selected: set[str] = set(PLANS[plan_code].included_modules)
    addon_codes = list(addon_codes or [])

    for addon_code in addon_codes:
        addon = ADDONS.get(addon_code)
        if addon is None:
            raise ValueError(f"Unknown addon_code: {addon_code!r}")
        selected.update(addon.included_modules)

    normalized_mode = _billing_mode_for_tier(billing_mode, billing_tier_code, addon_codes)
    if normalized_mode:
        selected.update(BILLING_MODES[normalized_mode].included_modules)

    normalized_operational_mode = (operational_mode or "").strip().upper()
    if normalized_operational_mode == "HEMS_TRANSPORT":
        selected.update({"hems", "aviation_missions"})

    normalized_agency_type = (agency_type or "").strip().lower()
    if "fire" in normalized_agency_type:
        selected.add("fire_module")
        if "NERIS_FIRE" in addon_codes:
            selected.add("neris")

    return sorted(selected)


def calculate_quote(
    plan_code: str,
    tier_code: str | None = None,
    billing_tier_code: str | None = None,
    addon_codes: list[str] | None = None,
    billing_mode: str | None = None,
    operational_mode: str | None = None,
    agency_type: str | None = None,
) -> QuoteResult:
    if plan_code not in PLANS:
        raise ValueError(f"Unknown plan_code: {plan_code!r}")

    plan = PLANS[plan_code]
    addon_codes = list(addon_codes or [])
    normalized_mode = _billing_mode_for_tier(billing_mode, billing_tier_code, addon_codes)

    for addon_code in addon_codes:
        if addon_code not in ADDONS:
            raise ValueError(f"Unknown addon_code: {addon_code!r}")

    stripe_line_items: list[dict[str, Any]] = []
    if plan_code == "SCHEDULING_ONLY":
        if not tier_code:
            raise ValueError("tier_code is required for SCHEDULING_ONLY plan")
        if tier_code not in SCHEDULING_TIERS:
            raise ValueError(f"Unknown tier_code: {tier_code!r}")
        tier = SCHEDULING_TIERS[tier_code]
        base_monthly_cents = tier.monthly_cents
        stripe_line_items.append({"lookup_key": tier.lookup_key, "quantity": 1, "metered": False})
    else:
        base_monthly_cents = plan.monthly_cents
        stripe_line_items.append({"lookup_key": plan.lookup_key, "quantity": 1, "metered": False})

    addon_monthly_cents = 0
    for addon_code in addon_codes:
        addon = ADDONS[addon_code]
        if addon.uses_billing_tier:
            if not billing_tier_code:
                raise ValueError("billing_tier_code is required for addon 'BILLING_AUTOMATION'")
            tier = BILLING_TIERS.get(billing_tier_code)
            if tier is None:
                raise ValueError(f"Unknown billing_tier_code: {billing_tier_code!r}")
            addon_monthly_cents += tier.base_monthly_cents
            stripe_line_items.append(
                {"lookup_key": tier.base_lookup_key, "quantity": 1, "metered": False}
            )
            stripe_line_items.append({"lookup_key": tier.per_claim_lookup_key, "metered": True})
        else:
            addon_monthly_cents += addon.monthly_cents
            if addon.lookup_key:
                stripe_line_items.append(
                    {"lookup_key": addon.lookup_key, "quantity": 1, "metered": False}
                )

    module_codes = resolve_selected_modules(
        plan_code=plan_code,
        addon_codes=addon_codes,
        billing_mode=normalized_mode,
        billing_tier_code=billing_tier_code,
        operational_mode=operational_mode,
        agency_type=agency_type,
    )

    return QuoteResult(
        plan_code=plan_code,
        tier_code=tier_code,
        billing_tier_code=billing_tier_code,
        addon_codes=addon_codes,
        base_monthly_cents=base_monthly_cents,
        addon_monthly_cents=addon_monthly_cents,
        total_monthly_cents=base_monthly_cents + addon_monthly_cents,
        requires_quote=plan.contact_sales,
        stripe_line_items=stripe_line_items,
        module_codes=module_codes,
    )


def lookup_key_to_cents(lookup_key: str) -> int:
    for plan in PLANS.values():
        if plan.lookup_key == lookup_key:
            return plan.monthly_cents
    for tier in SCHEDULING_TIERS.values():
        if tier.lookup_key == lookup_key:
            return tier.monthly_cents
    for billing_tier in BILLING_TIERS.values():
        if billing_tier.base_lookup_key == lookup_key:
            return billing_tier.base_monthly_cents
        if billing_tier.per_claim_lookup_key == lookup_key:
            return billing_tier.per_claim_cents
    for addon in ADDONS.values():
        if addon.lookup_key == lookup_key:
            return addon.monthly_cents
    return 0


def get_catalog() -> dict[str, list[dict[str, Any]]]:
    return {
        "plans": [
            {
                "code": plan.code,
                "label": plan.label,
                "desc": plan.desc,
                "contact_sales": plan.contact_sales,
                "color": plan.color,
                "price_display": "Contact us"
                if plan.contact_sales
                else (
                    f"from {_fmt_cents(min(t.monthly_cents for t in SCHEDULING_TIERS.values()))}/mo"
                    if plan.code == "SCHEDULING_ONLY"
                    else f"{_fmt_cents(plan.monthly_cents)}/mo"
                ),
                "included_modules": list(plan.included_modules),
            }
            for plan in PLANS.values()
        ],
        "scheduling_tiers": [
            {
                "code": tier.code,
                "label": tier.label,
                "monthly_cents": tier.monthly_cents,
                "price_display": f"{_fmt_cents(tier.monthly_cents)}/mo",
            }
            for tier in SCHEDULING_TIERS.values()
        ],
        "billing_tiers": [
            {
                "code": tier.code,
                "label": tier.label,
                "billing_mode": tier.billing_mode,
                "base_monthly_cents": tier.base_monthly_cents,
                "per_claim_cents": tier.per_claim_cents,
                "base_display": f"{_fmt_cents(tier.base_monthly_cents)}/mo",
                "per_claim_display": f"+{_fmt_cents(tier.per_claim_cents)}/claim",
            }
            for tier in BILLING_TIERS.values()
        ],
        "addons": [
            {
                "code": addon.code,
                "label": addon.label,
                "monthly_cents": addon.monthly_cents,
                "gov_only": addon.gov_only,
                "uses_billing_tier": addon.uses_billing_tier,
                "price_display": (
                    "see billing_tiers"
                    if addon.uses_billing_tier
                    else f"+{_fmt_cents(addon.monthly_cents)}/mo"
                ),
                "included_modules": list(addon.included_modules),
            }
            for addon in ADDONS.values()
        ],
        "billing_modes": [
            {
                "code": mode.code,
                "label": mode.label,
                "description": mode.description,
                "included_modules": list(mode.included_modules),
            }
            for mode in BILLING_MODES.values()
        ],
    }

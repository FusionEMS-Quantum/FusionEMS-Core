from __future__ import annotations

from dataclasses import dataclass, field


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


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
    mode: str
    base_monthly_cents: int
    per_claim_cents: int
    base_lookup_key: str
    per_claim_lookup_key: str


@dataclass(frozen=True)
class Plan:
    code: str
    label: str
    desc: str
    contact_sales: bool
    color: str
    monthly_cents: int | None = None
    lookup_key: str | None = None
    included_modules: tuple[str, ...] = ()


@dataclass(frozen=True)
class Addon:
    code: str
    label: str
    desc: str
    monthly_cents: int
    gov_only: bool
    uses_billing_tier: bool
    lookup_key: str
    included_modules: tuple[str, ...] = ()


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
    stripe_line_items: list[dict] = field(default_factory=list)
    module_codes: list[str] = field(default_factory=list)


DEFAULT_BILLING_MODE = "FUSION_RCM"


BILLING_MODES: dict[str, dict[str, str]] = {
    "FUSION_RCM": {
        "label": "FusionEMS AI Billing Center",
        "summary": (
            "Fixed-fee AI-assisted RCM with claim automation, patient statements, "
            "Office Ally workflows, and real-time revenue analytics."
        ),
    },
    "THIRD_PARTY_EXPORT": {
        "label": "Internal / Third-Party Billing",
        "summary": (
            "Export-first billing support for agencies keeping their internal or external biller, "
            "with predictable fixed pricing instead of percentage skims."
        ),
    },
}


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


BILLING_TIERS: dict[str, BillingTier] = {
    "B1": BillingTier(
        code="B1",
        label="0–150 claims/mo",
        mode="FUSION_RCM",
        base_monthly_cents=39900,
        per_claim_cents=600,
        base_lookup_key="BILLING_AUTOMATION_B1_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B1_PER_CLAIM_V1",
    ),
    "B2": BillingTier(
        code="B2",
        label="151–400 claims/mo",
        mode="FUSION_RCM",
        base_monthly_cents=59900,
        per_claim_cents=500,
        base_lookup_key="BILLING_AUTOMATION_B2_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B2_PER_CLAIM_V1",
    ),
    "B3": BillingTier(
        code="B3",
        label="401–1,000 claims/mo",
        mode="FUSION_RCM",
        base_monthly_cents=99900,
        per_claim_cents=400,
        base_lookup_key="BILLING_AUTOMATION_B3_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B3_PER_CLAIM_V1",
    ),
    "B4": BillingTier(
        code="B4",
        label="1,001+ claims/mo",
        mode="FUSION_RCM",
        base_monthly_cents=149900,
        per_claim_cents=325,
        base_lookup_key="BILLING_AUTOMATION_B4_BASE_V1_MONTHLY",
        per_claim_lookup_key="BILLING_AUTOMATION_B4_PER_CLAIM_V1",
    ),
    "TPB1": BillingTier(
        code="TPB1",
        label="0–150 claims/mo",
        mode="THIRD_PARTY_EXPORT",
        base_monthly_cents=14900,
        per_claim_cents=125,
        base_lookup_key="THIRD_PARTY_EXPORT_B1_BASE_V1_MONTHLY",
        per_claim_lookup_key="THIRD_PARTY_EXPORT_B1_PER_CLAIM_V1",
    ),
    "TPB2": BillingTier(
        code="TPB2",
        label="151–400 claims/mo",
        mode="THIRD_PARTY_EXPORT",
        base_monthly_cents=24900,
        per_claim_cents=110,
        base_lookup_key="THIRD_PARTY_EXPORT_B2_BASE_V1_MONTHLY",
        per_claim_lookup_key="THIRD_PARTY_EXPORT_B2_PER_CLAIM_V1",
    ),
    "TPB3": BillingTier(
        code="TPB3",
        label="401–1,000 claims/mo",
        mode="THIRD_PARTY_EXPORT",
        base_monthly_cents=39900,
        per_claim_cents=95,
        base_lookup_key="THIRD_PARTY_EXPORT_B3_BASE_V1_MONTHLY",
        per_claim_lookup_key="THIRD_PARTY_EXPORT_B3_PER_CLAIM_V1",
    ),
    "TPB4": BillingTier(
        code="TPB4",
        label="1,001+ claims/mo",
        mode="THIRD_PARTY_EXPORT",
        base_monthly_cents=59900,
        per_claim_cents=85,
        base_lookup_key="THIRD_PARTY_EXPORT_B4_BASE_V1_MONTHLY",
        per_claim_lookup_key="THIRD_PARTY_EXPORT_B4_PER_CLAIM_V1",
    ),
}


PLANS: dict[str, Plan] = {
    "SCHEDULING_ONLY": Plan(
        code="SCHEDULING_ONLY",
        label="Scheduling Only",
        desc="Calendar, shifts, crew, bids, scheduling PWA",
        contact_sales=False,
        color="var(--color-status-info)",
        included_modules=("scheduling", "crewlink", "data_export"),
    ),
    "OPS_CORE": Plan(
        code="OPS_CORE",
        label="Ops Core",
        desc="TransportLink + CAD + CrewLink + Scheduling + command analytics",
        contact_sales=False,
        color="var(--q-green)",
        monthly_cents=129900,
        lookup_key="OPS_CORE_V1_MONTHLY",
        included_modules=(
            "operations_command",
            "transportlink",
            "dispatch",
            "cad_module",
            "crewlink",
            "scheduling",
            "realtime_analytics",
            "data_export",
        ),
    ),
    "CLINICAL_CORE": Plan(
        code="CLINICAL_CORE",
        label="Clinical Core",
        desc="ePCR + NEMSIS/WI validation + patient portal + clinical QA",
        contact_sales=False,
        color="var(--color-system-compliance)",
        monthly_cents=149900,
        lookup_key="CLINICAL_CORE_V1_MONTHLY",
        included_modules=(
            "clinical_command",
            "epcr",
            "nemsis_export",
            "patient_portal",
            "quality_assurance",
            "realtime_analytics",
            "data_export",
        ),
    ),
    "FULL_STACK": Plan(
        code="FULL_STACK",
        label="Full Stack",
        desc="Everything — Ops + Clinical + Billing + HEMS + NERIS + portability",
        contact_sales=False,
        color="var(--q-orange)",
        monthly_cents=249900,
        lookup_key="FULL_STACK_V1_MONTHLY",
        included_modules=(
            "analytics",
            "billing",
            "cad_module",
            "clinical_command",
            "communications",
            "compliance",
            "crewlink",
            "dispatch",
            "epcr",
            "fleet",
            "nemsis_export",
            "operations_command",
            "patient_portal",
            "patient_statements",
            "lob_print_mail",
            "office_ally_edi",
            "npi_verification",
            "realtime_analytics",
            "scheduling",
            "system_command",
            "transportlink",
            "data_export",
        ),
    ),
}


ADDONS: dict[str, Addon] = {
    "CCT_TRANSPORT_OPS": Addon(
        code="CCT_TRANSPORT_OPS",
        label="CCT / Transport Ops",
        desc="Advanced transport coordination for interfacility, specialty, and CCT workflows.",
        monthly_cents=39900,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="CCT_TRANSPORT_OPS_V1_MONTHLY",
        included_modules=("cct_transport", "medical_necessity_workflows"),
    ),
    "HEMS_OPS": Addon(
        code="HEMS_OPS",
        label="HEMS Ops (rotor + fixed-wing)",
        desc="Mission ops, tail tracking, aviation workflows, and base readiness for HEMS teams.",
        monthly_cents=75000,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="HEMS_OPS_V1_MONTHLY",
        included_modules=("aviation_missions", "hems"),
    ),
    "BILLING_AUTOMATION": Addon(
        code="BILLING_AUTOMATION",
        label="Billing Automation",
        desc="AI billing, payer workflow automation, patient statements, and revenue command center analytics.",
        monthly_cents=0,
        gov_only=False,
        uses_billing_tier=True,
        lookup_key="",
        included_modules=(),
    ),
    "PATIENT_STATEMENTS_AI": Addon(
        code="PATIENT_STATEMENTS_AI",
        label="Patient Statements + Lob Mail",
        desc="Print/mail statements, digital statement delivery, and AI-assisted payment follow-up orchestration.",
        monthly_cents=14900,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="PATIENT_STATEMENTS_AI_V1_MONTHLY",
        included_modules=("patient_statements", "lob_print_mail", "statement_ai"),
    ),
    "OFFICE_ALLY_CONNECT": Addon(
        code="OFFICE_ALLY_CONNECT",
        label="Office Ally + NPI Verification",
        desc="Clearinghouse connectivity, NPI validation, claim status, and ERA visibility.",
        monthly_cents=9900,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="OFFICE_ALLY_CONNECT_V1_MONTHLY",
        included_modules=("office_ally_edi", "claim_status", "npi_verification"),
    ),
    "FLEET_COMMAND": Addon(
        code="FLEET_COMMAND",
        label="Fleet Command",
        desc="Vehicle readiness, maintenance tracking, defect alerts, and serviceability control.",
        monthly_cents=34900,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="FLEET_COMMAND_V1_MONTHLY",
        included_modules=("fleet",),
    ),
    "COMMS_COMMAND": Addon(
        code="COMMS_COMMAND",
        label="Comms Command",
        desc="Voice, SMS, callback orchestration, and centralized patient communication lanes.",
        monthly_cents=24900,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="COMMS_COMMAND_V1_MONTHLY",
        included_modules=("communications", "voice_ai", "sms_workflows"),
    ),
    "COMPLIANCE_COMMAND": Addon(
        code="COMPLIANCE_COMMAND",
        label="Compliance Command",
        desc="DEA/CMS, HIPAA, and audit-evidence workflows in a single operator lane.",
        monthly_cents=19900,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="COMPLIANCE_COMMAND_V1_MONTHLY",
        included_modules=("compliance", "audit_center"),
    ),
    "NERIS_FIRE": Addon(
        code="NERIS_FIRE",
        label="NERIS Fire Command",
        desc="Wisconsin-first fire and NERIS onboarding, validation, and export readiness.",
        monthly_cents=24900,
        gov_only=False,
        uses_billing_tier=False,
        lookup_key="NERIS_FIRE_V1_MONTHLY",
        included_modules=("fire_module", "neris"),
    ),
    "TRIP_PACK": Addon(
        code="TRIP_PACK",
        label="Wisconsin TRIP Pack (gov agencies only)",
        desc="Wisconsin state-program automation and debt-recovery workflow support for public agencies.",
        monthly_cents=19900,
        gov_only=True,
        uses_billing_tier=False,
        lookup_key="TRIP_PACK_V1_MONTHLY",
        included_modules=("state_programs", "trip_pack"),
    ),
}


def _normalize_billing_mode(value: str | None) -> str:
    candidate = str(value or DEFAULT_BILLING_MODE).strip().upper()
    return candidate if candidate in BILLING_MODES else DEFAULT_BILLING_MODE


def _billing_modules_for_mode(billing_mode: str) -> list[str]:
    if billing_mode == "THIRD_PARTY_EXPORT":
        return [
            "billing",
            "third_party_billing_export",
            "remit_exports",
            "realtime_analytics",
            "data_portability",
        ]
    return [
        "billing",
        "central_billing",
        "rcm_automation",
        "patient_portal",
        "realtime_analytics",
    ]


def resolve_selected_modules(
    *,
    plan_code: str,
    addon_codes: list[str] | None = None,
    billing_mode: str | None = None,
    billing_tier_code: str | None = None,
    operational_mode: str | None = None,
    agency_type: str | None = None,
) -> list[str]:
    if plan_code not in PLANS:
        raise ValueError(f"Unknown plan_code: {plan_code!r}")

    billing_mode_normalized = _normalize_billing_mode(billing_mode)
    resolved = list(PLANS[plan_code].included_modules)
    addon_codes = list(addon_codes or [])

    for addon_code in addon_codes:
        addon = ADDONS.get(addon_code)
        if addon is None:
            raise ValueError(f"Unknown addon_code: {addon_code!r}")
        resolved.extend(addon.included_modules)

    if billing_tier_code and "BILLING_AUTOMATION" in addon_codes:
        if billing_tier_code not in BILLING_TIERS:
            raise ValueError(f"Unknown billing_tier_code: {billing_tier_code!r}")
        tier = BILLING_TIERS[billing_tier_code]
        if tier.mode != billing_mode_normalized:
            raise ValueError(
                f"billing_tier_code {billing_tier_code!r} is not valid for billing_mode {billing_mode_normalized!r}"
            )
        resolved.extend(_billing_modules_for_mode(billing_mode_normalized))
        if billing_mode_normalized == "FUSION_RCM":
            resolved.extend(["patient_statements", "lob_print_mail", "statement_ai"])

    operational_mode_normalized = str(operational_mode or "").strip().upper()
    agency_type_normalized = str(agency_type or "").strip().upper()
    if operational_mode_normalized == "HEMS_TRANSPORT":
        resolved.extend(["aviation_missions", "hems"])
    if operational_mode_normalized == "EXTERNAL_911_CAD":
        resolved.append("cad_module")
    if agency_type_normalized.startswith("FIRE"):
        resolved.append("fire_module")
    resolved.append("data_export")
    return _dedupe(resolved)


def lookup_key_to_cents(lookup_key: str) -> int:
    for plan in PLANS.values():
        if plan.lookup_key == lookup_key and plan.monthly_cents is not None:
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


def calculate_quote(
    plan_code: str,
    tier_code: str | None = None,
    billing_tier_code: str | None = None,
    addon_codes: list[str] | None = None,
    billing_mode: str | None = None,
) -> QuoteResult:
    if plan_code not in PLANS:
        raise ValueError(f"Unknown plan_code: {plan_code!r}")

    plan = PLANS[plan_code]
    addon_codes = list(addon_codes or [])
    billing_mode_normalized = _normalize_billing_mode(billing_mode)

    for addon_code in addon_codes:
        if addon_code not in ADDONS:
            raise ValueError(f"Unknown addon_code: {addon_code!r}")

    stripe_line_items: list[dict] = []

    if plan_code == "SCHEDULING_ONLY":
        if not tier_code:
            raise ValueError("tier_code is required for SCHEDULING_ONLY plan")
        if tier_code not in SCHEDULING_TIERS:
            raise ValueError(f"Unknown tier_code: {tier_code!r}")
        tier = SCHEDULING_TIERS[tier_code]
        base_monthly_cents = tier.monthly_cents
        stripe_line_items.append({"lookup_key": tier.lookup_key, "quantity": 1, "metered": False})
    else:
        if plan.monthly_cents is None or not plan.lookup_key:
            raise ValueError(f"Plan {plan_code!r} is missing pricing metadata")
        base_monthly_cents = plan.monthly_cents
        stripe_line_items.append({"lookup_key": plan.lookup_key, "quantity": 1, "metered": False})

    addon_monthly_cents = 0
    for addon_code in addon_codes:
        addon = ADDONS[addon_code]
        if addon.uses_billing_tier:
            if not billing_tier_code:
                raise ValueError(f"billing_tier_code is required for addon {addon_code!r}")
            if billing_tier_code not in BILLING_TIERS:
                raise ValueError(f"Unknown billing_tier_code: {billing_tier_code!r}")
            billing_tier = BILLING_TIERS[billing_tier_code]
            if billing_tier.mode != billing_mode_normalized:
                raise ValueError(
                    f"billing_tier_code {billing_tier_code!r} is not valid for billing_mode {billing_mode_normalized!r}"
                )
            addon_monthly_cents += billing_tier.base_monthly_cents
            stripe_line_items.append(
                {"lookup_key": billing_tier.base_lookup_key, "quantity": 1, "metered": False}
            )
            stripe_line_items.append({"lookup_key": billing_tier.per_claim_lookup_key, "metered": True})
            continue

        addon_monthly_cents += addon.monthly_cents
        if addon.lookup_key:
            stripe_line_items.append(
                {"lookup_key": addon.lookup_key, "quantity": 1, "metered": False}
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
        module_codes=resolve_selected_modules(
            plan_code=plan_code,
            addon_codes=addon_codes,
            billing_mode=billing_mode_normalized,
            billing_tier_code=billing_tier_code,
        ),
    )


def get_catalog() -> dict:
    def _fmt_cents(cents: int) -> str:
        dollars = cents / 100
        if dollars == int(dollars):
            return f"${int(dollars)}"
        return f"${dollars:.2f}"

    return {
        "plans": [
            {
                "code": plan.code,
                "label": plan.label,
                "desc": plan.desc,
                "contact_sales": plan.contact_sales,
                "color": plan.color,
                "price_display": (
                    f"from {_fmt_cents(min(t.monthly_cents for t in SCHEDULING_TIERS.values()))}/mo"
                    if plan.code == "SCHEDULING_ONLY"
                    else (f"{_fmt_cents(plan.monthly_cents or 0)}/mo" if plan.monthly_cents else "Contact us")
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
                "mode": tier.mode,
                "base_monthly_cents": tier.base_monthly_cents,
                "per_claim_cents": tier.per_claim_cents,
                "base_display": f"{_fmt_cents(tier.base_monthly_cents)}/mo",
                "per_claim_display": f"+{_fmt_cents(tier.per_claim_cents)}/claim",
                "compare_display": (
                    "Fixed-fee RCM beats typical 6–9% collections pricing for most EMS reimbursement profiles."
                    if tier.mode == "FUSION_RCM"
                    else "Keep your biller, avoid revenue skims, and pay a predictable export-first platform rate."
                ),
            }
            for tier in BILLING_TIERS.values()
        ],
        "addons": [
            {
                "code": addon.code,
                "label": addon.label,
                "desc": addon.desc,
                "monthly_cents": addon.monthly_cents,
                "gov_only": addon.gov_only,
                "uses_billing_tier": addon.uses_billing_tier,
                "included_modules": list(addon.included_modules),
                "price_display": (
                    "see billing tiers"
                    if addon.uses_billing_tier
                    else f"+{_fmt_cents(addon.monthly_cents)}/mo"
                ),
            }
            for addon in ADDONS.values()
        ],
        "billing_modes": [
            {
                "code": code,
                "label": mode["label"],
                "summary": mode["summary"],
            }
            for code, mode in BILLING_MODES.items()
        ],
    }

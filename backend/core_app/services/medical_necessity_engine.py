"""
Medical Necessity Engine for FusionEMS TransportLink.

Implements rule-based evaluation mirroring CMS Medicare Benefit Policy Manual
Chapter 10 criteria and Wisconsin ForwardHealth (Medicaid) transport coverage
criteria.

Rules encoded here are operational reference guidelines.  They do NOT constitute
legal or clinical advice.  EMS agencies and billing staff must verify compliance
with current payer-specific policies.
"""
from __future__ import annotations

# ruff: noqa: I001

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────


class MNStatus(StrEnum):
    """Medical necessity determination outcome codes."""

    MEDICAL_NECESSITY_SUPPORTED = "MEDICAL_NECESSITY_SUPPORTED"
    MEDICAL_NECESSITY_INSUFFICIENT = "MEDICAL_NECESSITY_INSUFFICIENT"
    LIKELY_NOT_MEDICALLY_NECESSARY = "LIKELY_NOT_MEDICALLY_NECESSARY"
    LEVEL_OF_CARE_NOT_SUPPORTED = "LEVEL_OF_CARE_NOT_SUPPORTED"
    ABN_REVIEW_REQUIRED = "ABN_REVIEW_REQUIRED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    WISCONSIN_MEDICAID_SUPPORT_PRESENT = "WISCONSIN_MEDICAID_SUPPORT_PRESENT"
    WISCONSIN_MEDICAID_SUPPORT_MISSING = "WISCONSIN_MEDICAID_SUPPORT_MISSING"


@dataclass
class MNFinding:
    rule_id: str
    description: str
    policy_reference: str
    passed: bool
    detail: str = ""


@dataclass
class MNResult:
    status: MNStatus
    explanation: str
    policy: str
    findings: list[MNFinding] = field(default_factory=list)
    abn_required: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Constant rule sets
# ─────────────────────────────────────────────────────────────────────────────

# CMS "weak" indications that alone are insufficient to support BLS/ALS transport
WEAK_ONLY_CONDITIONS: set[str] = {
    "dementia",
    "alzheimer",
    "fall_risk",
    "altered_mental_status",
    "ams",
    "confusion",
    "behavioral",
    "anxiety",
    "non_ambulatory_without_medical_need",
}

# Conditions that do support medical necessity when properly documented
STRONG_SUPPORTIVE_CONDITIONS: set[str] = {
    "cardiac_monitoring",
    "iv_therapy",
    "iv_infusion",
    "oxygen_therapy",
    "mechanical_ventilation",
    "vent_dependent",
    "airway_management",
    "spinal_precaution",
    "fracture_immobilization",
    "psychiatric_hold",
    "seizure_disorder",
    "stroke_protocol",
    "chest_pain",
    "respiratory_distress",
    "wound_care_requiring_supine",
    "immobilization",
    "contractures",
    "morbid_obesity",
    "combative",
    "dialysis_access_concerns",
    "post_surgical_monitoring",
    "pressure_injury",
}

# Wisconsin ForwardHealth specific supportive criteria
WI_MEDICAID_SUPPORTIVE: set[str] = {
    "supine_required",
    "continuous_cardiac_monitoring",
    "oxygen_therapy",
    "iv_infusion",
    "mechanical_ventilation",
    "vent_dependent",
    "post_surgical_supine",
    "wound_care_requiring_supine",
}

# Original Medicare payer identifiers (lowercase, substring match)
MEDICARE_ORIGINAL_IDENTIFIERS: tuple[str, ...] = (
    "original medicare",
    "medicare fee-for-service",
    "medicare ffs",
    "medicare part b",
    "traditional medicare",
    "medicare (not advantage)",
)

# Medicare Advantage / managed care — ABN does NOT apply
MEDICARE_ADVANTAGE_IDENTIFIERS: tuple[str, ...] = (
    "medicare advantage",
    "medicare+choice",
    "mapd",
    "part c",
    "humana medicare",
    "united healthcare medicare",
    "aetna medicare",
    "anthem medicare",
    "centene medicare",
    "molina medicare",
    "cigna medicare",
)

# Wisconsin Medicaid payer identifiers
WI_MEDICAID_IDENTIFIERS: tuple[str, ...] = (
    "forwardhealth",
    "forward health",
    "wi medicaid",
    "wisconsin medicaid",
    "badgercare",
    "badger care",
    "wi ffs medicaid",
)

# ALS service levels
ALS_LEVELS: set[str] = {"als", "als1", "als2", "als_emergency", "als1_emergency", "air", "hems"}

# BLS service levels
BLS_LEVELS: set[str] = {"bls", "bls_emergency", "bls_non_emergency", "wheelchair"}


# ─────────────────────────────────────────────────────────────────────────────
# Helper predicates
# ─────────────────────────────────────────────────────────────────────────────


def _is_original_medicare(payer: str) -> bool:
    p = payer.lower()
    if any(ident in p for ident in MEDICARE_ADVANTAGE_IDENTIFIERS):
        return False
    return any(ident in p for ident in MEDICARE_ORIGINAL_IDENTIFIERS)


def _is_medicare_advantage(payer: str) -> bool:
    p = payer.lower()
    return any(ident in p for ident in MEDICARE_ADVANTAGE_IDENTIFIERS)


def _is_wi_medicaid(payer: str) -> bool:
    p = payer.lower()
    return any(ident in p for ident in WI_MEDICAID_IDENTIFIERS)


def _extract_condition_keys(data: dict[str, Any]) -> set[str]:
    """Extract normalised condition/reason keys from request data."""
    conditions: set[str] = set()

    # Direct list fields
    for field_name in ("conditions", "diagnosis_codes", "medical_conditions", "mn_reasons"):
        val = data.get(field_name)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    conditions.add(item.lower().replace(" ", "_").replace("-", "_"))

    # Free-text clinical reason — look for known keywords
    for text_field in ("clinical_reason", "transport_reason", "mn_narrative", "clinical_notes"):
        text = data.get(text_field, "")
        if not isinstance(text, str):
            continue
        text_lower = text.lower()
        for kw in STRONG_SUPPORTIVE_CONDITIONS | WEAK_ONLY_CONDITIONS | WI_MEDICAID_SUPPORTIVE:
            if kw.replace("_", " ") in text_lower or kw in text_lower:
                conditions.add(kw)

    return conditions


# ─────────────────────────────────────────────────────────────────────────────
# Core evaluation
# ─────────────────────────────────────────────────────────────────────────────


def evaluate(data: dict[str, Any]) -> MNResult:
    """
    Evaluate medical necessity for a transport request.

    Args:
        data: The ``data`` JSONB payload from a ``facility_requests`` record.
              Expected keys (all optional but evaluated when present):
              - payer / payer_name: str
              - requested_service_level: str (BLS, ALS, ALS1, etc.)
              - conditions / mn_reasons: list[str]
              - clinical_reason / mn_narrative: str
              - mn_explanation: str  (why patient requires ambulance vs alternatives)
              - pcs_complete: bool
              - aob_complete: bool

    Returns:
        MNResult with status, explanation, policy reference, and per-rule findings.
    """
    findings: list[MNFinding] = []
    payer_raw: str = str(data.get("payer") or data.get("payer_name") or "")
    service_level: str = str(data.get("requested_service_level") or "").lower()
    mn_explanation: str = str(data.get("mn_explanation") or "").strip()
    pcs_complete: bool = bool(data.get("pcs_complete"))

    conditions = _extract_condition_keys(data)
    strong_present = conditions & STRONG_SUPPORTIVE_CONDITIONS
    weak_only = (conditions - STRONG_SUPPORTIVE_CONDITIONS) & WEAK_ONLY_CONDITIONS
    only_weak = bool(weak_only) and not strong_present

    orig_medicare = _is_original_medicare(payer_raw)
    wi_medicaid = _is_wi_medicaid(payer_raw)

    wi_strong = conditions & WI_MEDICAID_SUPPORTIVE

    # ── Rule 1: Service-level alignment ──────────────────────────────────────
    als_requested = service_level in ALS_LEVELS or "als" in service_level
    bls_requested = service_level in BLS_LEVELS or "bls" in service_level or "wheelchair" in service_level

    if als_requested and not strong_present:
        findings.append(MNFinding(
            rule_id="LOC-01",
            description="ALS level requested without strong clinical indication",
            policy_reference="CMS MBPM Ch. 10 §10.2.1",
            passed=False,
            detail=f"Service level: {service_level}; no ALS-qualifying condition found",
        ))
    elif als_requested and strong_present:
        findings.append(MNFinding(
            rule_id="LOC-01",
            description="ALS level supported by clinical documentation",
            policy_reference="CMS MBPM Ch. 10 §10.2.1",
            passed=True,
            detail=f"Supporting conditions: {', '.join(sorted(strong_present))}",
        ))

    if bls_requested and only_weak:
        findings.append(MNFinding(
            rule_id="LOC-02",
            description="BLS level — only weak indications documented",
            policy_reference="CMS MBPM Ch. 10 §10.2",
            passed=False,
            detail=f"Weak conditions only: {', '.join(sorted(weak_only))}",
        ))
    elif bls_requested and (strong_present or not weak_only):
        findings.append(MNFinding(
            rule_id="LOC-02",
            description="BLS level documentation",
            policy_reference="CMS MBPM Ch. 10 §10.2",
            passed=bool(strong_present),
        ))

    # ── Rule 2: Why ambulance was medically required (not alternatives) ───────
    explanation_present = len(mn_explanation) >= 20
    findings.append(MNFinding(
        rule_id="MN-01",
        description="Explanation of why ambulance transport is medically necessary",
        policy_reference="CMS MBPM Ch. 10 §10.1; ForwardHealth Transportation Manual §2.1",
        passed=explanation_present,
        detail=mn_explanation[:100] if explanation_present else "No explanation provided",
    ))

    # ── Rule 3: Physician Certification Statement ─────────────────────────────
    findings.append(MNFinding(
        rule_id="MN-02",
        description="PCS / Physician Certification Statement complete",
        policy_reference="CMS MBPM Ch. 10 §10.3; ForwardHealth Transportation Manual §3.2",
        passed=pcs_complete,
        detail="PCS complete" if pcs_complete else "PCS not marked complete",
    ))

    # ── Rule 4: Weak-only assessment ─────────────────────────────────────────
    if only_weak:
        findings.append(MNFinding(
            rule_id="MN-03",
            description="Documented conditions do not independently support medical necessity",
            policy_reference="CMS MBPM Ch. 10 §10.2; Palmetto JJ LCD L33393",
            passed=False,
            detail=f"Weak-only conditions: {', '.join(sorted(weak_only))}",
        ))
    elif strong_present:
        findings.append(MNFinding(
            rule_id="MN-03",
            description="Strong medical indication present",
            policy_reference="CMS MBPM Ch. 10 §10.2",
            passed=True,
            detail=f"Qualifying conditions: {', '.join(sorted(strong_present))}",
        ))

    # ── Rule 5: Wisconsin ForwardHealth specific ──────────────────────────────
    if wi_medicaid:
        wi_ok = bool(wi_strong)
        findings.append(MNFinding(
            rule_id="WI-01",
            description="Wisconsin ForwardHealth: supine, monitoring, O2, infusion, or vent requirement",
            policy_reference="ForwardHealth Transportation Manual §2.2 (Ambulance Services)",
            passed=wi_ok,
            detail=f"WI-qualifying criteria: {', '.join(sorted(wi_strong)) if wi_ok else 'none found'}",
        ))

    # ── Rule 6: ABN requirement for Original Medicare ─────────────────────────
    abn_required = orig_medicare and (only_weak or not strong_present or not explanation_present)

    # ─────────────────────────────────────────────────────────────────────────
    # Final determination
    # ─────────────────────────────────────────────────────────────────────────

    failed_rules = [f for f in findings if not f.passed]
    critical_fails = [f for f in failed_rules if f.rule_id.startswith("MN-") or f.rule_id.startswith("LOC-")]

    # Level-of-care mismatch (ALS requested, no ALS indicators)
    if als_requested and not strong_present:
        return MNResult(
            status=MNStatus.LEVEL_OF_CARE_NOT_SUPPORTED,
            explanation=(
                "ALS transport was requested, but no strong ALS-qualifying clinical indication "
                "was found in the documentation. Downgrade to BLS or provide additional "
                "clinical justification with specific ALS-level interventions required."
            ),
            policy="CMS MBPM Chapter 10 §10.2.1",
            findings=findings,
            abn_required=abn_required,
        )

    # Weak-only conditions
    if only_weak:
        if orig_medicare:
            return MNResult(
                status=MNStatus.ABN_REVIEW_REQUIRED,
                explanation=(
                    "The documented conditions ({}) may not independently satisfy CMS medical "
                    "necessity requirements for Original Medicare. An Advance Beneficiary Notice "
                    "(ABN) should be issued to the patient before transport. "
                    "Additional clinical documentation or payer pre-authorization is recommended."
                ).format(", ".join(sorted(weak_only))),
                policy="CMS MBPM Chapter 10 §10.2; 42 C.F.R. §411.406",
                findings=findings,
                abn_required=True,
            )
        return MNResult(
            status=MNStatus.LIKELY_NOT_MEDICALLY_NECESSARY,
            explanation=(
                "The only documented indications ({}) are generally insufficient to establish "
                "medical necessity on their own. Additional clinical justification must be "
                "provided explaining why the patient requires ambulance transport and cannot "
                "use a wheelchair van, stretcher car, or other non-ambulance transport."
            ).format(", ".join(sorted(weak_only))),
            policy="CMS MBPM Chapter 10 §10.2",
            findings=findings,
            abn_required=abn_required,
        )

    # Wisconsin Medicaid — strong present but no WI-specific criteria
    if wi_medicaid and not wi_strong and not only_weak:
        return MNResult(
            status=MNStatus.WISCONSIN_MEDICAID_SUPPORT_MISSING,
            explanation=(
                "Wisconsin ForwardHealth requires documentation of at least one of the following "
                "for ambulance transport coverage: patient must remain supine, continuous cardiac "
                "monitoring, oxygen therapy, IV infusion, or mechanical ventilation. None were "
                "found in the current documentation."
            ),
            policy="ForwardHealth Transportation Manual §2.2 (Ambulance Services)",
            findings=findings,
            abn_required=False,
        )

    if wi_medicaid and wi_strong:
        return MNResult(
            status=MNStatus.WISCONSIN_MEDICAID_SUPPORT_PRESENT,
            explanation=(
                "Wisconsin ForwardHealth ambulance transport criteria are present. "
                "Supporting criteria: {}."
            ).format(", ".join(sorted(wi_strong))),
            policy="ForwardHealth Transportation Manual §2.2",
            findings=findings,
            abn_required=False,
        )

    # Insufficient documentation (no strong conditions, no explanation)
    if critical_fails:
        if not explanation_present and not strong_present:
            return MNResult(
                status=MNStatus.MEDICAL_NECESSITY_INSUFFICIENT,
                explanation=(
                    "Medical necessity documentation is incomplete. Both a clinical explanation "
                    "of why ambulance transport is required (vs. alternative transport) and at "
                    "least one qualifying clinical condition must be documented."
                ),
                policy="CMS MBPM Chapter 10 §10.1–10.3",
                findings=findings,
                abn_required=abn_required,
            )
        if not explanation_present:
            return MNResult(
                status=MNStatus.MEDICAL_NECESSITY_INSUFFICIENT,
                explanation=(
                    "A qualifying clinical condition is present, but the documentation is missing "
                    "a required explanation of why the patient cannot use alternative transport "
                    "(wheelchair van, stretcher car, private vehicle, etc.)."
                ),
                policy="CMS MBPM Chapter 10 §10.1",
                findings=findings,
                abn_required=abn_required,
            )
        if not pcs_complete:
            # PCS alone is not a hard denial but flags for human review
            return MNResult(
                status=MNStatus.HUMAN_REVIEW_REQUIRED,
                explanation=(
                    "Clinical conditions and narrative are present, but the Physician Certification "
                    "Statement (PCS) has not been completed. The PCS is required for Medicare, "
                    "Medicaid, and most commercial payers. Obtain PCS before billing."
                ),
                policy="CMS MBPM Chapter 10 §10.3",
                findings=findings,
                abn_required=abn_required,
            )

    # All checks pass
    return MNResult(
        status=MNStatus.MEDICAL_NECESSITY_SUPPORTED,
        explanation=(
            "Medical necessity criteria are met. Supporting conditions: {}. "
            "Clinical explanation documented. {}{}".format(
                ", ".join(sorted(strong_present)) if strong_present else "documented",
                "PCS complete. " if pcs_complete else "PCS pending. ",
                "ABN not required." if not abn_required else "ABN review recommended.",
            )
        ),
        policy="CMS MBPM Chapter 10; ForwardHealth Transportation Manual",
        findings=findings,
        abn_required=abn_required,
    )

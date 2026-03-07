from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── CARC/RARC Denial Classification Taxonomy ──────────────────────────────────
# Maps Claim Adjustment Reason Codes to human-readable categories and actions.
# Source: X12 835 CARC standard + CMS ambulance billing guidance.

_CARC_TAXONOMY: dict[str, dict[str, str]] = {
    # Contractual Obligation (CO) — payer contractual adjustments
    "CO-4": {
        "category": "Modifier/Procedure Mismatch",
        "description": "Procedure code inconsistent with modifier or missing required modifier.",
        "action": "Review modifier usage. Attach documentation showing distinct services.",
    },
    "CO-16": {
        "category": "Missing Information",
        "description": "Claim/service lacks information or has submission errors.",
        "action": "Review 835 remark codes for specific missing data and resubmit.",
    },
    "CO-18": {
        "category": "Duplicate Claim",
        "description": "Exact duplicate claim/service.",
        "action": "Verify this is not a true duplicate. If different, submit appeal with documentation.",
    },
    "CO-29": {
        "category": "Timely Filing",
        "description": "Timely filing limit exceeded.",
        "action": "Check proof of timely filing. Appeal with submission receipt if applicable.",
    },
    "CO-45": {
        "category": "Charges Exceed Allowed",
        "description": "Charges exceed fee schedule or maximum allowable.",
        "action": "Write off excess per contract. No appeal unless fee schedule is incorrect.",
    },
    "CO-50": {
        "category": "Medical Necessity",
        "description": "Non-covered service — not deemed medically necessary.",
        "action": "Submit appeal with PCS form, physician certification, and medical necessity narrative.",
    },
    "CO-97": {
        "category": "Bundled Service",
        "description": "Payment included in allowance for another service/procedure.",
        "action": "Review bundling rules. Appeal with documentation if services are distinct.",
    },
    "CO-109": {
        "category": "Not Covered",
        "description": "Claim/service not covered by this payer/plan.",
        "action": "Verify payer and plan. If incorrect payer, resubmit to correct payer.",
    },
    "CO-167": {
        "category": "Diagnosis Mismatch",
        "description": "Diagnosis is not consistent with procedure.",
        "action": "Review ICD-10/HCPCS pairing. Correct and resubmit if coding error.",
    },
    "CO-197": {
        "category": "Authorization Required",
        "description": "Precertification/authorization/notification absent.",
        "action": "Obtain retroactive authorization if possible. Submit with prior auth number.",
    },
    "CO-204": {
        "category": "Service Not Rendered",
        "description": "Service/equipment/drug not furnished directly to patient.",
        "action": "Verify service delivery documentation. Correct claim if billing error.",
    },
    "CO-236": {
        "category": "Level of Service",
        "description": "Level of care/service not supported by documentation.",
        "action": "Submit supporting clinical documentation to justify level of service.",
    },
    # Patient Responsibility (PR) — patient owes
    "PR-1": {
        "category": "Deductible",
        "description": "Patient deductible amount.",
        "action": "Bill patient for deductible amount per EOB. No appeal needed.",
    },
    "PR-2": {
        "category": "Coinsurance",
        "description": "Patient coinsurance amount.",
        "action": "Bill patient for coinsurance amount per EOB. No appeal needed.",
    },
    "PR-3": {
        "category": "Copay",
        "description": "Patient copay amount.",
        "action": "Collect copay from patient. No appeal needed.",
    },
    "PR-96": {
        "category": "Non-Covered Charge",
        "description": "Non-covered charge(s) — patient responsibility.",
        "action": "Bill patient if ABN was signed. If no ABN, write off.",
    },
    # Other Adjustment (OA)
    "OA-23": {
        "category": "Coordination of Benefits",
        "description": "Payment adjusted due to other insurance payment.",
        "action": "Verify primary payer payment. Bill secondary if applicable.",
    },
}


def classify_denial(group_code: str, reason_code: str) -> dict[str, str]:
    """
    Classifies a CARC group+reason code into a human-readable category with recommended action.
    Returns structured classification for the founder dashboard and ClaimIssue pipeline.
    """
    key = f"{group_code}-{reason_code}"
    match = _CARC_TAXONOMY.get(key)
    if match:
        return {
            "code": key,
            "category": match["category"],
            "description": match["description"],
            "action": match["action"],
        }
    # Fallback: classify by group code
    group_labels = {
        "CO": "Contractual Obligation",
        "PR": "Patient Responsibility",
        "OA": "Other Adjustment",
        "PI": "Payer Initiated Reduction",
    }
    return {
        "code": key,
        "category": group_labels.get(group_code, "Unknown Adjustment"),
        "description": f"Adjustment reason code {reason_code} under group {group_code}.",
        "action": "Review the specific reason code in the CARC reference and determine appropriate follow-up.",
    }


@dataclass(frozen=True)
class EraDenial:
    claim_id: str
    group_code: str
    reason_code: str
    amount: float


def parse_835(x12_text: str) -> dict[str, Any]:
    """
    Minimal 835 parser: extracts CLP (claim payment info) and CAS (adjustments/denials)
    to populate `eras` and `denials`. Includes denial classification via CARC taxonomy.
    """
    segments = [s for s in x12_text.split("~") if s.strip()]
    current_claim_id: str | None = None
    denials: list[EraDenial] = []
    for seg in segments:
        parts = seg.split("*")
        tag = parts[0].strip()
        if tag == "CLP" and len(parts) > 2:
            current_claim_id = parts[1]
        if tag == "CAS" and current_claim_id and len(parts) >= 4:
            group = parts[1]
            reason = parts[2]
            try:
                amt = float(parts[3])
            except Exception:
                amt = 0.0
            denials.append(
                EraDenial(
                    claim_id=current_claim_id, group_code=group, reason_code=reason, amount=amt
                )
            )

    classified_denials = []
    for d in denials:
        entry = d.__dict__.copy()
        entry["classification"] = classify_denial(d.group_code, d.reason_code)
        classified_denials.append(entry)

    return {"denials": classified_denials}

from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class LegalPricingInput:
    request_type: str
    requester_category: str
    estimated_page_count: int
    print_mail_requested: bool
    rush_requested: bool
    jurisdiction_state: str


@dataclass(frozen=True)
class LegalPricingResult:
    currency: str
    total_due_cents: int
    agency_payout_cents: int
    platform_fee_cents: int
    margin_status: str
    payment_required: bool
    workflow_state: str
    delivery_mode: str
    line_items: list[dict[str, object]]
    costs: dict[str, int]
    hold_reasons: list[str]


_BASE_FEE_CENTS = {
    "patient": 0,
    "patient_representative": 0,
    "attorney": 2500,
    "insurance": 2000,
    "government_agency": 0,
    "employer": 2000,
    "other_third_party_manual_review": 0,
}

_PER_PAGE_CENTS = {
    "patient": 100,
    "patient_representative": 100,
    "attorney": 125,
    "insurance": 125,
    "government_agency": 100,
    "employer": 125,
    "other_third_party_manual_review": 125,
}


def _line_item(code: str, label: str, amount_cents: int, payee: str, note: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "code": code,
        "label": label,
        "amount_cents": amount_cents,
        "payee": payee,
    }
    if note:
        payload["note"] = note
    return payload


def compute_legal_quote(inputs: LegalPricingInput) -> LegalPricingResult:
    category = inputs.requester_category
    pages = max(0, int(inputs.estimated_page_count))
    jurisdiction = inputs.jurisdiction_state.upper()

    base_fee_cents = _BASE_FEE_CENTS.get(category, 0)
    page_fee_cents = _PER_PAGE_CENTS.get(category, _PER_PAGE_CENTS["other_third_party_manual_review"]) * pages
    certification_fee_cents = 1500 if inputs.request_type in {"subpoena", "court_order"} else 0
    rush_fee_cents = 2000 if inputs.rush_requested else 0

    delivery_mode = "print_and_mail" if inputs.print_mail_requested else "secure_digital"
    print_fixed_cents = 250 if inputs.print_mail_requested else 0
    print_page_cents = (15 * pages) if inputs.print_mail_requested else 0
    postage_cents = 120 if inputs.print_mail_requested else 0
    lob_cost_cents = print_fixed_cents + print_page_cents + postage_cents

    subtotal_cents = base_fee_cents + page_fee_cents + certification_fee_cents + rush_fee_cents

    platform_fee_floor_cents = 200
    platform_fee_pct_cents = ceil(subtotal_cents * 0.10)
    platform_fee_cents = max(platform_fee_floor_cents, platform_fee_pct_cents) if subtotal_cents > 0 else 0

    processor_fee_cents = ceil(subtotal_cents * 0.029) + (30 if subtotal_cents > 0 else 0)
    labor_cost_cents = 300 + (20 * pages)
    platform_margin_cents = platform_fee_cents - (processor_fee_cents + labor_cost_cents + lob_cost_cents)
    agency_payout_cents = max(subtotal_cents - platform_fee_cents, 0)

    hold_reasons: list[str] = []
    payment_required = subtotal_cents > 0

    if category == "other_third_party_manual_review":
        hold_reasons.append("Requester category requires manual approval before fulfillment.")

    if jurisdiction != "WI":
        hold_reasons.append("Non-Wisconsin jurisdiction requires legal policy review.")

    if payment_required:
        hold_reasons.append("Fulfillment remains on hold until required payment clears.")

    if platform_margin_cents < 0:
        margin_status = "at_risk_of_loss"
        hold_reasons.append("Estimated platform margin is negative; manual pricing override required.")
    elif platform_margin_cents < 200:
        margin_status = "low_margin"
    elif category == "other_third_party_manual_review":
        margin_status = "manual_review_required"
    else:
        margin_status = "profitable"

    if margin_status in {"at_risk_of_loss", "manual_review_required"}:
        workflow_state = "manual_approval_required"
    elif payment_required:
        workflow_state = "payment_required"
    else:
        workflow_state = "fee_calculated"

    if inputs.print_mail_requested and workflow_state == "fee_calculated":
        workflow_state = "ready_to_mail"

    line_items = [
        _line_item("base_processing_fee", "Base processing fee", base_fee_cents, "agency"),
        _line_item("record_page_fee", f"Record reproduction ({pages} pages)", page_fee_cents, "agency"),
        _line_item("certification_fee", "Certification / legal handling fee", certification_fee_cents, "agency"),
        _line_item("rush_service_fee", "Rush service surcharge", rush_fee_cents, "agency"),
    ]

    if inputs.print_mail_requested:
        line_items.extend(
            [
                _line_item("mail_processing_fee", "Print + mail handling", print_fixed_cents, "agency"),
                _line_item("mail_page_fee", f"Printed pages ({pages})", print_page_cents, "agency"),
                _line_item("postage_fee", "USPS postage estimate", postage_cents, "agency"),
            ]
        )

    line_items.append(
        _line_item(
            "platform_fee",
            "FusionEMS platform fee",
            platform_fee_cents,
            "platform",
            note="Automatically withheld from collected funds.",
        )
    )

    return LegalPricingResult(
        currency="usd",
        total_due_cents=subtotal_cents,
        agency_payout_cents=agency_payout_cents,
        platform_fee_cents=platform_fee_cents,
        margin_status=margin_status,
        payment_required=payment_required,
        workflow_state=workflow_state,
        delivery_mode=delivery_mode,
        line_items=line_items,
        costs={
            "estimated_processor_fee_cents": processor_fee_cents,
            "estimated_labor_cost_cents": labor_cost_cents,
            "estimated_lob_cost_cents": lob_cost_cents,
            "estimated_platform_margin_cents": platform_margin_cents,
        },
        hold_reasons=hold_reasons,
    )

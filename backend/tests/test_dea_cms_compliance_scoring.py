from __future__ import annotations

from core_app.api.cms_gate_router import _compute_cms_score
from core_app.api.dea_compliance_router import _dea_scorecard


def test_dea_scorecard_hard_blocks_with_open_discrepancy_and_unwitnessed_waste() -> None:
    result = _dea_scorecard(
        narc_counts=[{"data": {"created_at": "2026-03-08T00:00:00+00:00"}}],
        narc_waste_events=[{"data": {"wasted_at": "2026-03-08T00:00:00+00:00"}}],
        narc_discrepancies=[{"data": {"status": "open"}}],
        narc_seals=[{"data": {"scanned_at": "2026-03-08T00:00:00+00:00"}}],
        min_count_events=1,
    )

    assert result["hard_block"] is True
    assert result["passed"] is False
    assert result["metrics"]["open_discrepancies"] == 1
    assert result["metrics"]["unwitnessed_waste_events"] == 1
    assert len(result["required_actions"]) >= 2


def test_dea_scorecard_passes_when_all_controls_are_met() -> None:
    result = _dea_scorecard(
        narc_counts=[{"data": {"created_at": "2026-03-08T00:00:00+00:00"}}],
        narc_waste_events=[
            {
                "data": {
                    "wasted_at": "2026-03-08T00:00:00+00:00",
                    "witness_user_id": "witness-1",
                }
            }
        ],
        narc_discrepancies=[{"data": {"status": "resolved"}}],
        narc_seals=[{"data": {"scanned_at": "2026-03-08T00:00:00+00:00"}}],
        min_count_events=1,
    )

    assert result["hard_block"] is False
    assert result["passed"] is True
    assert result["score"] == 100
    assert result["required_actions"] == []


def test_cms_score_includes_name_field_for_gate_rows() -> None:
    result = _compute_cms_score(
        {
            "patient_condition": "Chest pain",
            "transport_reason": "Acute condition requiring monitored transport",
            "transport_level": "ALS",
            "origin_address": "123 Main St",
            "destination_name": "Regional Hospital",
            "pcs_on_file": True,
            "pcs_obtained": False,
            "medical_necessity_documented": True,
            "patient_signature": True,
            "signature_on_file": False,
            "primary_insurance_id": "A123",
            "medicare_id": "",
            "medicaid_id": "",
        }
    )

    assert result["gates"], "Expected at least one gate in CMS score output"
    for gate in result["gates"]:
        assert "name" in gate
        assert "gate" in gate

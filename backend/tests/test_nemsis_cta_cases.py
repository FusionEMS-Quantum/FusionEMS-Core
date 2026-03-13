from __future__ import annotations

from core_app.nemsis.cta_cases import get_cta_case


def test_vendor_case_metadata_stays_within_pre_block() -> None:
    case = get_cta_case("2025-DEM-1-FullSet_v351")

    assert case.expected_result == "PASS"
    assert "<table>" not in case.description
    assert "<table>" not in case.expected_result

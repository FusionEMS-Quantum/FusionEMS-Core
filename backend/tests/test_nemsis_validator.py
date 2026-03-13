from __future__ import annotations

from core_app.nemsis.validator import NEMSISValidator


def test_dem_dataset_skips_ems_specific_schematron_rules() -> None:
    xml_bytes = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<DEMDataSet xmlns="http://www.nemsis.org">'
        b"<DemographicReport><dAgency><dAgency.02>351-T0495</dAgency.02></dAgency></DemographicReport>"
        b"</DEMDataSet>"
    )

    result = NEMSISValidator().validate_xml_bytes(xml_bytes, state_code="FL")

    assert result.valid is True
    assert result.stage_results["xsd"]["passed"] is True
    assert result.stage_results["national_schematron"]["skipped"] is True
    assert result.issues == []

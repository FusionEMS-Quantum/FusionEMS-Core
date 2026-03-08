"""Tests for NEMSISExportService — XML generation, completeness validation."""
import pytest

from core_app.services.nemsis_service import NEMSISExportService


@pytest.fixture()
def service() -> NEMSISExportService:
    return NEMSISExportService()


# ── Completeness Validation ──────────────────────────────────────────────────


def test_validate_completeness_full_record(service: NEMSISExportService) -> None:
    record = {
        "pcr_number": "PCR-001",
        "agency_id": "AG-001",
        "complaint_reported": "Chest pain",
        "psap_call_dt": "2026-01-15T10:00:00Z",
        "unit_notified_dt": "2026-01-15T10:01:00Z",
        "enroute_dt": "2026-01-15T10:02:00Z",
        "arrived_scene_dt": "2026-01-15T10:08:00Z",
        "patient_gender": "M",
        "patient_age": "65",
        "primary_impression": "Acute coronary syndrome",
        "narrative": "Responded to 65yo male with chest pain...",
        "incident_disposition": "TRANSPORT",
        "vitals": [{"pulse": 88}],
    }
    result = service.validate_completeness(record)
    assert result["complete"] is True
    assert result["missing_fields"] == []
    assert result["completeness_pct"] == 100.0


def test_validate_completeness_missing_fields(service: NEMSISExportService) -> None:
    record = {"pcr_number": "PCR-002"}
    result = service.validate_completeness(record)
    assert result["complete"] is False
    assert len(result["missing_fields"]) > 0
    assert "agency_id" in result["missing_fields"]


# ── XML Generation ───────────────────────────────────────────────────────────


def test_build_epcr_xml_returns_bytes(service: NEMSISExportService) -> None:
    record = {
        "pcr_number": "PCR-003",
        "agency_id": "AG-001",
        "complaint_reported": "Fall",
        "incident_number": "INC-003",
        "incident_date": "2026-01-15",
        "psap_call_dt": "2026-01-15T10:00:00Z",
        "unit_notified_dt": "2026-01-15T10:01:00Z",
        "enroute_dt": "2026-01-15T10:02:00Z",
        "arrived_scene_dt": "2026-01-15T10:08:00Z",
        "patient_last_name": "Doe",
        "patient_first_name": "John",
        "patient_gender": "M",
        "patient_age": "45",
        "patient_dob": "1980-03-20",
        "primary_impression": "Hip fracture",
        "narrative": "Patient fell from standing height.",
        "incident_disposition": "TRANSPORT",
        "vitals": [
            {"time": "2026-01-15T10:10:00Z", "pulse": 88, "bp_systolic": 130, "bp_diastolic": 80},
        ],
        "destination_facility": "General Hospital",
    }
    xml = service.build_epcr_xml(record)
    assert isinstance(xml, bytes)
    assert b"EMSDataSet" in xml


def test_build_batch_xml(service: NEMSISExportService) -> None:
    records = [
        {"pcr_number": f"PCR-{i}", "agency_id": "AG-001"} for i in range(3)
    ]
    xml = service.build_batch_xml(records)
    assert isinstance(xml, bytes)
    assert b"EMSDataSet" in xml

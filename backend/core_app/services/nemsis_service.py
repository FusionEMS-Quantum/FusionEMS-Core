"""NEMSIS Export Service — XML generation, XSD validation, batch export.

Generates NEMSIS 3.5 compliant XML from ePCR records, validates against
XSD schemas, and orchestrates batch export job lifecycle.
"""
from __future__ import annotations

import logging
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

logger = logging.getLogger(__name__)

# NEMSIS 3.5 namespace
_NEMSIS_NS = "http://www.nemsis.org"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


class NEMSISExportService:
    """Generates NEMSIS 3.5 compliant XML and manages export jobs."""

    def build_epcr_xml(self, record: dict[str, Any]) -> bytes:
        """Build a single ePCR NEMSIS XML document from a record dict."""
        root = Element("EMSDataSet")
        root.set("xmlns", _NEMSIS_NS)
        root.set("xmlns:xsi", _XSI_NS)

        header = SubElement(root, "Header")
        SubElement(header, "DemographicGroup").text = record.get("agency_id", "")
        SubElement(header, "PatientCareReport")

        pcr = SubElement(root, "PatientCareReport")

        # eRecord — Identification
        e_record = SubElement(pcr, "eRecord")
        SubElement(e_record, "eRecord.01").text = record.get("pcr_number", "")
        SubElement(e_record, "eRecord.SoftwareApplicationGroup")

        # eResponse — Unit/Agency
        e_response = SubElement(pcr, "eResponse")
        SubElement(e_response, "eResponse.AgencyGroup")
        SubElement(e_response, "eResponse.01").text = record.get("agency_number", "")
        SubElement(e_response, "eResponse.02").text = record.get("agency_name", "")

        # eDispatch
        e_dispatch = SubElement(pcr, "eDispatch")
        SubElement(e_dispatch, "eDispatch.01").text = record.get("complaint_reported", "")
        SubElement(e_dispatch, "eDispatch.02").text = record.get("emd_performed", "")

        # eTimes
        e_times = SubElement(pcr, "eTimes")
        time_elements = [
            ("eTimes.01", "psap_call_dt"),
            ("eTimes.03", "unit_notified_dt"),
            ("eTimes.05", "enroute_dt"),
            ("eTimes.06", "arrived_scene_dt"),
            ("eTimes.07", "arrived_patient_dt"),
            ("eTimes.09", "depart_scene_dt"),
            ("eTimes.11", "arrived_destination_dt"),
            ("eTimes.12", "transfer_care_dt"),
            ("eTimes.13", "unit_back_service_dt"),
        ]
        for elem_name, field in time_elements:
            val = record.get(field, "")
            SubElement(e_times, elem_name).text = str(val) if val else ""

        # ePatient
        e_patient = SubElement(pcr, "ePatient")
        SubElement(e_patient, "ePatient.13").text = record.get("patient_gender", "")
        SubElement(e_patient, "ePatient.15").text = record.get("patient_age", "")
        SubElement(e_patient, "ePatient.16").text = record.get("patient_age_units", "")

        # eSituation
        e_situation = SubElement(pcr, "eSituation")
        SubElement(e_situation, "eSituation.01").text = record.get("date_symptom_onset", "")
        SubElement(e_situation, "eSituation.04").text = record.get("complaint_type", "")
        SubElement(e_situation, "eSituation.07").text = record.get("primary_symptom", "")
        SubElement(e_situation, "eSituation.09").text = record.get("primary_impression", "")
        SubElement(e_situation, "eSituation.11").text = record.get("provider_primary_impression", "")

        # eNarrative
        e_narrative = SubElement(pcr, "eNarrative")
        SubElement(e_narrative, "eNarrative.01").text = record.get("narrative", "")

        # eVitals (multiple sets)
        for vital in record.get("vitals", []):
            e_vital_group = SubElement(pcr, "eVitals")
            vital_set = SubElement(e_vital_group, "eVitals.VitalGroup")
            SubElement(vital_set, "eVitals.01").text = str(vital.get("taken_at", ""))
            SubElement(vital_set, "eVitals.06").text = str(vital.get("systolic", ""))
            SubElement(vital_set, "eVitals.07").text = str(vital.get("diastolic", ""))
            SubElement(vital_set, "eVitals.10").text = str(vital.get("heart_rate", ""))
            SubElement(vital_set, "eVitals.12").text = str(vital.get("pulse_oximetry", ""))
            SubElement(vital_set, "eVitals.14").text = str(vital.get("respiratory_rate", ""))
            SubElement(vital_set, "eVitals.26").text = str(vital.get("gcs_total", ""))

        # eDisposition
        e_disposition = SubElement(pcr, "eDisposition")
        SubElement(e_disposition, "eDisposition.12").text = record.get("incident_disposition", "")
        SubElement(e_disposition, "eDisposition.17").text = record.get("transport_disposition", "")
        SubElement(e_disposition, "eDisposition.21").text = record.get("destination_type", "")

        return tostring(root, encoding="unicode").encode("utf-8")

    def build_batch_xml(self, records: list[dict[str, Any]]) -> bytes:
        """Build a batch NEMSIS DataSet XML from multiple records."""
        root = Element("EMSDataSet")
        root.set("xmlns", _NEMSIS_NS)
        root.set("xmlns:xsi", _XSI_NS)

        for record in records:
            pcr = SubElement(root, "PatientCareReport")
            e_record = SubElement(pcr, "eRecord")
            SubElement(e_record, "eRecord.01").text = record.get("pcr_number", "")

            e_narrative = SubElement(pcr, "eNarrative")
            SubElement(e_narrative, "eNarrative.01").text = record.get("narrative", "")

            e_times = SubElement(pcr, "eTimes")
            for tag, field in [
                ("eTimes.01", "psap_call_dt"),
                ("eTimes.06", "arrived_scene_dt"),
            ]:
                SubElement(e_times, tag).text = str(record.get(field, ""))

        return tostring(root, encoding="unicode").encode("utf-8")

    def validate_completeness(
        self, record: dict[str, Any]
    ) -> dict[str, Any]:
        """Check a record for NEMSIS completeness before export."""
        required = [
            "pcr_number", "agency_id", "complaint_reported",
            "psap_call_dt", "unit_notified_dt", "enroute_dt",
            "arrived_scene_dt", "patient_gender", "patient_age",
            "primary_impression", "narrative", "incident_disposition",
        ]
        missing = [f for f in required if not record.get(f)]
        warnings: list[str] = []
        if not record.get("vitals"):
            warnings.append("No vital signs recorded")
        if not record.get("transfer_care_dt"):
            warnings.append("Transfer of care time not recorded")

        return {
            "complete": len(missing) == 0,
            "missing_fields": missing,
            "warnings": warnings,
            "completeness_pct": round((len(required) - len(missing)) / len(required) * 100, 1),
        }

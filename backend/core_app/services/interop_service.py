"""
Interoperability Service — FHIR-ready mapping and handoff exchange.

This service provides canonical data contracts, outbound handoff packet generation,
and external data provenance tracking. It does NOT assume any direct hospital
integration exists — it builds readiness first.
"""
import uuid
from typing import Any

from sqlalchemy.orm import Session

from core_app.models.governance import DataProvenance, HandoffExchangeRecord


class InteropService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Outbound FHIR–ready Mapping ──────────────────────────────────────

    def build_patient_fhir_resource(self, patient: Any) -> dict[str, Any]:
        """Map an internal Patient model to a FHIR-compliant Patient resource stub."""
        return {
            "resourceType": "Patient",
            "id": str(patient.id),
            "identifier": [
                {
                    "system": "urn:fusionems:patient",
                    "value": str(patient.id),
                }
            ],
            "name": [
                {
                    "use": "official",
                    "family": patient.last_name,
                    "given": [patient.first_name] + ([patient.middle_name] if patient.middle_name else []),
                }
            ],
            "gender": _map_gender(patient.gender.value if hasattr(patient.gender, "value") else str(patient.gender)),
            "birthDate": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        }

    def build_encounter_fhir_resource(self, incident: Any, patient_id: str | None = None) -> dict[str, Any]:
        """Map an internal Incident to a FHIR Encounter stub."""
        return {
            "resourceType": "Encounter",
            "id": str(incident.id),
            "identifier": [
                {
                    "system": "urn:fusionems:incident",
                    "value": incident.incident_number,
                }
            ],
            "status": _map_encounter_status(incident.status.value if hasattr(incident.status, "value") else str(incident.status)),
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "EMER",
                "display": "emergency",
            },
            "subject": {"reference": f"Patient/{patient_id}"} if patient_id else None,
            "period": {
                "start": incident.dispatch_time.isoformat() if incident.dispatch_time else None,
                "end": incident.arrival_time.isoformat() if incident.arrival_time else None,
            },
        }

    # ── Handoff Packet Generation ────────────────────────────────────────

    def create_handoff_packet(
        self,
        tenant_id: uuid.UUID,
        incident_id: uuid.UUID,
        destination_facility: str,
        exchange_type: str,
        payload_reference: str | None = None,
    ) -> HandoffExchangeRecord:
        record = HandoffExchangeRecord(
            tenant_id=tenant_id,
            incident_id=incident_id,
            destination_facility=destination_facility,
            exchange_type=exchange_type,
            status="CREATED",
            payload_reference=payload_reference,
        )
        self.db.add(record)
        self.db.flush()
        return record

    # ── Import Provenance Tracking ───────────────────────────────────────

    def record_import_provenance(
        self,
        tenant_id: uuid.UUID,
        entity_name: str,
        entity_id: uuid.UUID,
        source_system: str,
        external_id: str,
        raw_payload: dict[str, Any] | None = None,
    ) -> DataProvenance:
        """Track provenance of externally imported data. Prevents silent overwrites."""
        record = DataProvenance(
            tenant_id=tenant_id,
            entity_name=entity_name,
            entity_id=entity_id,
            source_system=source_system,
            external_id=external_id,
            raw_payload=raw_payload or {},
        )
        self.db.add(record)
        self.db.flush()
        return record


# ── Private Helpers ──────────────────────────────────────────────────────────

def _map_gender(gender: str) -> str:
    mapping = {
        "female": "female",
        "male": "male",
        "non_binary": "other",
        "other": "other",
        "unknown": "unknown",
    }
    return mapping.get(gender, "unknown")


def _map_encounter_status(status: str) -> str:
    mapping = {
        "draft": "planned",
        "in_progress": "in-progress",
        "ready_for_review": "in-progress",
        "completed": "finished",
        "locked": "finished",
    }
    return mapping.get(status, "unknown")

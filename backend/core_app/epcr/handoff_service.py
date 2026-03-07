from __future__ import annotations

import uuid
from datetime import UTC, datetime

from backend.core_app.epcr.chart_model import (
    Chart,
    ClinicalHandoffPacket,
    HandoffStatus,
)


class HandoffService:
    def generate_handoff(self, chart: Chart, recipient_facility: str) -> ClinicalHandoffPacket:
        """
        Generate a clinical handoff packet for the receiving facility.
        """
        age = chart.patient.age if chart.patient.age is not None else "??"
        summary = f"Patient: {chart.patient.first_name} {chart.patient.last_name} ({age}yo)\n"
        summary += f"Chief Complaint: {chart.assessments[0].chief_complaint if chart.assessments else 'None'}\n"
        if chart.vitals:
            last_v = chart.vitals[-1]
            summary += f"Last Vitals: BP {last_v.systolic_bp}/{last_v.diastolic_bp}, HR {last_v.heart_rate}, SpO2 {last_v.spo2}%\n"
        
        packet = ClinicalHandoffPacket(
            packet_id=str(uuid.uuid4()),
            chart_id=chart.chart_id,
            generated_at=datetime.now(UTC).isoformat(),
            recipient_facility=recipient_facility,
            content_summary=summary,
            delivery_status=HandoffStatus.HANDOFF_READY,
            delivery_method="electronic", 
        )
        
        chart.handoff_packet = packet
        # Persist packet
        
        return packet

    def send_handoff(self, packet: ClinicalHandoffPacket) -> bool:
        """
        Send the handoff packet via configured method (Fax, Direct, Email).
        """
        packet.delivery_status = HandoffStatus.HANDOFF_SENT
        # Logic to integrate with Fax/Direct messaging service
        return True

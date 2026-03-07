from __future__ import annotations

import uuid
from datetime import UTC, datetime

from backend.core_app.epcr.chart_model import (
    AINarrativeDraft,
    Chart,
    ClinicalContradictionFlag,
)


class AINarrativeGenerator:
    def generate_draft(self, chart: Chart, model_version: str = "gpt-4") -> AINarrativeDraft:
        """
        Generates a narrative draft based on the chart data.
        In a real implementation, this would call an LLM service.
        """
        # Placeholder logic
        age = chart.patient.age if chart.patient.age is not None else "??"
        narrative_text = f"Patient {age}yo {chart.patient.gender} complaint of {chart.assessments[0].chief_complaint if chart.assessments else 'unknown'}."
        
        draft = AINarrativeDraft(
            draft_id=str(uuid.uuid4()),
            chart_id=chart.chart_id,
            generated_at=datetime.now(UTC).isoformat(),
            model_version=model_version,
            narrative_text=narrative_text,
            confidence_score=0.85,
            is_accepted=False,
        )
        return draft

class ContradictionDetector:
    def detect_contradictions(self, chart: Chart) -> list[ClinicalContradictionFlag]:
        """
        Detects contradictions in the chart data using heuristic rules or AI.
        """
        flags: list[ClinicalContradictionFlag] = []
        
        # 1. Timeline Mismatch (Heuristic)
        if chart.dispatch.arrived_scene_time > chart.dispatch.departed_scene_time:
             flags.append(ClinicalContradictionFlag(
                 flag_id=str(uuid.uuid4()),
                 chart_id=chart.chart_id,
                 flag_type="TIMELINE_ERROR",
                 description="Departure time is before arrival time.",
                 severity="high",
                 flagged_by="AI_RULE",
                 resolved=False
             ))

        # 2. Vitals vs Condition (Heuristic)
        # e.g. "Patient is responsive" but GCS is 3
        # This would require more complex logic

        return flags

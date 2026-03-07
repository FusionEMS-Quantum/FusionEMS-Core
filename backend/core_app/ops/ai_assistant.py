"""
Operations AI Assistant — FusionEMS-Core
Explains operational issues in plain English for paramedic founders.

For every issue the AI answers:
- What is wrong
- Why it matters
- What to do next
- How serious it is
- Whether human review is needed
- What rule or system caused it

AI RULES:
- Never assume dispatch or technical knowledge
- Define acronyms
- Never give false certainty
- Distinguish hard fact from model judgment
- NEVER silently change critical operations state
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any


class IssueSeverity(str, Enum):
    BLOCKING = "BLOCKING"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class IssueSource(str, Enum):
    RULE = "RULE"
    AI_REVIEW = "AI_REVIEW"
    DISPATCH_EVENT = "DISPATCH_EVENT"
    TELEMETRY_EVENT = "TELEMETRY_EVENT"
    PAGING_EVENT = "PAGING_EVENT"
    HUMAN_NOTE = "HUMAN_NOTE"


class HumanReview(str, Enum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    SAFE_TO_AUTO_PROCESS = "SAFE_TO_AUTO_PROCESS"


class AIConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def _ops_issue(
    title: str,
    severity: IssueSeverity,
    source: IssueSource,
    what_is_wrong: str,
    why_it_matters: str,
    what_to_do: str,
    ops_context: str,
    human_review: HumanReview,
    confidence: AIConfidence,
    raw_data: dict | None = None,
) -> dict[str, Any]:
    """Format an ops AI issue in the standard PART 9 format."""
    return {
        "issue": title,
        "severity": severity.value,
        "source": source.value,
        "what_is_wrong": what_is_wrong,
        "why_it_matters": why_it_matters,
        "what_you_should_do": what_to_do,
        "operations_context": ops_context,
        "human_review": human_review.value,
        "confidence": confidence.value,
        "generated_at": datetime.now(UTC).isoformat(),
        "raw_data": raw_data or {},
    }


class OpsAIAssistant:
    """
    Operations AI assistant that explains issues in plain English.
    Does NOT modify state. Does NOT make silent decisions.
    Provides structured analysis for founder command center.
    """

    # ── Dispatch Issues ───────────────────────────────────────────────────────

    def explain_unassigned_mission(self, mission: dict) -> dict[str, Any]:
        """Explain why a mission is sitting unassigned."""
        data = mission.get("data") or {}
        state = data.get("state", "UNKNOWN")
        priority = data.get("priority", "UNKNOWN")
        complaint = data.get("chief_complaint", "not recorded")
        service_level = data.get("service_level", "UNKNOWN")

        age_minutes = None
        created_str = data.get("created_at")
        if created_str:
            try:
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                age_minutes = int((datetime.now(UTC) - created).total_seconds() / 60)
            except Exception:
                pass

        age_str = f"This call has been waiting {age_minutes} minute(s)." if age_minutes else ""

        severity = IssueSeverity.BLOCKING if priority in ("P1", "ECHO", "DELTA") else IssueSeverity.HIGH

        return _ops_issue(
            title=f"Unassigned {service_level} Mission — {priority}",
            severity=severity,
            source=IssueSource.DISPATCH_EVENT,
            what_is_wrong=(
                f"A {service_level} (service level: {service_level} = "
                f"{'Basic Life Support' if service_level == 'BLS' else 'Advanced Life Support' if service_level == 'ALS' else 'Critical Care Transport' if service_level == 'CCT' else service_level}) "
                f"call is in state {state} with no unit assigned. "
                f"Chief complaint: {complaint}. {age_str}"
            ),
            why_it_matters=(
                f"A {priority} priority call without a unit means no ambulance (EMS vehicle) "
                f"is responding. Every minute of delay can affect patient outcomes."
            ),
            what_to_do=(
                "1. Open the CAD board and review available units. "
                "2. Check unit readiness scores — assign the highest-scored available unit. "
                "3. Page the assigned crew immediately. "
                "4. If no qualified crew is available, trigger backup staffing protocol."
            ),
            ops_context=(
                f"CAD state machine: {state}. "
                f"The call must reach ASSIGNED → PAGE_SENT → ACCEPTED before a unit is responding. "
                f"Manual override is always available with an audit reason."
            ),
            human_review=HumanReview.REQUIRED,
            confidence=AIConfidence.HIGH,
            raw_data=data,
        )

    def explain_escalated_page(self, alert: dict) -> dict[str, Any]:
        """Explain an escalated CrewLink page."""
        data = alert.get("data") or {}
        mission_id = data.get("mission_id", "unknown")
        crew_count = len(data.get("target_crew_ids") or [])
        escalated_at = data.get("escalated_at", "unknown time")
        priority = data.get("priority", "UNKNOWN")

        return _ops_issue(
            title="CrewLink Page Escalated — No Crew Response",
            severity=IssueSeverity.BLOCKING,
            source=IssueSource.PAGING_EVENT,
            what_is_wrong=(
                f"A CrewLink page (mobile dispatch alert) was sent to {crew_count} crew member(s) "
                f"for mission {mission_id}, but no one accepted in time. "
                f"Escalated at {escalated_at}."
            ),
            why_it_matters=(
                "An escalated page means no crew has committed to responding. "
                "The call is effectively uncovered until a crew accepts or backup is paged."
            ),
            what_to_do=(
                "1. Check which crew members received the page and their current status. "
                "2. Call backup crew or on-call dispatcher. "
                "3. Use the CrewLink console to manually page backup crew. "
                "4. If no crew is available, notify your medical director per protocol."
            ),
            ops_context=(
                f"Priority: {priority}. CrewLink paging is strictly for operations — "
                "no billing messages are sent through this channel. "
                "Escalation timer fired automatically per agency rules."
            ),
            human_review=HumanReview.REQUIRED,
            confidence=AIConfidence.HIGH,
            raw_data=data,
        )

    def explain_staffing_gap(self, gap: dict) -> dict[str, Any]:
        """Explain a staffing readiness gap."""
        gap_type = gap.get("type", "UNKNOWN")
        message = gap.get("message", "Staffing issue detected")

        titles = {
            "CRITICAL_STAFFING_SHORTAGE": "Critical Staffing Shortage",
            "FATIGUE_FLAGS": "Crew Fatigue Flags Active",
            "ASSIGNMENT_CONFLICTS": "Crew Assignment Conflicts",
        }
        severities = {
            "CRITICAL_STAFFING_SHORTAGE": IssueSeverity.BLOCKING,
            "FATIGUE_FLAGS": IssueSeverity.HIGH,
            "ASSIGNMENT_CONFLICTS": IssueSeverity.HIGH,
        }

        title = titles.get(gap_type, "Staffing Issue")
        severity = severities.get(gap_type, IssueSeverity.MEDIUM)

        return _ops_issue(
            title=title,
            severity=severity,
            source=IssueSource.RULE,
            what_is_wrong=message,
            why_it_matters=(
                "If there is not enough qualified crew available, calls cannot be assigned. "
                "Fatigue-flagged crew must be reviewed before assignment — "
                "this is a patient safety rule, not a preference."
            ),
            what_to_do=(
                "1. Open Staffing Readiness in the Operations dashboard. "
                "2. Review crew availability and clear any conflicts. "
                "3. Contact on-call crew or mutual aid agency if critically short. "
                "4. Document all staffing decisions for compliance."
            ),
            ops_context=(
                "Staffing rules are deterministic — the system will NOT silently assign "
                "unqualified crew. Override is always available but requires an explicit reason "
                "that creates an audit record."
            ),
            human_review=HumanReview.REQUIRED,
            confidence=AIConfidence.HIGH,
            raw_data=gap,
        )

    def explain_fleet_alert(self, alert: dict) -> dict[str, Any]:
        """Explain a fleet telemetry alert."""
        data = alert.get("data") or {}
        unit_id = data.get("unit_id", "unknown unit")
        severity_raw = data.get("severity", "warning")
        message = data.get("message", "Fleet alert detected")
        fault_codes = data.get("fault_codes", [])

        severity_map = {
            "critical": IssueSeverity.BLOCKING,
            "warning": IssueSeverity.HIGH,
            "info": IssueSeverity.INFORMATIONAL,
        }
        severity = severity_map.get(severity_raw.lower(), IssueSeverity.MEDIUM)

        return _ops_issue(
            title=f"Fleet Alert — Unit {unit_id}",
            severity=severity,
            source=IssueSource.TELEMETRY_EVENT,
            what_is_wrong=(
                f"Unit {unit_id} has a fleet alert: {message}. "
                f"{'Fault codes: ' + ', '.join(fault_codes) + '.' if fault_codes else ''}"
            ),
            why_it_matters=(
                "A vehicle with an unresolved fleet alert may not be safe to dispatch. "
                "Critical alerts (engine, oil pressure, brakes) are immediate stop-use conditions."
            ),
            what_to_do=(
                f"1. Check unit {unit_id} in the Fleet dashboard for full telemetry details. "
                "2. If severity is CRITICAL — take unit out of service immediately. "
                "3. Create a maintenance work order in the Fleet module. "
                "4. Do NOT dispatch this unit until cleared by maintenance."
            ),
            ops_context=(
                "OBD-II (On-Board Diagnostics) data feeds this alert automatically. "
                "The readiness score for this unit has been reduced. "
                "The CAD dispatch engine will flag this unit as limited or unavailable."
            ),
            human_review=HumanReview.REQUIRED if severity == IssueSeverity.BLOCKING else HumanReview.RECOMMENDED,
            confidence=AIConfidence.HIGH,
            raw_data=data,
        )

    def explain_out_of_service_unit(self, unit: dict) -> dict[str, Any]:
        """Explain an out-of-service unit."""
        data = unit.get("data") or {}
        unit_name = data.get("unit_name", str(unit.get("id", "unknown")))
        reason = data.get("oos_reason", "No reason recorded")

        return _ops_issue(
            title=f"Unit Out of Service — {unit_name}",
            severity=IssueSeverity.HIGH,
            source=IssueSource.RULE,
            what_is_wrong=(
                f"Unit {unit_name} is marked OUT OF SERVICE. Reason: {reason}. "
                "This unit CANNOT be assigned to calls."
            ),
            why_it_matters=(
                "An out-of-service unit reduces your total available fleet. "
                "If this is your last available unit for a service level, "
                "you may be unable to respond to new calls."
            ),
            what_to_do=(
                f"1. Review the reason for unit {unit_name} being out of service. "
                "2. If it's a maintenance issue, check Fleet → Work Orders. "
                "3. If the issue is resolved, update unit status to AVAILABLE. "
                "4. Consider mutual aid if fleet is critically short."
            ),
            ops_context=(
                "Out-of-service status is enforced by the CAD system — "
                "this unit will not appear in dispatch recommendations. "
                "Restoring availability requires explicit status update with reason."
            ),
            human_review=HumanReview.RECOMMENDED,
            confidence=AIConfidence.HIGH,
            raw_data=data,
        )

    def explain_late_transport(self, mission: dict) -> dict[str, Any]:
        """Explain a mission that is taking longer than expected."""
        data = mission.get("data") or {}
        state = data.get("state", "UNKNOWN")
        service_level = data.get("service_level", "UNKNOWN")
        priority = data.get("priority", "UNKNOWN")

        return _ops_issue(
            title=f"Late Transport — {service_level} {priority}",
            severity=IssueSeverity.MEDIUM,
            source=IssueSource.DISPATCH_EVENT,
            what_is_wrong=(
                f"A {service_level} mission is in state {state} longer than expected. "
                "This may indicate a delay at scene, transport difficulty, or a documentation gap."
            ),
            why_it_matters=(
                "Extended transport times affect patient care, hospital coordination, "
                "and crew availability for the next call."
            ),
            what_to_do=(
                "1. Contact the crew via CrewLink or radio for status update. "
                "2. Verify the mission state in CAD reflects reality. "
                "3. Update state manually if crew is unable to do so. "
                "4. Notify receiving facility if ETA is delayed significantly."
            ),
            ops_context=(
                "This is an AI observation based on state duration — "
                "it does NOT automatically change the mission state. "
                "Human dispatcher review is required before any action."
            ),
            human_review=HumanReview.RECOMMENDED,
            confidence=AIConfidence.MEDIUM,
            raw_data=data,
        )

    # ── Top 3 Actions ─────────────────────────────────────────────────────────

    def generate_top_actions(self, ops_board: dict) -> list[dict[str, Any]]:
        """
        Generate the top 3 next actions for the founder ops command center.
        Prioritized by severity: BLOCKING first, then HIGH, then MEDIUM.
        """
        actions = []

        unassigned = ops_board.get("unassigned_missions") or []
        escalated = ops_board.get("escalated_pages") or []
        late_pages = ops_board.get("late_pages") or []

        for m in unassigned[:3]:
            mdata = m.get("data") or {}
            priority = mdata.get("priority", "P2")
            service_level = mdata.get("service_level", "BLS")
            actions.append({
                "priority": 1 if priority in ("P1", "ECHO", "DELTA") else 2,
                "color": "RED",
                "title": f"Assign Unit to {priority} {service_level} Call",
                "what": f"Mission {str(m['id'])[:8]} has no unit assigned.",
                "do_this": "Open CAD board → select recommended unit → page crew.",
                "severity": "BLOCKING",
            })

        for a in escalated[:2]:
            adata = a.get("data") or {}
            actions.append({
                "priority": 1,
                "color": "RED",
                "title": "Resolve Escalated CrewLink Page",
                "what": f"Page for mission {adata.get('mission_id', 'unknown')[:8]} has no crew response.",
                "do_this": "Open CrewLink → page backup crew or call dispatcher.",
                "severity": "BLOCKING",
            })

        for a in late_pages[:1]:
            adata = a.get("data") or {}
            actions.append({
                "priority": 2,
                "color": "ORANGE",
                "title": "Late Page — No Response",
                "what": f"Crew page for mission {adata.get('mission_id', 'unknown')[:8]} has no response.",
                "do_this": "Check crew status and contact directly if needed.",
                "severity": "HIGH",
            })

        # Sort by priority (1 = most urgent)
        actions.sort(key=lambda x: x["priority"])
        return actions[:3]

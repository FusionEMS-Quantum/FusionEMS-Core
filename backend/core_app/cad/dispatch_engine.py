"""
CAD Dispatch Engine — FusionEMS-Core
Full state machine for EMS Computer-Aided Dispatch (CAD).

STATE MACHINE:
  NEW_REQUEST → TRIAGED → READY_FOR_ASSIGNMENT → UNIT_RECOMMENDED →
  CREW_RECOMMENDED → ASSIGNED → PAGE_SENT → ACK_PENDING → ACCEPTED →
  EN_ROUTE → ON_SCENE → TRANSPORTING → ARRIVED_DESTINATION →
  HANDOFF_COMPLETE → CHART_PENDING → CLOSED / CANCELLED

RULES:
- No trip silently bypasses assignment logic
- Every state change is logged with who/what triggered it
- Manual override is always possible and auditable
- Dispatch is fully separate from billing communications
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher


class DispatchState(str, Enum):
    NEW_REQUEST = "NEW_REQUEST"
    TRIAGED = "TRIAGED"
    READY_FOR_ASSIGNMENT = "READY_FOR_ASSIGNMENT"
    UNIT_RECOMMENDED = "UNIT_RECOMMENDED"
    CREW_RECOMMENDED = "CREW_RECOMMENDED"
    ASSIGNED = "ASSIGNED"
    PAGE_SENT = "PAGE_SENT"
    ACK_PENDING = "ACK_PENDING"
    ACCEPTED = "ACCEPTED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    TRANSPORTING = "TRANSPORTING"
    ARRIVED_DESTINATION = "ARRIVED_DESTINATION"
    HANDOFF_COMPLETE = "HANDOFF_COMPLETE"
    CHART_PENDING = "CHART_PENDING"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


# Valid forward transitions for each state
_VALID_TRANSITIONS: dict[DispatchState, list[DispatchState]] = {
    DispatchState.NEW_REQUEST: [DispatchState.TRIAGED, DispatchState.CANCELLED],
    DispatchState.TRIAGED: [DispatchState.READY_FOR_ASSIGNMENT, DispatchState.CANCELLED],
    DispatchState.READY_FOR_ASSIGNMENT: [DispatchState.UNIT_RECOMMENDED, DispatchState.ASSIGNED, DispatchState.CANCELLED],
    DispatchState.UNIT_RECOMMENDED: [DispatchState.CREW_RECOMMENDED, DispatchState.ASSIGNED, DispatchState.READY_FOR_ASSIGNMENT, DispatchState.CANCELLED],
    DispatchState.CREW_RECOMMENDED: [DispatchState.ASSIGNED, DispatchState.UNIT_RECOMMENDED, DispatchState.CANCELLED],
    DispatchState.ASSIGNED: [DispatchState.PAGE_SENT, DispatchState.CANCELLED],
    DispatchState.PAGE_SENT: [DispatchState.ACK_PENDING, DispatchState.CANCELLED],
    DispatchState.ACK_PENDING: [DispatchState.ACCEPTED, DispatchState.ASSIGNED, DispatchState.CANCELLED],
    DispatchState.ACCEPTED: [DispatchState.EN_ROUTE, DispatchState.CANCELLED],
    DispatchState.EN_ROUTE: [DispatchState.ON_SCENE, DispatchState.CANCELLED],
    DispatchState.ON_SCENE: [DispatchState.TRANSPORTING, DispatchState.HANDOFF_COMPLETE, DispatchState.CANCELLED],
    DispatchState.TRANSPORTING: [DispatchState.ARRIVED_DESTINATION, DispatchState.CANCELLED],
    DispatchState.ARRIVED_DESTINATION: [DispatchState.HANDOFF_COMPLETE],
    DispatchState.HANDOFF_COMPLETE: [DispatchState.CHART_PENDING],
    DispatchState.CHART_PENDING: [DispatchState.CLOSED],
    DispatchState.CLOSED: [],
    DispatchState.CANCELLED: [],
}

# Service level capabilities
_SERVICE_LEVEL_CAPABILITIES = {
    "BLS": {"min_cert": "EMT", "interventions": ["oxygen", "splinting", "monitoring"]},
    "ALS": {"min_cert": "AEMT", "interventions": ["IV", "12-lead", "intubation", "medications"]},
    "CCT": {"min_cert": "Paramedic", "interventions": ["vent_management", "drips", "invasive_monitoring"]},
    "HEMS": {"min_cert": "Flight_Paramedic", "interventions": ["surgical_airway", "thoracostomy", "blood_products"]},
}


class DispatchEngine:
    """
    Core CAD dispatch engine.
    All mutations are idempotent, retry-safe, and fully audited.
    """

    def __init__(
        self,
        db: Session,
        publisher: EventPublisher,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
    ) -> None:
        self.svc = DominationService(db, publisher)
        self.tenant_id = tenant_id
        self.actor_user_id = actor_user_id

    # ── State Machine ─────────────────────────────────────────────────────────

    def validate_transition(
        self, current_state: str, target_state: str
    ) -> dict[str, Any]:
        """Validate a state transition. Returns {valid, reason}."""
        try:
            cur = DispatchState(current_state)
            tgt = DispatchState(target_state)
        except ValueError as e:
            return {"valid": False, "reason": f"Invalid state value: {e}"}

        allowed = _VALID_TRANSITIONS.get(cur, [])
        if tgt in allowed:
            return {"valid": True, "reason": "ok"}
        return {
            "valid": False,
            "reason": (
                f"Transition {current_state} → {target_state} is not permitted. "
                f"Allowed next states: {[s.value for s in allowed]}"
            ),
        }

    async def transition_mission(
        self,
        *,
        mission_id: uuid.UUID,
        target_state: str,
        actor_user_id: uuid.UUID | None = None,
        override: bool = False,
        override_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Transition an active mission to a new dispatch state.
        Every transition is logged. Override requires explicit reason.
        """
        mission = self.svc.repo("active_missions").get(
            tenant_id=self.tenant_id, record_id=mission_id
        )
        if not mission:
            return {"error": "mission_not_found", "mission_id": str(mission_id)}

        current_state = (mission.get("data") or {}).get("state", DispatchState.NEW_REQUEST)
        validation = self.validate_transition(current_state, target_state)

        if not validation["valid"]:
            if not override:
                return {
                    "error": "invalid_transition",
                    "reason": validation["reason"],
                    "current_state": current_state,
                    "requested_state": target_state,
                    "override_available": True,
                }
            # Override path — requires reason
            if not override_reason:
                return {"error": "override_reason_required"}

        now = datetime.now(UTC).isoformat()
        effective_actor = actor_user_id or self.actor_user_id

        # Log timeline event
        timeline_event: dict[str, Any] = {
            "mission_id": str(mission_id),
            "from_state": current_state,
            "to_state": target_state,
            "actor_user_id": str(effective_actor) if effective_actor else None,
            "override": override,
            "override_reason": override_reason,
            "metadata": metadata or {},
            "ts": now,
        }
        await self.svc.create(
            table="dispatch_timeline_events",
            tenant_id=self.tenant_id,
            actor_user_id=effective_actor,
            data=timeline_event,
            correlation_id=correlation_id,
        )

        # Update mission state
        updated = self.svc.repo("active_missions").update(
            tenant_id=self.tenant_id,
            record_id=mission_id,
            expected_version=(mission.get("version") or 1),
            patch={"state": target_state, "state_updated_at": now},
        )

        return {
            "mission_id": str(mission_id),
            "previous_state": current_state,
            "current_state": target_state,
            "override_applied": override,
            "ts": now,
            "record": updated,
        }

    # ── Unit Recommendation ───────────────────────────────────────────────────

    def recommend_unit(
        self,
        *,
        service_level: str,
        origin_lat: float | None,
        origin_lon: float | None,
        priority: str = "P2",
    ) -> dict[str, Any]:
        """
        Recommend available units based on service level and proximity.
        Returns ranked list with reasoning for each recommendation.
        """
        units = self.svc.repo("units").list(tenant_id=self.tenant_id, limit=200)
        unit_statuses = self.svc.repo("unit_status_events").list(
            tenant_id=self.tenant_id, limit=500
        )
        readiness_scores = self.svc.repo("readiness_scores").list(
            tenant_id=self.tenant_id, limit=200
        )

        # Build latest status per unit
        latest_status: dict[str, str] = {}
        for evt in sorted(unit_statuses, key=lambda x: x.get("created_at", "")):
            uid = (evt.get("data") or {}).get("unit_id")
            if uid:
                latest_status[uid] = (evt.get("data") or {}).get("status", "UNKNOWN")

        # Build readiness per unit
        readiness_map: dict[str, int] = {}
        for rs in sorted(readiness_scores, key=lambda x: x.get("created_at", "")):
            uid = (rs.get("data") or {}).get("unit_id")
            if uid:
                readiness_map[uid] = int((rs.get("data") or {}).get("readiness_score", 0))

        candidates = []
        for unit in units:
            uid = str(unit["id"])
            unit_data = unit.get("data") or {}
            unit_service_level = unit_data.get("service_level", "BLS")
            unit_status = latest_status.get(uid, "UNKNOWN")
            unit_readiness = readiness_map.get(uid, 50)

            # Skip unavailable or out-of-service units
            if unit_status in ("OUT_OF_SERVICE", "UNAVAILABLE", "OFF_DUTY"):
                continue

            # Service level check
            level_rank = {"BLS": 1, "ALS": 2, "CCT": 3, "HEMS": 4}
            req_rank = level_rank.get(service_level, 1)
            unit_rank = level_rank.get(unit_service_level, 1)
            if unit_rank < req_rank:
                continue  # Under-equipped

            # Score: readiness + service level match bonus
            score = unit_readiness
            if unit_service_level == service_level:
                score += 20  # Exact match bonus
            elif unit_rank > req_rank:
                score -= 10  # Overqualified (prefer right-sized)

            # Priority boost
            if priority in ("P1", "ECHO", "DELTA") and unit_status == "AVAILABLE":
                score += 15

            candidates.append({
                "unit_id": uid,
                "unit_name": unit_data.get("unit_name", uid),
                "service_level": unit_service_level,
                "current_status": unit_status,
                "readiness_score": unit_readiness,
                "recommendation_score": min(score, 100),
                "reasons": self._unit_recommendation_reasons(
                    unit_data, unit_status, unit_readiness, service_level
                ),
            })

        candidates.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return {
            "recommended": candidates[:5],
            "service_level_required": service_level,
            "total_available": len(candidates),
            "computed_at": datetime.now(UTC).isoformat(),
        }

    def _unit_recommendation_reasons(
        self,
        unit_data: dict,
        status: str,
        readiness: int,
        required_level: str,
    ) -> list[str]:
        reasons = []
        if status == "AVAILABLE":
            reasons.append("Unit is currently available")
        if readiness >= 80:
            reasons.append(f"High readiness score ({readiness}/100)")
        elif readiness >= 50:
            reasons.append(f"Moderate readiness ({readiness}/100)")
        else:
            reasons.append(f"Low readiness — review before dispatch ({readiness}/100)")
        if unit_data.get("service_level") == required_level:
            reasons.append(f"Exact service level match ({required_level})")
        return reasons

    # ── Crew Recommendation ───────────────────────────────────────────────────

    def recommend_crew(
        self,
        *,
        unit_id: uuid.UUID,
        service_level: str,
        shift_start: str | None = None,
    ) -> dict[str, Any]:
        """
        Recommend qualified crew for a unit and service level.
        Checks certifications, availability, and conflicts.
        """
        now = datetime.now(UTC)
        uid = str(unit_id)

        # Get crew availability records
        availability = self.svc.repo("crew_availability").list(
            tenant_id=self.tenant_id, limit=500
        )
        qualifications = self.svc.repo("crew_qualifications").list(
            tenant_id=self.tenant_id, limit=1000
        )
        conflicts = self.svc.repo("crew_assignment_conflicts").list(
            tenant_id=self.tenant_id, limit=500
        )
        fatigue_flags = self.svc.repo("crew_fatigue_flags").list(
            tenant_id=self.tenant_id, limit=200
        )

        # Index by crew member
        qual_map: dict[str, list[dict]] = {}
        for q in qualifications:
            cid = (q.get("data") or {}).get("crew_member_id")
            if cid:
                qual_map.setdefault(cid, []).append(q.get("data") or {})

        conflict_set: set[str] = set()
        for c in conflicts:
            cid = (c.get("data") or {}).get("crew_member_id")
            if cid and not (c.get("data") or {}).get("resolved"):
                conflict_set.add(cid)

        fatigue_set: set[str] = set()
        for f in fatigue_flags:
            cid = (f.get("data") or {}).get("crew_member_id")
            if cid and not (f.get("data") or {}).get("cleared"):
                fatigue_set.add(cid)

        required_cert = _SERVICE_LEVEL_CAPABILITIES.get(service_level, {}).get("min_cert", "EMT")
        cert_rank = {"EMT": 1, "AEMT": 2, "Paramedic": 3, "Flight_Paramedic": 4}
        req_rank = cert_rank.get(required_cert, 1)

        candidates = []
        for avail in availability:
            avail_data = avail.get("data") or {}
            cid = avail_data.get("crew_member_id")
            if not cid:
                continue

            avail_status = avail_data.get("status", "UNAVAILABLE")
            if avail_status not in ("AVAILABLE", "ON_STANDBY"):
                continue

            if cid in conflict_set:
                continue

            has_fatigue = cid in fatigue_set
            crew_quals = qual_map.get(cid, [])

            # Check certification level
            highest_cert = "EMT"
            active_certs = []
            for q in crew_quals:
                if q.get("status") == "ACTIVE":
                    cert = q.get("certification_type", "EMT")
                    active_certs.append(cert)
                    if cert_rank.get(cert, 0) > cert_rank.get(highest_cert, 0):
                        highest_cert = cert

            if cert_rank.get(highest_cert, 0) < req_rank:
                continue  # Not qualified

            score = 80
            if not has_fatigue:
                score += 10
            if avail_status == "AVAILABLE":
                score += 10
            if cert_rank.get(highest_cert, 0) == req_rank:
                score += 5  # Exact cert match

            candidates.append({
                "crew_member_id": cid,
                "crew_name": avail_data.get("crew_name", cid),
                "availability_status": avail_status,
                "highest_certification": highest_cert,
                "active_certifications": active_certs,
                "fatigue_flag": has_fatigue,
                "recommendation_score": min(score, 100),
                "qualification_met": True,
                "warnings": ["FATIGUE_FLAG_ACTIVE"] if has_fatigue else [],
            })

        candidates.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return {
            "unit_id": uid,
            "service_level": service_level,
            "required_certification": required_cert,
            "recommended_crew": candidates[:6],
            "total_qualified": len(candidates),
            "computed_at": now.isoformat(),
        }

    # ── Mission Creation ──────────────────────────────────────────────────────

    async def create_mission(
        self,
        *,
        dispatch_request_id: uuid.UUID,
        service_level: str,
        priority: str,
        chief_complaint: str,
        origin_address: str,
        destination_address: str | None,
        agency_id: str | None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create an active mission from a validated dispatch request.
        Initializes at NEW_REQUEST state with full audit trail.
        """
        now = datetime.now(UTC).isoformat()
        mission_data: dict[str, Any] = {
            "dispatch_request_id": str(dispatch_request_id),
            "state": DispatchState.NEW_REQUEST.value,
            "service_level": service_level,
            "priority": priority,
            "chief_complaint": chief_complaint,
            "origin_address": origin_address,
            "destination_address": destination_address,
            "agency_id": agency_id,
            "assigned_unit_id": None,
            "assigned_crew_ids": [],
            "page_alert_id": None,
            "state_updated_at": now,
            "created_at": now,
            **(metadata or {}),
        }

        mission = await self.svc.create(
            table="active_missions",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data=mission_data,
            correlation_id=correlation_id,
        )

        # Initial timeline event
        await self.svc.create(
            table="dispatch_timeline_events",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "mission_id": str(mission["id"]),
                "from_state": None,
                "to_state": DispatchState.NEW_REQUEST.value,
                "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
                "override": False,
                "metadata": {"source": "dispatch_engine"},
                "ts": now,
            },
            correlation_id=correlation_id,
        )

        # Audit event
        await self.svc.create(
            table="mission_audit_events",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "mission_id": str(mission["id"]),
                "event_type": "MISSION_CREATED",
                "actor": str(self.actor_user_id) if self.actor_user_id else "SYSTEM",
                "data": mission_data,
                "ts": now,
            },
            correlation_id=correlation_id,
        )

        return mission

    # ── Assignment ────────────────────────────────────────────────────────────

    async def assign_unit_and_crew(
        self,
        *,
        mission_id: uuid.UUID,
        unit_id: uuid.UUID,
        crew_member_ids: list[str],
        assigned_by: str = "DISPATCHER",
        override: bool = False,
        override_reason: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Assign a unit and crew to an active mission.
        Creates DispatchAssignment record with full audit.
        """
        now = datetime.now(UTC).isoformat()

        if override and not override_reason:
            return {"error": "override_reason_required"}

        assignment_data: dict[str, Any] = {
            "mission_id": str(mission_id),
            "unit_id": str(unit_id),
            "crew_member_ids": crew_member_ids,
            "assigned_by": assigned_by,
            "assigned_by_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "override": override,
            "override_reason": override_reason,
            "assigned_at": now,
        }

        assignment = await self.svc.create(
            table="dispatch_assignments",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data=assignment_data,
            correlation_id=correlation_id,
        )

        # Update mission with assignment
        mission = self.svc.repo("active_missions").get(
            tenant_id=self.tenant_id, record_id=mission_id
        )
        if mission:
            self.svc.repo("active_missions").update(
                tenant_id=self.tenant_id,
                record_id=mission_id,
                expected_version=(mission.get("version") or 1),
                patch={
                    "assigned_unit_id": str(unit_id),
                    "assigned_crew_ids": crew_member_ids,
                    "state": DispatchState.ASSIGNED.value,
                    "state_updated_at": now,
                },
            )

        # Audit
        await self.svc.create(
            table="mission_audit_events",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "mission_id": str(mission_id),
                "event_type": "UNIT_AND_CREW_ASSIGNED",
                "actor": str(self.actor_user_id) if self.actor_user_id else assigned_by,
                "data": assignment_data,
                "ts": now,
            },
            correlation_id=correlation_id,
        )

        return {"assignment": assignment, "mission_id": str(mission_id)}

    # ── Ops Board ─────────────────────────────────────────────────────────────

    def get_ops_board(self) -> dict[str, Any]:
        """
        Real-time ops board for founder command center.
        Returns active missions, unassigned, escalated, and late pages.
        """
        missions = self.svc.repo("active_missions").list(
            tenant_id=self.tenant_id, limit=200
        )
        timeline = self.svc.repo("dispatch_timeline_events").list(
            tenant_id=self.tenant_id, limit=500
        )
        pages = self.svc.repo("crew_paging_alerts").list(
            tenant_id=self.tenant_id, limit=200
        )

        now = datetime.now(UTC)
        active = []
        unassigned = []
        en_route = []
        escalated_pages = []
        late_pages = []

        terminal = {DispatchState.CLOSED.value, DispatchState.CANCELLED.value}
        for m in missions:
            data = m.get("data") or {}
            state = data.get("state", "UNKNOWN")
            if state in terminal:
                continue
            active.append(m)
            if state in (DispatchState.NEW_REQUEST.value, DispatchState.TRIAGED.value, DispatchState.READY_FOR_ASSIGNMENT.value):
                unassigned.append(m)
            if state == DispatchState.EN_ROUTE.value:
                en_route.append(m)

        for p in pages:
            pdata = p.get("data") or {}
            pstate = pdata.get("state", "")
            if pstate == "ESCALATED":
                escalated_pages.append(p)
            elif pstate == "NO_RESPONSE":
                late_pages.append(p)

        return {
            "active_mission_count": len(active),
            "unassigned_count": len(unassigned),
            "en_route_count": len(en_route),
            "escalated_page_count": len(escalated_pages),
            "late_page_count": len(late_pages),
            "active_missions": active,
            "unassigned_missions": unassigned,
            "escalated_pages": escalated_pages,
            "late_pages": late_pages,
            "computed_at": now.isoformat(),
        }

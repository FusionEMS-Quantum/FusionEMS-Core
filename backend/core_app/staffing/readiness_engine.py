"""
Staffing Readiness Engine — FusionEMS-Core
Crew qualification checks, availability, conflict detection,
fatigue awareness, and backup staffing logic.

RULES:
- No unit assigned to crew lacking required credentials
- No silent override of staffing conflicts
- AI may explain staffing risk but hard rules remain deterministic
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher


class CrewStaffingState(str, Enum):
    CREW_AVAILABLE = "CREW_AVAILABLE"
    CREW_ASSIGNED = "CREW_ASSIGNED"
    CREW_UNAVAILABLE = "CREW_UNAVAILABLE"
    CREW_CONFLICT = "CREW_CONFLICT"
    CREW_UNQUALIFIED = "CREW_UNQUALIFIED"
    CREW_FATIGUE_WARNING = "CREW_FATIGUE_WARNING"
    CREW_BACKUP_REQUIRED = "CREW_BACKUP_REQUIRED"


# Minimum certification per service level (deterministic — not overrideable without audit)
_CERT_REQUIREMENTS: dict[str, str] = {
    "BLS": "EMT",
    "ALS": "AEMT",
    "CCT": "Paramedic",
    "HEMS": "Flight_Paramedic",
}

_CERT_RANK: dict[str, int] = {
    "First_Responder": 0,
    "EMT": 1,
    "AEMT": 2,
    "Paramedic": 3,
    "Flight_Paramedic": 4,
    "Critical_Care_Paramedic": 4,
}


class StaffingReadinessEngine:
    """
    Staffing and qualification engine for EMS crew management.
    All hard rules are deterministic. Override requires explicit audit trail.
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

    # ── Qualification Check ───────────────────────────────────────────────────

    def check_crew_qualification(
        self,
        crew_member_id: str,
        service_level: str,
    ) -> dict[str, Any]:
        """
        Deterministic qualification check.
        Returns QUALIFIED / UNQUALIFIED with explicit reason.
        Cannot be overridden without logging.
        """
        required_cert = _CERT_REQUIREMENTS.get(service_level, "EMT")
        req_rank = _CERT_RANK.get(required_cert, 1)

        quals = self.svc.repo("crew_qualifications").list(
            tenant_id=self.tenant_id, limit=500
        )
        now = datetime.now(UTC)

        crew_certs = [
            q.get("data") or {}
            for q in quals
            if (q.get("data") or {}).get("crew_member_id") == crew_member_id
        ]

        active_certs = []
        expired_certs = []
        for q in crew_certs:
            cert_type = q.get("certification_type", "")
            expires_at_str = q.get("expires_at")
            status = q.get("status", "UNKNOWN")
            if status == "ACTIVE":
                if expires_at_str:
                    try:
                        exp = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                        if exp < now:
                            expired_certs.append(cert_type)
                            continue
                    except Exception:
                        pass
                active_certs.append(cert_type)
            elif status == "EXPIRED":
                expired_certs.append(cert_type)

        highest_active = max(
            (_CERT_RANK.get(c, 0) for c in active_certs),
            default=0,
        )
        highest_cert_name = next(
            (c for c, r in sorted(_CERT_RANK.items(), key=lambda x: -x[1]) if _CERT_RANK[c] == highest_active),
            None,
        )

        qualified = highest_active >= req_rank
        blocking_reasons = []
        warnings = []

        if not qualified:
            blocking_reasons.append(
                f"Crew requires {required_cert} or higher for {service_level}. "
                f"Highest active cert: {highest_cert_name or 'NONE'}."
            )
        if expired_certs:
            warnings.append(f"Expired certifications: {', '.join(expired_certs)}")

        return {
            "crew_member_id": crew_member_id,
            "service_level": service_level,
            "required_certification": required_cert,
            "highest_active_certification": highest_cert_name,
            "active_certifications": active_certs,
            "expired_certifications": expired_certs,
            "qualified": qualified,
            "state": CrewStaffingState.CREW_AVAILABLE.value if qualified else CrewStaffingState.CREW_UNQUALIFIED.value,
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
        }

    # ── Availability Check ────────────────────────────────────────────────────

    def check_crew_availability(
        self,
        crew_member_id: str,
    ) -> dict[str, Any]:
        """Check crew member current availability and any active conflicts."""
        avail_records = self.svc.repo("crew_availability").list(
            tenant_id=self.tenant_id, limit=500
        )
        conflict_records = self.svc.repo("crew_assignment_conflicts").list(
            tenant_id=self.tenant_id, limit=200
        )
        fatigue_records = self.svc.repo("crew_fatigue_flags").list(
            tenant_id=self.tenant_id, limit=100
        )

        # Find latest availability record
        crew_avail = [
            r for r in avail_records
            if (r.get("data") or {}).get("crew_member_id") == crew_member_id
        ]
        crew_avail.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
        latest_avail = crew_avail[0] if crew_avail else None
        avail_status = (latest_avail.get("data") or {}).get("status", "UNKNOWN") if latest_avail else "UNKNOWN"

        # Check conflicts
        active_conflicts = [
            r for r in conflict_records
            if (r.get("data") or {}).get("crew_member_id") == crew_member_id
            and not (r.get("data") or {}).get("resolved")
        ]

        # Check fatigue
        active_fatigue = [
            r for r in fatigue_records
            if (r.get("data") or {}).get("crew_member_id") == crew_member_id
            and not (r.get("data") or {}).get("cleared")
        ]

        state = CrewStaffingState.CREW_AVAILABLE.value
        warnings = []
        blocking_reasons = []

        if avail_status in ("UNAVAILABLE", "OFF_DUTY", "SICK"):
            state = CrewStaffingState.CREW_UNAVAILABLE.value
            blocking_reasons.append(f"Crew status is {avail_status}")
        if active_conflicts:
            state = CrewStaffingState.CREW_CONFLICT.value
            blocking_reasons.append(f"{len(active_conflicts)} active assignment conflict(s)")
        if active_fatigue:
            if state == CrewStaffingState.CREW_AVAILABLE.value:
                state = CrewStaffingState.CREW_FATIGUE_WARNING.value
            warnings.append("Fatigue flag active — review before assignment")

        return {
            "crew_member_id": crew_member_id,
            "availability_status": avail_status,
            "state": state,
            "active_conflicts": len(active_conflicts),
            "fatigue_flag": len(active_fatigue) > 0,
            "available": state == CrewStaffingState.CREW_AVAILABLE.value,
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
        }

    # ── Conflict Detection ────────────────────────────────────────────────────

    async def detect_assignment_conflict(
        self,
        *,
        crew_member_id: str,
        proposed_mission_id: str,
        proposed_unit_id: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Detect if a crew assignment creates a conflict.
        Checks existing assignments for double-booking.
        """
        now = datetime.now(UTC).isoformat()
        existing = self.svc.repo("dispatch_assignments").list(
            tenant_id=self.tenant_id, limit=500
        )

        active_missions = self.svc.repo("active_missions").list(
            tenant_id=self.tenant_id, limit=200
        )
        active_mission_ids = set()
        terminal = {"CLOSED", "CANCELLED", "CHART_PENDING", "HANDOFF_COMPLETE"}
        for m in active_missions:
            if (m.get("data") or {}).get("state") not in terminal:
                active_mission_ids.add(str(m["id"]))

        conflicts = []
        for a in existing:
            adata = a.get("data") or {}
            if crew_member_id in (adata.get("crew_member_ids") or []):
                existing_mission_id = adata.get("mission_id")
                if existing_mission_id in active_mission_ids and existing_mission_id != proposed_mission_id:
                    conflicts.append({
                        "conflicting_mission_id": existing_mission_id,
                        "conflicting_unit_id": adata.get("unit_id"),
                    })

        if conflicts:
            conflict_record = await self.svc.create(
                table="crew_assignment_conflicts",
                tenant_id=self.tenant_id,
                actor_user_id=self.actor_user_id,
                data={
                    "crew_member_id": crew_member_id,
                    "proposed_mission_id": proposed_mission_id,
                    "proposed_unit_id": proposed_unit_id,
                    "conflicting_assignments": conflicts,
                    "detected_at": now,
                    "resolved": False,
                },
                correlation_id=correlation_id,
            )
            await self._audit(
                event_type="ASSIGNMENT_CONFLICT_DETECTED",
                data={
                    "crew_member_id": crew_member_id,
                    "conflict_count": len(conflicts),
                    "conflicts": conflicts,
                },
                correlation_id=correlation_id,
            )
            return {
                "conflict_detected": True,
                "conflict_count": len(conflicts),
                "conflicts": conflicts,
                "conflict_record_id": str(conflict_record["id"]),
                "action_required": "RESOLVE_BEFORE_ASSIGNMENT",
            }

        return {"conflict_detected": False}

    # ── Staffing Readiness Summary ────────────────────────────────────────────

    def staffing_readiness_summary(self) -> dict[str, Any]:
        """
        Agency-wide staffing readiness snapshot.
        Returns counts by state, gaps, and qualified crew per service level.
        """
        avail_records = self.svc.repo("crew_availability").list(
            tenant_id=self.tenant_id, limit=500
        )
        qualifications = self.svc.repo("crew_qualifications").list(
            tenant_id=self.tenant_id, limit=1000
        )
        fatigue_flags = self.svc.repo("crew_fatigue_flags").list(
            tenant_id=self.tenant_id, limit=200
        )
        conflicts = self.svc.repo("crew_assignment_conflicts").list(
            tenant_id=self.tenant_id, limit=200
        )

        now = datetime.now(UTC)
        total = len(avail_records)
        available = 0
        assigned = 0
        unavailable = 0
        fatigue_count = 0
        conflict_count = 0

        active_fatigue_ids: set[str] = set()
        for f in fatigue_flags:
            if not (f.get("data") or {}).get("cleared"):
                cid = (f.get("data") or {}).get("crew_member_id")
                if cid:
                    active_fatigue_ids.add(cid)

        active_conflict_ids: set[str] = set()
        for c in conflicts:
            if not (c.get("data") or {}).get("resolved"):
                cid = (c.get("data") or {}).get("crew_member_id")
                if cid:
                    active_conflict_ids.add(cid)

        for r in avail_records:
            status = (r.get("data") or {}).get("status", "UNKNOWN")
            if status == "AVAILABLE":
                available += 1
            elif status == "ASSIGNED":
                assigned += 1
            else:
                unavailable += 1

        fatigue_count = len(active_fatigue_ids)
        conflict_count = len(active_conflict_ids)

        # Qualified crew per service level
        qual_by_level: dict[str, int] = {"BLS": 0, "ALS": 0, "CCT": 0, "HEMS": 0}
        qual_map: dict[str, int] = {}
        for q in qualifications:
            qdata = q.get("data") or {}
            if qdata.get("status") == "ACTIVE":
                cid = qdata.get("crew_member_id")
                cert = qdata.get("certification_type", "EMT")
                rank = _CERT_RANK.get(cert, 0)
                if cid:
                    qual_map[cid] = max(qual_map.get(cid, 0), rank)

        for rank in qual_map.values():
            if rank >= _CERT_RANK.get("EMT", 1):
                qual_by_level["BLS"] += 1
            if rank >= _CERT_RANK.get("AEMT", 2):
                qual_by_level["ALS"] += 1
            if rank >= _CERT_RANK.get("Paramedic", 3):
                qual_by_level["CCT"] += 1
            if rank >= _CERT_RANK.get("Flight_Paramedic", 4):
                qual_by_level["HEMS"] += 1

        gaps = []
        if available < 2:
            gaps.append({"type": "CRITICAL_STAFFING_SHORTAGE", "message": f"Only {available} crew available"})
        if fatigue_count > 0:
            gaps.append({"type": "FATIGUE_FLAGS", "message": f"{fatigue_count} crew have active fatigue flags"})
        if conflict_count > 0:
            gaps.append({"type": "ASSIGNMENT_CONFLICTS", "message": f"{conflict_count} crew have unresolved conflicts"})

        return {
            "total_crew": total,
            "available": available,
            "assigned": assigned,
            "unavailable": unavailable,
            "fatigue_flags": fatigue_count,
            "active_conflicts": conflict_count,
            "qualified_by_service_level": qual_by_level,
            "staffing_gaps": gaps,
            "overall_readiness": "CRITICAL" if available < 2 else "WARNING" if gaps else "READY",
            "computed_at": now.isoformat(),
        }

    # ── Fatigue Flag ──────────────────────────────────────────────────────────

    async def flag_fatigue(
        self,
        *,
        crew_member_id: str,
        reason: str,
        hours_on_duty: float | None = None,
        flagged_by: str = "SYSTEM",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Flag a crew member for fatigue review. Cannot be silently cleared."""
        now = datetime.now(UTC).isoformat()
        flag = await self.svc.create(
            table="crew_fatigue_flags",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "crew_member_id": crew_member_id,
                "reason": reason,
                "hours_on_duty": hours_on_duty,
                "flagged_by": flagged_by,
                "flagged_at": now,
                "cleared": False,
                "cleared_by": None,
                "cleared_at": None,
            },
            correlation_id=correlation_id,
        )
        await self._audit(
            event_type="FATIGUE_FLAG_SET",
            data={"crew_member_id": crew_member_id, "reason": reason, "flagged_by": flagged_by},
            correlation_id=correlation_id,
        )
        return {"flag_id": str(flag["id"]), "crew_member_id": crew_member_id, "status": "FLAGGED"}

    # ── Audit ─────────────────────────────────────────────────────────────────

    async def _audit(
        self,
        event_type: str,
        data: dict[str, Any],
        correlation_id: str | None,
    ) -> None:
        await self.svc.create(
            table="staffing_audit_events",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "event_type": event_type,
                "data": data,
                "actor_user_id": str(self.actor_user_id) if self.actor_user_id else "SYSTEM",
                "ts": datetime.now(UTC).isoformat(),
                "correlation_id": correlation_id,
            },
            correlation_id=correlation_id,
        )

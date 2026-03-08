"""CAD Service — call lifecycle, unit management, dispatch recommendations.

Provides typed service operations for CAD calls, unit assignment,
timeline tracking, and integration with the DispatchEngine.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.cad import (
    CADCall,
    CADCallState,
    CADTimelineEvent,
    CADUnit,
    CADUnitAssignment,
    CADUnitState,
    CADUnitStatusEvent,
)

logger = logging.getLogger(__name__)


class CADService:
    """Manages CAD call lifecycle, unit tracking, and dispatch assignments."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── CALL LIFECYCLE ────────────────────────────────────────────────────

    async def create_call(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        data: dict[str, Any],
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        call = CADCall(
            tenant_id=tenant_id,
            call_number=data.get("call_number"),
            state=CADCallState.NEW.value,
            priority=data.get("priority"),
            caller_name=data.get("caller_name"),
            caller_phone=data.get("caller_phone"),
            address=data.get("location_address") or data.get("address"),
            latitude=data.get("location_lat") or data.get("latitude"),
            longitude=data.get("location_lng") or data.get("longitude"),
            chief_complaint=data.get("chief_complaint"),
            triage_notes=data.get("triage_notes"),
            intake_answers=data.get("intake_answers"),
            call_received_at=datetime.now(UTC),
        )
        self.db.add(call)
        await self._add_timeline(
            tenant_id=tenant_id,
            call_id=call.id,
            event_type="CALL_CREATED",
            description="Call created",
            actor_id=actor_user_id,
        )
        await self.db.commit()
        await self.db.refresh(call)
        logger.info(
            "cad_call_created",
            extra={
                "tenant_id": str(tenant_id),
                "call_id": str(call.id),
                "correlation_id": correlation_id,
            },
        )
        return {"id": str(call.id), "call_number": call.call_number, "state": call.state}

    async def get_call(
        self, *, tenant_id: uuid.UUID, call_id: uuid.UUID
    ) -> CADCall:
        stmt = select(CADCall).where(
            CADCall.tenant_id == tenant_id,
            CADCall.id == call_id,
        )
        result = await self.db.execute(stmt)
        call = result.scalar_one_or_none()
        if call is None:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                status_code=404,
                message="CAD call not found",
            )
        return call

    async def transition_call(
        self,
        *,
        tenant_id: uuid.UUID,
        call_id: uuid.UUID,
        new_state: str,
        actor_user_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        call = await self.get_call(tenant_id=tenant_id, call_id=call_id)
        old_state = call.state
        call.state = new_state
        now = datetime.now(UTC)

        # Set lifecycle timestamps based on state transition
        timestamp_map: dict[str, str] = {
            CADCallState.DISPATCHED.value: "dispatched_at",
            CADCallState.ENROUTE.value: "enroute_at",
            CADCallState.ON_SCENE.value: "on_scene_at",
            CADCallState.TRANSPORTING.value: "transporting_at",
            CADCallState.AT_HOSPITAL.value: "at_hospital_at",
            CADCallState.CLEARED.value: "cleared_at",
        }
        ts_field = timestamp_map.get(new_state)
        if ts_field and getattr(call, ts_field, None) is None:
            setattr(call, ts_field, now)

        await self._add_timeline(
            tenant_id=tenant_id,
            call_id=call_id,
            event_type="STATE_TRANSITION",
            description=f"{old_state} → {new_state}",
            actor_id=actor_user_id,
            metadata_blob={"old_state": old_state, "new_state": new_state},
        )
        await self.db.commit()
        logger.info(
            "cad_call_transitioned",
            extra={
                "tenant_id": str(tenant_id),
                "call_id": str(call_id),
                "old_state": old_state,
                "new_state": new_state,
                "correlation_id": correlation_id,
            },
        )
        return {"call_id": str(call_id), "old_state": old_state, "new_state": new_state}

    async def list_active_calls(
        self, *, tenant_id: uuid.UUID, limit: int = 200
    ) -> list[CADCall]:
        active_states = [
            CADCallState.NEW.value,
            CADCallState.DISPATCHED.value,
            CADCallState.ENROUTE.value,
            CADCallState.ON_SCENE.value,
            CADCallState.TRANSPORTING.value,
            CADCallState.AT_HOSPITAL.value,
        ]
        stmt = (
            select(CADCall)
            .where(
                CADCall.tenant_id == tenant_id,
                CADCall.state.in_(active_states),
            )
            .order_by(CADCall.call_received_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── UNIT MANAGEMENT ───────────────────────────────────────────────────

    async def register_unit(
        self,
        *,
        tenant_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        unit = CADUnit(
            tenant_id=tenant_id,
            unit_name=data["unit_name"],
            unit_type=data.get("unit_type"),
            service_level=data.get("service_level", "BLS"),
            state=CADUnitState.AVAILABLE.value,
            station=data.get("station"),
            latitude=data.get("lat") or data.get("latitude"),
            longitude=data.get("lng") or data.get("longitude"),
            crew_ids=data.get("crew_ids"),
            capabilities=data.get("capabilities"),
        )
        self.db.add(unit)
        await self.db.commit()
        await self.db.refresh(unit)
        return {"id": str(unit.id), "unit_name": unit.unit_name}

    async def update_unit_status(
        self,
        *,
        tenant_id: uuid.UUID,
        unit_id: uuid.UUID,
        new_state: str,
        actor_user_id: uuid.UUID,
        reason: str | None = None,
    ) -> dict[str, Any]:
        stmt = select(CADUnit).where(
            CADUnit.tenant_id == tenant_id,
            CADUnit.id == unit_id,
        )
        result = await self.db.execute(stmt)
        unit = result.scalar_one_or_none()
        if unit is None:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                status_code=404,
                message="CAD unit not found",
            )
        old_state = unit.state
        unit.state = new_state

        event = CADUnitStatusEvent(
            tenant_id=tenant_id,
            unit_id=unit_id,
            old_state=old_state,
            new_state=new_state,
            reason=reason,
            actor_id=actor_user_id,
        )
        self.db.add(event)
        await self.db.commit()
        return {"unit_id": str(unit_id), "old_state": old_state, "new_state": new_state}

    async def update_unit_gps(
        self,
        *,
        tenant_id: uuid.UUID,
        unit_id: uuid.UUID,
        lat: float,
        lng: float,
    ) -> None:
        stmt = (
            update(CADUnit)
            .where(CADUnit.tenant_id == tenant_id, CADUnit.id == unit_id)
            .values(latitude=lat, longitude=lng, last_gps_update=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def list_units(
        self, *, tenant_id: uuid.UUID, active_only: bool = True
    ) -> list[CADUnit]:
        stmt = select(CADUnit).where(CADUnit.tenant_id == tenant_id)
        if active_only:
            stmt = stmt.where(CADUnit.active.is_(True))
        stmt = stmt.order_by(CADUnit.unit_name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── UNIT ASSIGNMENT ───────────────────────────────────────────────────

    async def assign_unit_to_call(
        self,
        *,
        tenant_id: uuid.UUID,
        call_id: uuid.UUID,
        unit_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        primary: bool = True,
    ) -> dict[str, Any]:
        assignment = CADUnitAssignment(
            tenant_id=tenant_id,
            call_id=call_id,
            unit_id=unit_id,
            primary=primary,
            assigned_at=datetime.now(UTC),
        )
        self.db.add(assignment)
        await self._add_timeline(
            tenant_id=tenant_id,
            call_id=call_id,
            event_type="UNIT_ASSIGNED",
            description=f"Unit {unit_id} assigned",
            actor_id=actor_user_id,
            unit_id=unit_id,
        )
        # Transition unit to DISPATCHED
        await self.update_unit_status(
            tenant_id=tenant_id,
            unit_id=unit_id,
            new_state=CADUnitState.DISPATCHED.value,
            actor_user_id=actor_user_id,
            reason=f"Assigned to call {call_id}",
        )
        return {"assignment_id": str(assignment.id)}

    # ── TIMELINE ──────────────────────────────────────────────────────────

    async def _add_timeline(
        self,
        *,
        tenant_id: uuid.UUID,  # noqa: ARG002 — kept for call-site compatibility
        call_id: uuid.UUID,
        event_type: str,
        description: str,
        actor_id: uuid.UUID | None = None,
        unit_id: uuid.UUID | None = None,
        metadata_blob: dict[str, Any] | None = None,
    ) -> None:
        event = CADTimelineEvent(
            call_id=call_id,
            event_type=event_type,
            description=description,
            actor_id=actor_id,
            unit_id=unit_id,
            metadata_blob=metadata_blob,
        )
        self.db.add(event)

    async def get_call_timeline(
        self, *, tenant_id: uuid.UUID, call_id: uuid.UUID
    ) -> list[CADTimelineEvent]:
        stmt = (
            select(CADTimelineEvent)
            .where(
                CADTimelineEvent.call_id == call_id,
            )
            .order_by(CADTimelineEvent.occurred_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

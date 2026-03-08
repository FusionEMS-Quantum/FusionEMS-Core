"""Scheduling Service — shifts, swaps, coverage, credentials, fatigue.

Handles scheduling domain operations including shift template/instance management,
swap requests with approval workflow, coverage validation, credential tracking,
and NFPA fatigue assessment.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.scheduling import (
    AvailabilityBlock,
    CoverageRule,
    CrewCredential,
    FatigueAssessment,
    ShiftInstance,
    ShiftSwapRequest,
    ShiftSwapState,
    ShiftTemplate,
    TimeOffRequest,
)

logger = logging.getLogger(__name__)

# NFPA 1584 thresholds
_FATIGUE_MAX_24H = 16.0
_FATIGUE_MAX_7D = 60.0
_FATIGUE_HIGH_CALLS_PER_SHIFT = 12


class SchedulingService:
    """Manages scheduling operations including shifts, swaps, coverage, and fatigue."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── SHIFT TEMPLATES ───────────────────────────────────────────────────

    async def create_template(
        self,
        *,
        tenant_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        tpl = ShiftTemplate(
            tenant_id=tenant_id,
            name=data["name"],
            pattern_type=data.get("pattern_type", "fixed"),
            shift_hours=int(data.get("shift_hours", 24)),
            off_hours=int(data.get("off_hours", 48)),
            rotation_days=data.get("rotation_days"),
            start_time=data.get("start_time", "07:00"),
            min_crew=int(data.get("min_crew", 2)),
            required_roles=data.get("required_roles"),
        )
        self.db.add(tpl)
        await self.db.commit()
        await self.db.refresh(tpl)
        return {"id": str(tpl.id), "name": tpl.name}

    async def list_templates(
        self, *, tenant_id: uuid.UUID
    ) -> list[ShiftTemplate]:
        stmt = (
            select(ShiftTemplate)
            .where(ShiftTemplate.tenant_id == tenant_id, ShiftTemplate.active.is_(True))
            .order_by(ShiftTemplate.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── SHIFT INSTANCES ───────────────────────────────────────────────────

    async def create_instance(
        self,
        *,
        tenant_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        inst = ShiftInstance(
            tenant_id=tenant_id,
            template_id=uuid.UUID(data["template_id"]) if data.get("template_id") else None,
            user_id=uuid.UUID(data["user_id"]),
            unit_id=uuid.UUID(data["unit_id"]) if data.get("unit_id") else None,
            station=data.get("station"),
            role=data.get("role"),
            start_dt=data["start_dt"],
            end_dt=data["end_dt"],
            overtime=data.get("overtime", False),
            notes=data.get("notes"),
        )
        self.db.add(inst)
        await self.db.commit()
        await self.db.refresh(inst)
        return {"id": str(inst.id)}

    async def list_instances(
        self,
        *,
        tenant_id: uuid.UUID,
        start_after: datetime | None = None,
        end_before: datetime | None = None,
        user_id: uuid.UUID | None = None,
        limit: int = 500,
    ) -> list[ShiftInstance]:
        stmt = select(ShiftInstance).where(ShiftInstance.tenant_id == tenant_id)
        if start_after:
            stmt = stmt.where(ShiftInstance.start_dt >= start_after)
        if end_before:
            stmt = stmt.where(ShiftInstance.end_dt <= end_before)
        if user_id:
            stmt = stmt.where(ShiftInstance.user_id == user_id)
        stmt = stmt.order_by(ShiftInstance.start_dt).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── SWAP REQUESTS ─────────────────────────────────────────────────────

    async def request_swap(
        self,
        *,
        tenant_id: uuid.UUID,
        requester_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        swap = ShiftSwapRequest(
            tenant_id=tenant_id,
            requester_id=requester_id,
            requester_shift_id=uuid.UUID(data["requester_shift_id"]),
            acceptor_id=uuid.UUID(data["acceptor_id"]) if data.get("acceptor_id") else None,
            acceptor_shift_id=uuid.UUID(data["acceptor_shift_id"]) if data.get("acceptor_shift_id") else None,
            state=ShiftSwapState.REQUESTED.value,
            reason=data.get("reason"),
        )
        self.db.add(swap)
        await self.db.commit()
        await self.db.refresh(swap)
        logger.info(
            "shift_swap_requested",
            extra={"tenant_id": str(tenant_id), "swap_id": str(swap.id)},
        )
        return {"id": str(swap.id), "state": swap.state}

    async def approve_swap(
        self,
        *,
        tenant_id: uuid.UUID,
        swap_id: uuid.UUID,
        approver_id: uuid.UUID,
    ) -> dict[str, Any]:
        stmt = select(ShiftSwapRequest).where(
            ShiftSwapRequest.tenant_id == tenant_id,
            ShiftSwapRequest.id == swap_id,
        )
        result = await self.db.execute(stmt)
        swap = result.scalar_one_or_none()
        if swap is None:
            raise AppError(code=ErrorCodes.NOT_FOUND, status_code=404, message="Swap request not found")
        if swap.state != ShiftSwapState.REQUESTED.value:
            raise AppError(code=ErrorCodes.CONFLICT, status_code=409, message="Swap not in REQUESTED state")

        swap.state = ShiftSwapState.APPROVED.value
        swap.approver_id = approver_id
        swap.approved_at = datetime.now(UTC)

        # Actually swap the shift instances if both exist
        if swap.requester_shift_id and swap.acceptor_shift_id and swap.acceptor_id:
            req_shift = await self.db.get(ShiftInstance, swap.requester_shift_id)
            acc_shift = await self.db.get(ShiftInstance, swap.acceptor_shift_id)
            if req_shift and acc_shift:
                req_shift.user_id, acc_shift.user_id = acc_shift.user_id, req_shift.user_id

        await self.db.commit()
        return {"id": str(swap.id), "state": swap.state}

    async def deny_swap(
        self,
        *,
        tenant_id: uuid.UUID,
        swap_id: uuid.UUID,
        approver_id: uuid.UUID,
        reason: str,
    ) -> dict[str, Any]:
        stmt = select(ShiftSwapRequest).where(
            ShiftSwapRequest.tenant_id == tenant_id,
            ShiftSwapRequest.id == swap_id,
        )
        result = await self.db.execute(stmt)
        swap = result.scalar_one_or_none()
        if swap is None:
            raise AppError(code=ErrorCodes.NOT_FOUND, status_code=404, message="Swap request not found")

        swap.state = ShiftSwapState.DENIED.value
        swap.approver_id = approver_id
        swap.denied_reason = reason
        await self.db.commit()
        return {"id": str(swap.id), "state": swap.state}

    async def list_swaps(
        self, *, tenant_id: uuid.UUID, state: str | None = None
    ) -> list[ShiftSwapRequest]:
        stmt = select(ShiftSwapRequest).where(ShiftSwapRequest.tenant_id == tenant_id)
        if state:
            stmt = stmt.where(ShiftSwapRequest.state == state)
        stmt = stmt.order_by(ShiftSwapRequest.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── AVAILABILITY ──────────────────────────────────────────────────────

    async def set_availability(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        block = AvailabilityBlock(
            tenant_id=tenant_id,
            user_id=user_id,
            available=data.get("available", True),
            start_dt=data["start_dt"],
            end_dt=data["end_dt"],
            reason=data.get("reason"),
        )
        self.db.add(block)
        await self.db.commit()
        await self.db.refresh(block)
        return {"id": str(block.id)}

    # ── TIME OFF ──────────────────────────────────────────────────────────

    async def request_time_off(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        req = TimeOffRequest(
            tenant_id=tenant_id,
            user_id=user_id,
            start_date=data["start_date"],
            end_date=data["end_date"],
            category=data.get("category", "PTO"),
            notes=data.get("notes"),
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)
        return {"id": str(req.id), "status": req.status}

    async def approve_time_off(
        self,
        *,
        tenant_id: uuid.UUID,
        request_id: uuid.UUID,
        approver_id: uuid.UUID,
    ) -> dict[str, Any]:
        stmt = select(TimeOffRequest).where(
            TimeOffRequest.tenant_id == tenant_id,
            TimeOffRequest.id == request_id,
        )
        result = await self.db.execute(stmt)
        req = result.scalar_one_or_none()
        if req is None:
            raise AppError(code=ErrorCodes.NOT_FOUND, status_code=404, message="Time-off request not found")
        req.status = "APPROVED"
        req.approver_id = approver_id
        await self.db.commit()
        return {"id": str(req.id), "status": req.status}

    # ── CREDENTIALS ───────────────────────────────────────────────────────

    async def add_credential(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        cred = CrewCredential(
            tenant_id=tenant_id,
            user_id=user_id,
            credential_type=data["credential_type"],
            credential_number=data.get("credential_number"),
            issuing_authority=data.get("issuing_authority"),
            issued_date=data.get("issued_date"),
            expiry_date=data.get("expiry_date"),
            document_s3_key=data.get("document_s3_key"),
        )
        self.db.add(cred)
        await self.db.commit()
        await self.db.refresh(cred)
        return {"id": str(cred.id)}

    async def list_expiring_credentials(
        self, *, tenant_id: uuid.UUID, within_days: int = 30
    ) -> list[CrewCredential]:
        cutoff = datetime.now(UTC) + timedelta(days=within_days)
        stmt = (
            select(CrewCredential)
            .where(
                CrewCredential.tenant_id == tenant_id,
                CrewCredential.expiry_date <= cutoff,
                CrewCredential.expiry_date >= datetime.now(UTC),
            )
            .order_by(CrewCredential.expiry_date)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── FATIGUE / NFPA ────────────────────────────────────────────────────

    async def record_fatigue_assessment(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        hours_on = float(data.get("hours_on_duty", 0))
        hours_awake = float(data.get("hours_since_last_sleep", 0))
        calls = int(data.get("calls_this_shift", 0))

        risk = "LOW"
        fit = True
        if hours_on >= _FATIGUE_MAX_24H or hours_awake >= 24:
            risk = "HIGH"
            fit = False
        elif hours_on >= 12 or calls >= _FATIGUE_HIGH_CALLS_PER_SHIFT:
            risk = "MODERATE"

        assessment = FatigueAssessment(
            tenant_id=tenant_id,
            user_id=user_id,
            kss_score=data.get("kss_score"),
            hours_on_duty=hours_on,
            hours_since_last_sleep=hours_awake,
            calls_this_shift=calls,
            fatigue_risk_level=risk,
            assessment_notes=data.get("assessment_notes"),
            fit_for_duty=fit,
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        return {
            "id": str(assessment.id),
            "fatigue_risk_level": risk,
            "fit_for_duty": fit,
        }

    # ── COVERAGE RULES ────────────────────────────────────────────────────

    async def create_coverage_rule(
        self,
        *,
        tenant_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        rule = CoverageRule(
            tenant_id=tenant_id,
            name=data["name"],
            station=data.get("station"),
            unit_type=data.get("unit_type"),
            min_personnel=int(data.get("min_personnel", 2)),
            required_roles=data.get("required_roles"),
            effective_from=data.get("effective_from"),
            effective_to=data.get("effective_to"),
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return {"id": str(rule.id), "name": rule.name}

    async def check_coverage(
        self,
        *,
        tenant_id: uuid.UUID,
        target_dt: datetime,
    ) -> dict[str, Any]:
        """Check staffing coverage against rules for a given datetime."""
        rules_stmt = select(CoverageRule).where(
            CoverageRule.tenant_id == tenant_id,
            CoverageRule.active.is_(True),
        )
        rules_result = await self.db.execute(rules_stmt)
        rules = list(rules_result.scalars().all())

        shifts_stmt = select(ShiftInstance).where(
            ShiftInstance.tenant_id == tenant_id,
            ShiftInstance.start_dt <= target_dt,
            ShiftInstance.end_dt >= target_dt,
        )
        shifts_result = await self.db.execute(shifts_stmt)
        shifts = list(shifts_result.scalars().all())

        violations: list[dict[str, Any]] = []
        for rule in rules:
            matching_shifts = [
                s for s in shifts
                if (rule.station is None or s.station == rule.station)
                and (rule.unit_type is None or getattr(s, "unit_type", None) == rule.unit_type)
            ]
            if len(matching_shifts) < rule.min_personnel:
                violations.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "station": rule.station,
                    "required": rule.min_personnel,
                    "assigned": len(matching_shifts),
                    "shortfall": rule.min_personnel - len(matching_shifts),
                })

        return {
            "target_dt": target_dt.isoformat(),
            "rules_checked": len(rules),
            "violations": violations,
            "compliant": len(violations) == 0,
        }

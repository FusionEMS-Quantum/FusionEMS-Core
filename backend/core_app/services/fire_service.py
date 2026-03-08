"""Fire / NERIS Service — incident management, NERIS validation, export orchestration.

Handles Fire domain operations including NERIS 5.0 compliant field validation,
batch export job creation, and preplan/hydrant/inspection management.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.fire import (
    FireApparatusRecord,
    FireHydrant,
    FireIncident,
    FireInspection,
    FirePersonnelAssignment,
    FirePreplan,
    NERISExportJob,
    NERISExportState,
)

logger = logging.getLogger(__name__)

# ── NERIS 5.0 Required Fields per Section ────────────────────────────────────

_SECTION_A_REQUIRED = {
    "neris_incident_type_code",
    "incident_date",
    "alarm_date",
    "arrival_date",
    "street_address",
    "city",
    "state",
    "zip_code",
}

_SECTION_B_REQUIRED = {
    "property_use_code",
}

_SECTION_C_REQUIRED = {
    "area_of_origin_code",
    "heat_source_code",
    "item_first_ignited_code",
}


class FireService:
    """Manages Fire incident lifecycle, NERIS validation, and export orchestration."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── INCIDENT CRUD ─────────────────────────────────────────────────────

    async def create_incident(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        data: dict[str, Any],
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        inc = FireIncident(
            tenant_id=tenant_id,
            incident_number=data.get("incident_number"),
            incident_type=data.get("incident_type", "FIRE"),
            neris_incident_type_code=data.get("neris_incident_type_code"),
            incident_date=data.get("incident_date"),
            alarm_date=data.get("alarm_date"),
            arrival_date=data.get("arrival_date"),
            controlled_date=data.get("controlled_date"),
            last_unit_cleared_date=data.get("last_unit_cleared_date"),
            street_address=data.get("street_address"),
            city=data.get("city"),
            state=data.get("state"),
            zip_code=data.get("zip_code"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            property_use_code=data.get("property_use_code"),
            area_of_origin_code=data.get("area_of_origin_code"),
            heat_source_code=data.get("heat_source_code"),
            item_first_ignited_code=data.get("item_first_ignited_code"),
            cause_of_ignition_code=data.get("cause_of_ignition_code"),
            property_loss_dollars=data.get("property_loss_dollars", 0),
            contents_loss_dollars=data.get("contents_loss_dollars", 0),
            narrative=data.get("narrative"),
        )
        issues = self._validate_neris_fields(inc)
        inc.validation_issues = issues if issues else None

        self.db.add(inc)
        await self.db.commit()
        await self.db.refresh(inc)
        logger.info(
            "fire_incident_created",
            extra={
                "tenant_id": str(tenant_id),
                "actor_user_id": str(actor_user_id),
                "incident_id": str(inc.id),
                "correlation_id": correlation_id,
            },
        )
        return {"id": str(inc.id), "validation_issues": issues}

    async def get_incident(
        self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID
    ) -> FireIncident:
        stmt = select(FireIncident).where(
            FireIncident.tenant_id == tenant_id,
            FireIncident.id == incident_id,
        )
        result = await self.db.execute(stmt)
        inc = result.scalar_one_or_none()
        if inc is None:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                status_code=404,
                message="Fire incident not found",
            )
        return inc

    async def list_incidents(
        self, *, tenant_id: uuid.UUID, limit: int = 200, offset: int = 0
    ) -> list[FireIncident]:
        stmt = (
            select(FireIncident)
            .where(FireIncident.tenant_id == tenant_id)
            .order_by(FireIncident.incident_date.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def lock_incident(
        self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID
    ) -> None:
        inc = await self.get_incident(
            tenant_id=tenant_id, incident_id=incident_id
        )
        if inc.locked:
            raise AppError(
                code=ErrorCodes.CONFLICT,
                status_code=409,
                message="Incident already locked",
            )
        inc.locked = True
        await self.db.commit()

    # ── PERSONNEL ─────────────────────────────────────────────────────────

    async def assign_personnel(
        self,
        *,
        tenant_id: uuid.UUID,
        incident_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self.get_incident(tenant_id=tenant_id, incident_id=incident_id)
        pa = FirePersonnelAssignment(
            incident_id=incident_id,
            member_id=data.get("member_id"),
            role=data.get("role"),
            activity_code=data.get("activity_code"),
            injury_type_code=data.get("injury_type_code"),
        )
        self.db.add(pa)
        await self.db.commit()
        await self.db.refresh(pa)
        return {"id": str(pa.id)}

    # ── APPARATUS ─────────────────────────────────────────────────────────

    async def add_apparatus(
        self,
        *,
        tenant_id: uuid.UUID,
        incident_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self.get_incident(tenant_id=tenant_id, incident_id=incident_id)
        ar = FireApparatusRecord(
            incident_id=incident_id,
            unit_id=data.get("unit_id"),
            apparatus_type_code=data.get("apparatus_type_code"),
            dispatch_time=data.get("dispatch_time"),
            enroute_time=data.get("enroute_time"),
            arrival_time=data.get("arrival_time"),
            clear_time=data.get("clear_time"),
            actions_taken=data.get("actions_taken"),
            personnel_count=data.get("personnel_count"),
        )
        self.db.add(ar)
        await self.db.commit()
        await self.db.refresh(ar)
        return {"id": str(ar.id)}

    # ── NERIS VALIDATION ──────────────────────────────────────────────────

    def _validate_neris_fields(self, inc: FireIncident) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        for field in _SECTION_A_REQUIRED:
            if not getattr(inc, field, None):
                issues.append(
                    {"field": field, "section": "A", "severity": "error", "message": f"Required NERIS Section A field '{field}' is missing"}
                )
        if inc.neris_incident_type_code and str(inc.neris_incident_type_code).startswith("1"):
            for field in _SECTION_C_REQUIRED:
                if not getattr(inc, field, None):
                    issues.append(
                        {"field": field, "section": "C", "severity": "error", "message": f"Required NERIS Section C field '{field}' is missing for fire incidents"}
                    )
        if inc.property_use_code is None:
            issues.append(
                {"field": "property_use_code", "section": "B", "severity": "warning", "message": "Property use code recommended"}
            )
        if not inc.narrative:
            issues.append(
                {"field": "narrative", "section": "supplement", "severity": "warning", "message": "Narrative supplement recommended for completeness"}
            )
        return issues

    async def validate_incident(
        self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID
    ) -> list[dict[str, str]]:
        inc = await self.get_incident(
            tenant_id=tenant_id, incident_id=incident_id
        )
        issues = self._validate_neris_fields(inc)
        inc.validation_issues = issues if issues else None
        await self.db.commit()
        return issues

    # ── NERIS EXPORT ──────────────────────────────────────────────────────

    async def create_export_job(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_ids: list[str],
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        validation_results: list[dict[str, Any]] = []
        has_errors = False
        for iid in incident_ids:
            issues = await self.validate_incident(
                tenant_id=tenant_id, incident_id=uuid.UUID(iid)
            )
            errors = [i for i in issues if i["severity"] == "error"]
            validation_results.append(
                {"incident_id": iid, "issues": issues, "valid": len(errors) == 0}
            )
            if errors:
                has_errors = True

        state = NERISExportState.REJECTED.value if has_errors else NERISExportState.VALIDATED.value
        job = NERISExportJob(
            tenant_id=tenant_id,
            incident_ids=incident_ids,
            state=state,
            record_count=len(incident_ids),
            validation_results=validation_results,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        logger.info(
            "neris_export_job_created",
            extra={
                "tenant_id": str(tenant_id),
                "actor_user_id": str(actor_user_id),
                "job_id": str(job.id),
                "state": state,
                "incident_count": len(incident_ids),
                "correlation_id": correlation_id,
            },
        )
        return {
            "job_id": str(job.id),
            "state": state,
            "validation_results": validation_results,
        }

    async def get_export_job(
        self, *, tenant_id: uuid.UUID, job_id: uuid.UUID
    ) -> NERISExportJob:
        stmt = select(NERISExportJob).where(
            NERISExportJob.tenant_id == tenant_id,
            NERISExportJob.id == job_id,
        )
        result = await self.db.execute(stmt)
        job = result.scalar_one_or_none()
        if job is None:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                status_code=404,
                message="NERIS export job not found",
            )
        return job

    # ── PREPLANS ──────────────────────────────────────────────────────────

    async def create_preplan(
        self,
        *,
        tenant_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        pp = FirePreplan(
            tenant_id=tenant_id,
            name=data.get("name"),
            address=data.get("address"),
            occupancy_type=data.get("occupancy_type"),
            construction_type=data.get("construction_type"),
            stories=data.get("stories"),
            sprinkler_system=data.get("sprinkler_system", False),
            standpipe=data.get("standpipe", False),
            fire_alarm_system=data.get("fire_alarm_system", False),
            hazards=data.get("hazards"),
            contacts=data.get("contacts"),
            notes=data.get("notes"),
            floor_plans_s3_keys=data.get("floor_plans_s3_keys"),
        )
        self.db.add(pp)
        await self.db.commit()
        await self.db.refresh(pp)
        return {"id": str(pp.id)}

    async def list_preplans(
        self, *, tenant_id: uuid.UUID, limit: int = 500
    ) -> list[FirePreplan]:
        stmt = (
            select(FirePreplan)
            .where(FirePreplan.tenant_id == tenant_id)
            .order_by(FirePreplan.name)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── HYDRANTS ──────────────────────────────────────────────────────────

    async def create_hydrant(
        self,
        *,
        tenant_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        h = FireHydrant(
            tenant_id=tenant_id,
            hydrant_number=data.get("hydrant_number"),
            latitude=data.get("latitude") or data.get("lat"),
            longitude=data.get("longitude") or data.get("lng"),
            flow_rate_gpm=data.get("flow_rate_gpm"),
            static_pressure_psi=data.get("static_pressure_psi"),
            color_code=data.get("color_code"),
            in_service=data.get("in_service", True),
            notes=data.get("notes"),
        )
        self.db.add(h)
        await self.db.commit()
        await self.db.refresh(h)
        return {"id": str(h.id)}

    # ── INSPECTIONS ───────────────────────────────────────────────────────

    async def create_inspection(
        self,
        *,
        tenant_id: uuid.UUID,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        insp = FireInspection(
            tenant_id=tenant_id,
            preplan_id=uuid.UUID(data["preplan_id"]) if data.get("preplan_id") else None,
            inspector_id=uuid.UUID(data["inspector_id"]) if data.get("inspector_id") else None,
            status=data.get("status", "SCHEDULED"),
            scheduled_date=data.get("scheduled_date"),
            completed_date=data.get("completed_date"),
            findings=data.get("findings"),
            deficiencies=data.get("deficiencies"),
            corrective_due_date=data.get("corrective_due_date"),
            photos_s3_keys=data.get("photos_s3_keys"),
        )
        self.db.add(insp)
        await self.db.commit()
        await self.db.refresh(insp)
        return {"id": str(insp.id)}

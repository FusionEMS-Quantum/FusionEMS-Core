from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from core_app.core.errors import AppError
from core_app.models.terminology import TerminologyCodeSystem, TerminologyConcept, TerminologyMapping
from core_app.repositories.terminology_repository import TerminologyRepository
from core_app.schemas.terminology import (
    TerminologyCodeSystemCreate,
    TerminologyConceptCreate,
    TerminologyMappingCreate,
)
from core_app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MutationContext:
    tenant_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    correlation_id: str | None


class TerminologyService:
    """Centralized terminology service.

    Responsibilities:
    - Tenant-scoped terminology CRUD (code systems, concepts, mappings)
    - Search/autocomplete primitives
    - Audit logging for all mutations

    Notes:
    - Does not embed any licensed datasets.
    - Designed for founder-admin controlled ingestion of official source files.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = TerminologyRepository(db)
        self._audit = AuditService(db)

    # ── Code systems ──────────────────────────────────────────────────────

    def list_code_systems(self, *, tenant_id: uuid.UUID) -> list[TerminologyCodeSystem]:
        return self._repo.list_code_systems(tenant_id=tenant_id)

    def upsert_code_system(
        self,
        *,
        ctx: MutationContext,
        payload: TerminologyCodeSystemCreate,
    ) -> TerminologyCodeSystem:
        before: dict[str, Any] | None = None
        existing = None

        # Best-effort load for audit diff
        for row in self._repo.list_code_systems(tenant_id=ctx.tenant_id):
            if row.system_uri == payload.system_uri and row.system_version == payload.system_version:
                existing = row
                break

        if existing is not None:
            before = {
                "name": existing.name,
                "publisher": existing.publisher,
                "status": existing.status,
                "is_external": existing.is_external,
                "metadata_blob": existing.metadata_blob,
            }

        row = self._repo.upsert_code_system(
            tenant_id=ctx.tenant_id,
            payload={
                "system_uri": payload.system_uri,
                "system_version": payload.system_version,
                "name": payload.name,
                "publisher": payload.publisher,
                "status": payload.status,
                "is_external": payload.is_external,
                "metadata_blob": payload.metadata_blob,
            },
        )

        after = {
            "name": row.name,
            "publisher": row.publisher,
            "status": row.status,
            "is_external": row.is_external,
            "metadata_blob": row.metadata_blob,
        }
        field_changes = {"before": before or {}, "after": after}

        self._audit.log_mutation(
            tenant_id=ctx.tenant_id,
            action="upsert",
            entity_name="terminology_code_systems",
            entity_id=row.id,
            actor_user_id=ctx.actor_user_id,
            field_changes=field_changes,
            correlation_id=ctx.correlation_id,
        )

        self._db.commit()
        self._db.refresh(row)
        return row

    # ── Concepts ──────────────────────────────────────────────────────────

    def search_concepts(
        self,
        *,
        tenant_id: uuid.UUID,
        code_system_id: uuid.UUID | None,
        q: str,
        limit: int,
    ) -> list[TerminologyConcept]:
        return self._repo.search_concepts(
            tenant_id=tenant_id,
            code_system_id=code_system_id,
            q=q,
            limit=limit,
        )

    def get_concept(
        self,
        *,
        tenant_id: uuid.UUID,
        code_system_id: uuid.UUID,
        code: str,
    ) -> TerminologyConcept:
        row = self._repo.get_concept_by_code(
            tenant_id=tenant_id,
            code_system_id=code_system_id,
            code=code,
        )
        if row is None:
            raise AppError(
                status_code=404,
                code="TERMINOLOGY_CONCEPT_NOT_FOUND",
                message="Concept not found.",
            )
        return row

    def bulk_upsert_concepts(
        self,
        *,
        ctx: MutationContext,
        code_system_id: uuid.UUID,
        concepts: list[TerminologyConceptCreate],
    ) -> int:
        # Validate code_system belongs to tenant
        cs = self._db.get(TerminologyCodeSystem, code_system_id)
        if cs is None or cs.tenant_id != ctx.tenant_id:
            raise AppError(
                status_code=404,
                code="TERMINOLOGY_CODE_SYSTEM_NOT_FOUND",
                message="Code system not found.",
            )

        count = self._repo.bulk_upsert_concepts(
            tenant_id=ctx.tenant_id,
            code_system_id=code_system_id,
            concepts=[c.model_dump() for c in concepts],
        )

        self._audit.log_mutation(
            tenant_id=ctx.tenant_id,
            action="bulk_upsert",
            entity_name="terminology_concepts",
            entity_id=code_system_id,
            actor_user_id=ctx.actor_user_id,
            field_changes={
                "code_system_id": str(code_system_id),
                "concept_count": len(concepts),
                "rows_affected": count,
            },
            correlation_id=ctx.correlation_id,
        )

        self._db.commit()
        return count

    # ── Mappings ──────────────────────────────────────────────────────────

    def upsert_mapping(
        self,
        *,
        ctx: MutationContext,
        payload: TerminologyMappingCreate,
    ) -> TerminologyMapping:
        # Guard tenant isolation on referenced concept rows.
        for cid in (payload.from_concept_id, payload.to_concept_id):
            concept = self._db.get(TerminologyConcept, cid)
            if concept is None or concept.tenant_id != ctx.tenant_id:
                raise AppError(
                    status_code=404,
                    code="TERMINOLOGY_CONCEPT_NOT_FOUND",
                    message="Concept not found.",
                )

        row = self._repo.create_mapping(
            tenant_id=ctx.tenant_id,
            payload={
                "from_concept_id": payload.from_concept_id,
                "to_concept_id": payload.to_concept_id,
                "map_type": payload.map_type,
                "source": payload.source,
                "confidence": payload.confidence,
                "metadata_blob": payload.metadata_blob,
            },
        )

        self._audit.log_mutation(
            tenant_id=ctx.tenant_id,
            action="upsert",
            entity_name="terminology_mappings",
            entity_id=row.id,
            actor_user_id=ctx.actor_user_id,
            field_changes={"after": payload.model_dump()},
            correlation_id=ctx.correlation_id,
        )

        self._db.commit()
        self._db.refresh(row)
        return row

    def list_mappings_for_concept(
        self,
        *,
        tenant_id: uuid.UUID,
        concept_id: uuid.UUID,
        limit: int,
    ) -> list[TerminologyMapping]:
        return self._repo.list_mappings_for_concept(
            tenant_id=tenant_id,
            concept_id=concept_id,
            limit=limit,
        )

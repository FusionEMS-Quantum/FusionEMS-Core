from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from core_app.models.terminology import (
    TerminologyCodeSystem,
    TerminologyConcept,
    TerminologyMapping,
    TerminologySynonym,
)


class TerminologyRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Code systems ──────────────────────────────────────────────────────

    def list_code_systems(self, *, tenant_id: uuid.UUID) -> list[TerminologyCodeSystem]:
        stmt = (
            select(TerminologyCodeSystem)
            .where(TerminologyCodeSystem.tenant_id == tenant_id)
            .order_by(TerminologyCodeSystem.system_uri, TerminologyCodeSystem.system_version)
        )
        return list(self._db.scalars(stmt))

    def upsert_code_system(
        self, *, tenant_id: uuid.UUID, payload: dict
    ) -> TerminologyCodeSystem:
        # Deterministic upsert keyed by (tenant_id, system_uri, system_version)
        stmt = (
            insert(TerminologyCodeSystem)
            .values(tenant_id=tenant_id, **payload)
            .on_conflict_do_update(
                index_elements=[
                    TerminologyCodeSystem.tenant_id,
                    TerminologyCodeSystem.system_uri,
                    TerminologyCodeSystem.system_version,
                ],
                set_={
                    "name": payload.get("name"),
                    "publisher": payload.get("publisher"),
                    "status": payload.get("status"),
                    "is_external": payload.get("is_external"),
                    "metadata_blob": payload.get("metadata_blob", {}),
                    "updated_at": func.now(),
                    "version": TerminologyCodeSystem.version + 1,
                },
            )
            .returning(TerminologyCodeSystem.id)
        )
        code_system_id = self._db.execute(stmt).scalar_one()
        row = self._db.get(TerminologyCodeSystem, code_system_id)
        if row is None:
            raise RuntimeError("Terminology upsert failed to return row")
        return row

    # ── Concepts ──────────────────────────────────────────────────────────

    def get_concept_by_code(
        self,
        *,
        tenant_id: uuid.UUID,
        code_system_id: uuid.UUID,
        code: str,
    ) -> TerminologyConcept | None:
        stmt = (
            select(TerminologyConcept)
            .where(
                and_(
                    TerminologyConcept.tenant_id == tenant_id,
                    TerminologyConcept.code_system_id == code_system_id,
                    TerminologyConcept.code == code,
                )
            )
            .limit(1)
        )
        return self._db.scalars(stmt).first()

    def search_concepts(
        self,
        *,
        tenant_id: uuid.UUID,
        code_system_id: uuid.UUID | None,
        q: str,
        limit: int,
    ) -> list[TerminologyConcept]:
        q_norm = q.strip()
        if not q_norm:
            return []

        filters: list = [TerminologyConcept.tenant_id == tenant_id]
        if code_system_id is not None:
            filters.append(TerminologyConcept.code_system_id == code_system_id)

        # Search order: code prefix, display prefix, code contains, display contains, synonyms contains.
        code_prefix = f"{q_norm}%"
        contains = f"%{q_norm}%"

        synonym_subq: Select = (
            select(TerminologySynonym.concept_id)
            .where(
                and_(
                    TerminologySynonym.tenant_id == tenant_id,
                    TerminologySynonym.synonym.ilike(contains),
                )
            )
            .limit(limit)
        )

        stmt = (
            select(TerminologyConcept)
            .where(
                and_(
                    *filters,
                    or_(
                        TerminologyConcept.code.ilike(contains),
                        TerminologyConcept.display.ilike(contains),
                        TerminologyConcept.id.in_(synonym_subq),
                    ),
                )
            )
            .order_by(
                # Prefer prefix matches
                case(
                    (TerminologyConcept.code.ilike(code_prefix), 0),
                    (TerminologyConcept.display.ilike(code_prefix), 1),
                    else_=2,
                ).asc(),
                func.length(TerminologyConcept.code).asc(),
                TerminologyConcept.code.asc(),
            )
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def bulk_upsert_concepts(
        self,
        *,
        tenant_id: uuid.UUID,
        code_system_id: uuid.UUID,
        concepts: Iterable[dict],
    ) -> int:
        rows = [
            {
                "tenant_id": tenant_id,
                "code_system_id": code_system_id,
                **concept,
            }
            for concept in concepts
        ]
        if not rows:
            return 0

        stmt = insert(TerminologyConcept).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                TerminologyConcept.tenant_id,
                TerminologyConcept.code_system_id,
                TerminologyConcept.code,
            ],
            set_={
                "display": stmt.excluded.display,
                "definition": stmt.excluded.definition,
                "active": stmt.excluded.active,
                "effective_start_date": stmt.excluded.effective_start_date,
                "effective_end_date": stmt.excluded.effective_end_date,
                "properties": stmt.excluded.properties,
                "updated_at": func.now(),
                "version": TerminologyConcept.version + 1,
            },
        )
        result = self._db.execute(stmt)
        # rowcount can be unreliable with executemany; treat as best-effort.
        return int(getattr(result, "rowcount", 0) or 0)

    # ── Mappings ──────────────────────────────────────────────────────────

    def create_mapping(
        self,
        *,
        tenant_id: uuid.UUID,
        payload: dict,
    ) -> TerminologyMapping:
        stmt = (
            insert(TerminologyMapping)
            .values(tenant_id=tenant_id, **payload)
            .on_conflict_do_update(
                index_elements=[
                    TerminologyMapping.tenant_id,
                    TerminologyMapping.from_concept_id,
                    TerminologyMapping.to_concept_id,
                    TerminologyMapping.map_type,
                    TerminologyMapping.source,
                ],
                set_={
                    "confidence": payload.get("confidence"),
                    "is_active": True,
                    "metadata_blob": payload.get("metadata_blob", {}),
                    "updated_at": func.now(),
                    "version": TerminologyMapping.version + 1,
                },
            )
            .returning(TerminologyMapping.id)
        )
        mapping_id = self._db.execute(stmt).scalar_one()
        row = self._db.get(TerminologyMapping, mapping_id)
        if row is None:
            raise RuntimeError("Terminology mapping upsert failed to return row")
        return row

    def list_mappings_for_concept(
        self,
        *,
        tenant_id: uuid.UUID,
        concept_id: uuid.UUID,
        limit: int,
    ) -> list[TerminologyMapping]:
        stmt = (
            select(TerminologyMapping)
            .where(
                and_(
                    TerminologyMapping.tenant_id == tenant_id,
                    TerminologyMapping.is_active.is_(True),
                    or_(
                        TerminologyMapping.from_concept_id == concept_id,
                        TerminologyMapping.to_concept_id == concept_id,
                    ),
                )
            )
            .order_by(TerminologyMapping.updated_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

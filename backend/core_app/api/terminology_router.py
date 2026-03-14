from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.schemas.terminology import (
    NihClinicalTablesLookupResponse,
    NpiLookupRequest,
    NpiLookupResponse,
    RxNavNormalizeRequest,
    RxNavNormalizeResponse,
    TerminologyAutocompleteResponse,
    TerminologyCodeSystemCreate,
    TerminologyCodeSystemResponse,
    TerminologyConceptBulkUpsertRequest,
    TerminologyConceptResponse,
    TerminologyExternalLookupRequest,
    TerminologyMappingCreate,
    TerminologyMappingResponse,
    TerminologySearchResponse,
)
from core_app.services.terminology_service import MutationContext, TerminologyService

router = APIRouter(prefix="/api/v1/terminology", tags=["Terminology"])

_WRITE_ROLES = frozenset({"founder", "agency_admin", "billing", "compliance", "admin"})


def _svc(db: Session) -> TerminologyService:
    return TerminologyService(db)


def _check_write(current: CurrentUser) -> None:
    if current.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


def _ctx(request: Request, current: CurrentUser) -> MutationContext:
    return MutationContext(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/code-systems", response_model=list[TerminologyCodeSystemResponse])
def list_code_systems(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[TerminologyCodeSystemResponse]:
    svc = _svc(db)
    rows = svc.list_code_systems(tenant_id=current.tenant_id)
    return [TerminologyCodeSystemResponse.model_validate(r, from_attributes=True) for r in rows]


@router.put("/code-systems", response_model=TerminologyCodeSystemResponse)
def upsert_code_system(
    body: TerminologyCodeSystemCreate,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> TerminologyCodeSystemResponse:
    _check_write(current)
    svc = _svc(db)
    row = svc.upsert_code_system(ctx=_ctx(request, current), payload=body)
    return TerminologyCodeSystemResponse.model_validate(row, from_attributes=True)


@router.get("/concepts/search", response_model=TerminologySearchResponse)
def search_concepts(
    q: str = Query(min_length=1, max_length=200),
    code_system_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> TerminologySearchResponse:
    svc = _svc(db)
    rows = svc.search_concepts(
        tenant_id=current.tenant_id,
        code_system_id=code_system_id,
        q=q,
        limit=limit,
    )
    return TerminologySearchResponse(
        results=[TerminologyConceptResponse.model_validate(r, from_attributes=True) for r in rows]
    )


@router.get("/concepts/autocomplete", response_model=TerminologyAutocompleteResponse)
def autocomplete(
    q: str = Query(min_length=1, max_length=200),
    code_system_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> TerminologyAutocompleteResponse:
    svc = _svc(db)
    rows = svc.search_concepts(
        tenant_id=current.tenant_id,
        code_system_id=code_system_id,
        q=q,
        limit=limit,
    )
    return TerminologyAutocompleteResponse(
        suggestions=[TerminologyConceptResponse.model_validate(r, from_attributes=True) for r in rows]
    )


@router.get(
    "/code-systems/{code_system_id}/concepts/{code}",
    response_model=TerminologyConceptResponse,
)
def get_concept(
    code_system_id: uuid.UUID,
    code: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> TerminologyConceptResponse:
    svc = _svc(db)
    row = svc.get_concept(
        tenant_id=current.tenant_id,
        code_system_id=code_system_id,
        code=code,
    )
    return TerminologyConceptResponse.model_validate(row, from_attributes=True)


@router.post("/concepts/bulk-upsert")
def bulk_upsert_concepts(
    body: TerminologyConceptBulkUpsertRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    _check_write(current)
    svc = _svc(db)
    affected = svc.bulk_upsert_concepts(
        ctx=_ctx(request, current),
        code_system_id=body.code_system_id,
        concepts=body.concepts,
    )
    return {"rows_affected": affected}


@router.post("/mappings", response_model=TerminologyMappingResponse)
def upsert_mapping(
    body: TerminologyMappingCreate,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> TerminologyMappingResponse:
    _check_write(current)
    svc = _svc(db)
    row = svc.upsert_mapping(ctx=_ctx(request, current), payload=body)
    return TerminologyMappingResponse.model_validate(row, from_attributes=True)


@router.get("/concepts/{concept_id}/mappings", response_model=list[TerminologyMappingResponse])
def list_mappings_for_concept(
    concept_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[TerminologyMappingResponse]:
    svc = _svc(db)
    rows = svc.list_mappings_for_concept(
        tenant_id=current.tenant_id,
        concept_id=concept_id,
        limit=limit,
    )
    return [TerminologyMappingResponse.model_validate(r, from_attributes=True) for r in rows]


_TABLE_RE = re.compile(r"^[a-z0-9_]{1,64}$")


@router.post("/external/nih/{table}", response_model=NihClinicalTablesLookupResponse)
async def nih_lookup(
    table: str,
    body: TerminologyExternalLookupRequest,
    current: CurrentUser = Depends(get_current_user),
) -> NihClinicalTablesLookupResponse:
    if not _TABLE_RE.fullmatch(table):
        raise HTTPException(status_code=400, detail="Invalid table")

    from core_app.integrations.nih_clinical_tables import NihClinicalTablesClient

    client = NihClinicalTablesClient()
    try:
        results = await client.search(table=table, terms=body.q, limit=body.limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="External lookup failed") from exc

    return NihClinicalTablesLookupResponse(
        results=[{"code": r.code, "display": r.display, "extra": r.extra} for r in results]
    )


@router.post("/external/rxnav/normalize", response_model=RxNavNormalizeResponse)
async def rxnav_normalize(
    body: RxNavNormalizeRequest,
    current: CurrentUser = Depends(get_current_user),
) -> RxNavNormalizeResponse:
    from core_app.integrations.rxnav import RxNavClient

    client = RxNavClient()
    try:
        matches = await client.approximate_term(term=body.name, limit=1, max_entries=1)
        rxnorm_cui = matches[0].rxcui if matches else None
        normalized_name = None
        if rxnorm_cui:
            normalized_name = await client.rxcui_to_name(rxcui=rxnorm_cui)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="External lookup failed") from exc

    match_obj: dict[str, Any] | None = None
    if matches:
        match_obj = {
            "rxcui": matches[0].rxcui,
            "score": matches[0].score,
            "name": matches[0].name,
            "extra": matches[0].extra,
        }

    return RxNavNormalizeResponse(
        rxnorm_cui=rxnorm_cui,
        normalized_name=normalized_name,
        ingredients=[],
        result={"match": match_obj},
    )


@router.post("/external/npi/lookup", response_model=NpiLookupResponse)
async def npi_lookup(
    body: NpiLookupRequest,
    current: CurrentUser = Depends(get_current_user),
) -> NpiLookupResponse:
    from core_app.integrations.npi_registry import NpiRegistryClient

    client = NpiRegistryClient()
    try:
        results = await client.search(
            number=body.npi,
            organization_name=body.name,
            first_name=None,
            last_name=None,
            city=body.city,
            state=body.state,
            limit=body.limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="External lookup failed") from exc

    return NpiLookupResponse(
        results=[
            {
                "npi": r.npi,
                "name": r.name,
                "enumeration_type": r.enumeration_type,
                "extra": r.extra,
            }
            for r in results
        ]
    )

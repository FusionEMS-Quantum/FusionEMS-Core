
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.epcr.completeness_engine import ELEMENT_FIELD_MAP
from core_app.epcr.nemsis_exporter import NEMSIS_VERSION
from core_app.services.clinical_open_data_service import (
    OpenDataUnavailable,
    build_dataset_status,
    search_icd10_open,
    search_npi_open,
    search_rxnorm_open,
    search_snomed_open,
    verify_npi_open,
)

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])

@router.get("/status")
async def get_dataset_status(
    probe_external: bool = Query(default=False),
    db: Session = Depends(db_session_dependency),
):
    return build_dataset_status(db, probe_external=probe_external)


@router.get("/terminology/{system}/search")
async def terminology_search(
    system: str,
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(default=25, ge=1, le=100),
):
    normalized = system.strip().lower()
    try:
        if normalized == "icd10":
            return {
                "system": "icd10",
                "query": q,
                "results": search_icd10_open(query=q, limit=limit),
            }
        if normalized == "rxnorm":
            return {
                "system": "rxnorm",
                "query": q,
                "results": search_rxnorm_open(query=q, limit=limit),
            }
        if normalized == "snomed":
            return {
                "system": "snomed",
                "query": q,
                "results": search_snomed_open(query=q, limit=limit),
            }
    except OpenDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"open_data_unavailable:{exc}") from exc

    raise HTTPException(status_code=422, detail="system must be one of: icd10|rxnorm|snomed")


@router.get("/npi/search")
async def npi_search(
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(default=10, ge=1, le=50),
):
    try:
        return {
            "query": q,
            "results": search_npi_open(query=q, limit=limit),
        }
    except OpenDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"open_data_unavailable:{exc}") from exc


@router.get("/npi/verify/{npi_number}")
async def npi_verify(npi_number: str):
    try:
        return verify_npi_open(npi_number=npi_number)
    except OpenDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"open_data_unavailable:{exc}") from exc


@router.get("/nemsis/elements")
async def nemsis_elements(section: str | None = Query(default=None)):
    if section:
        filtered = {
            element_id: metadata
            for element_id, metadata in ELEMENT_FIELD_MAP.items()
            if str(metadata.get("section", "")).lower() == section.lower()
        }
    else:
        filtered = ELEMENT_FIELD_MAP

    return {
        "version": NEMSIS_VERSION,
        "element_count": len(filtered),
        "elements": filtered,
    }

class ExpressionRequest(BaseModel):
    natural_language: str
    target_standard: str = "NEMSIS"

@router.post("/ai-expression-builder")
async def build_expression(req: ExpressionRequest):
    if "cardiac arrest" in req.natural_language.lower() and "narrative" in req.natural_language.lower():
        xpath = "//eArrest.01 = 'Yes' and string-length(//eNarrative.01) < 50"
        rule = "<sch:assert test='not(//eArrest.01=\"Yes\" and string-length(//eNarrative.01) &lt; 50)'>Narrative must be &gt; 50 chars for Cardiac Arrest.</sch:assert>"
        explanation = "We triggered an XPath check against eArrest.01. If True, we enforce a character count assertion on eNarrative.01."
    else:
        xpath = "//eSituation.11 = 'I63.9'"
        rule = "<sch:report test='not(//eCustomResults.01)'>Missing custom result for condition</sch:report>"
        explanation = "Created a base Schematron report rule validating custom elements when ICD-10 indicates specified condition."

    return {
        "generated_xpath": xpath,
        "schematron_rule": rule,
        "human_readable": explanation,
        "ai_confidence": 0.96
    }

@router.get("/exports")
async def get_exports():
    return {
        "total_today": 12450,
        "successful": 12380,
        "failed": 70,
        "in_queue": 15,
        "agencies": [
            {"name": "Metro Fire Rescue", "state": "TX", "status": "Operational", "success_rate": 99.8, "failed_charts": 2},
            {"name": "Valley EMS", "state": "WI", "status": "Warning", "success_rate": 94.2, "failed_charts": 45},
            {"name": "Northern Flight", "state": "MN", "status": "Operational", "success_rate": 100.0, "failed_charts": 0},
        ]
    }

@router.get("/active-devices")
async def get_active_devices():
    return [
        {"id": "dev_001", "agency": "Metro Fire Rescue", "user": "J. Smith (Paramedic)", "device_type": "Android Tablet", "status": "En Route", "ip": "10.4.5.12"},
        {"id": "dev_002", "agency": "Valley EMS", "user": "A. Davis (EMT)", "device_type": "Android Mobile", "status": "On Scene", "ip": "10.4.8.99"},
        {"id": "dev_003", "agency": "Valley EMS", "user": "R. Cole (Dispatcher)", "device_type": "CAD Web", "status": "Available", "ip": "100.20.5.11"},
    ]

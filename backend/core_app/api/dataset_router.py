
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])

@router.get("/status")
async def get_dataset_status():
    return {
        "nemsis": {"version": "3.5.0", "last_update": "2026-03-01", "schematron_active": True},
        "neris": {"version": "1.0", "last_update": "2025-11-15", "schematron_active": True},
        "rxnorm": {"version": "2026.01", "last_update": "2026-01-05", "term_count": 348210},
        "snomed": {"version": "2026.02", "last_update": "2026-02-15", "term_count": 482190},
        "icd10": {"version": "2026", "last_update": "2025-10-01", "term_count": 72184},
        "facilities": {"active_count": 14920, "last_state_sync": "2026-03-05"}
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

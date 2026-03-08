"""Gold standard compliance router.

Provides deterministic capability/status metadata for compliance feature gating.
"""
from fastapi import APIRouter

router = APIRouter(tags=["Gold Standard"])


@router.get("/api/v1/gold-standard/status")
async def gold_standard_status() -> dict[str, object]:
    return {
        "enabled": True,
        "mode": "enforced",
        "controls": {
            "schema_validation": True,
            "auditability": True,
            "tenant_isolation_checks": True,
        },
    }

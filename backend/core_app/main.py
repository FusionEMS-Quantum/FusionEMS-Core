# ruff: noqa: I001

import logging
import os

# pylint: disable=broad-exception-caught
import redis.asyncio as aioredis
import sqlalchemy
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from core_app.core.config import get_settings
from core_app.core.errors import AppError
from core_app.core.logging import configure_logging
from core_app.db.session import async_engine
from core_app.middleware.audit_logging import AuditLoggingMiddleware
from core_app.middleware.phi_lock import PHILockMiddleware
from core_app.middleware.rate_limiter import TenantRateLimitMiddleware
from core_app.middleware.security_headers import SecurityHeadersMiddleware
from core_app.middleware.tenant_context import TenantContextMiddleware
from core_app.observability.otel import configure_otel

settings = get_settings()
configure_logging("DEBUG" if settings.debug else "INFO")
logger = logging.getLogger(__name__)
logger.info("integration_state_table=%s", settings.integration_state_table())

from core_app.api.accreditation_router import router as accreditation_router  # noqa: E402
from core_app.api.ai_platform_router import router as ai_platform_router  # noqa: E402
from core_app.api.ai_router import router as ai_router  # noqa: E402
from core_app.api.analytics_router import router as analytics_router  # noqa: E402
from core_app.api.ar_router import router as ar_router  # noqa: E402
from core_app.api.audit_router import router as audit_router  # noqa: E402
from core_app.api.auth_rep_router import router as auth_rep_router  # noqa: E402
from core_app.api.auth_router import router as auth_router  # noqa: E402
from core_app.api.billing_router import router as billing_router  # noqa: E402
from core_app.api.cad_calls_router import router as cad_calls_router  # noqa: E402
from core_app.api.cad_units_router import router as cad_units_router  # noqa: E402
from core_app.api.cases_router import router as cases_router  # noqa: E402
from core_app.api.claim_packet_router import router as claim_packet_router  # noqa: E402
from core_app.api.clinical_workflow_router import router as clinical_workflow_router  # noqa: E402
from core_app.api.cms_gate_router import router as cms_gate_router  # noqa: E402
from core_app.api.compliance_command_router import router as compliance_command_router  # noqa: E402
from core_app.api.compliance_pack_index_router import (  # noqa: E402
    router as compliance_pack_index_router,
)
from core_app.api.contact_preference_router import router as contact_preference_router  # noqa: E402
from core_app.api.crewlink_paging_router import router as crewlink_paging_router  # noqa: E402
from core_app.api.crewlink_router import router as crewlink_router  # noqa: E402
from core_app.api.customer_success_router import router as customer_success_router  # noqa: E402
from core_app.api.dataset_router import router as dataset_router  # noqa: E402
from core_app.api.dea_compliance_router import router as dea_compliance_router  # noqa: E402
from core_app.api.dispatch_router import router as dispatch_router  # noqa: E402
from core_app.api.doc_kit_router import router as doc_kit_router  # noqa: E402
from core_app.api.document_vault_router import router as document_vault_router
from core_app.api.founder_communications_router import router as founder_comms_router
from core_app.api.documents_router import router as documents_router  # noqa: E402
from core_app.api.epcr_capture_router import router as epcr_capture_router  # noqa: E402
from core_app.api.epcr_customization_router import router as epcr_customization_router  # noqa: E402
from core_app.api.epcr_router import router as epcr_router  # noqa: E402
from core_app.api.events_router import router as events_router  # noqa: E402
from core_app.api.export_offboarding_router import (  # noqa: E402
    founder_export_router,
    offboarding_router,
)
from core_app.api.export_offboarding_router import (
    router as export_offboarding_router,
)
from core_app.api.export_status_router import router as export_status_router  # noqa: E402
from core_app.api.exports_router import router as exports_router  # noqa: E402
from core_app.api.facility_router import router as facility_router  # noqa: E402
from core_app.api.fax_router import router as fax_router  # noqa: E402
from core_app.api.fax_webhook_router import router as fax_webhook_router  # noqa: E402
from core_app.api.fhir_router import router as fhir_router  # noqa: E402
from core_app.api.fire_epcr_router import router as fire_epcr_router  # noqa: E402
from core_app.api.fire_ops_router import router as fire_ops_router  # noqa: E402
from core_app.api.fire_statements_router import router as fire_statements_router  # noqa: E402
from core_app.api.fleet_intelligence_router import router as fleet_intelligence_router  # noqa: E402
from core_app.api.fleet_router import router as fleet_router  # noqa: E402
from core_app.api.founder_agents_router import router as founder_agents_router  # noqa: E402
from core_app.api.founder_billing_voice_router import (
    router as founder_billing_voice_router,  # noqa: E402
)
from core_app.api.founder_copilot_router import router as founder_copilot_router  # noqa: E402
from core_app.api.founder_documents_router import router as founder_documents_router  # noqa: E402
from core_app.api.founder_graph_router import router as founder_graph_router  # noqa: E402
from core_app.api.founder_integration_command_router import (  # noqa: E402
    router as founder_integration_command_router,
)
from core_app.api.founder_ops_command_router import (
    router as founder_ops_command_router,  # noqa: E402
)
from core_app.api.founder_records_command_router import (  # noqa: E402
    router as founder_records_command_router,
)
from core_app.api.founder_router import router as founder_router  # noqa: E402
from core_app.api.founder_specialty_ops_command_router import (  # noqa: E402
    router as founder_specialty_ops_command_router,
)
from core_app.api.founder_success_command_router import (
    router as founder_success_command_router,  # noqa: E402
)
from core_app.api.founder_tax_router import tax_advisor_router  # noqa: E402
from core_app.api.founder_accounting_router import accounting_router  # noqa: E402
from core_app.api.governance_router import router as governance_router  # noqa: E402
from core_app.api.health_router import router as health_router  # noqa: E402
from core_app.api.hems_router import router as hems_router  # noqa: E402
from core_app.api.icd10_router import router as icd10_router  # noqa: E402
from core_app.api.terminology_router import router as terminology_router  # noqa: E402
from core_app.api.imports_router import router as imports_router  # noqa: E402
from core_app.api.incident_router import router as incident_router  # noqa: E402
from core_app.api.interop_router import router as interop_router  # noqa: E402
from core_app.api.kitlink_compliance_router import router as kitlink_compliance_router  # noqa: E402
from core_app.api.kitlink_router import router as kitlink_router  # noqa: E402
from core_app.api.legal_requests_router import router as legal_requests_router  # noqa: E402
from core_app.api.lob_router import router as lob_router  # noqa: E402
from core_app.api.lob_webhook_router import router as lob_webhook_router  # noqa: E402
from core_app.api.mdt_router import router as mdt_router  # noqa: E402
from core_app.api.metrics_router import router as metrics_router  # noqa: E402
from core_app.api.microsoft_auth_router import router as microsoft_auth_router  # noqa: E402
from core_app.api.mobile_ops_router import router as mobile_ops_router  # noqa: E402
from core_app.api.nemsis_compliance_studio_router import (  # noqa: E402
    router as nemsis_compliance_studio_router,
)
from core_app.api.nemsis_copilot_router import router as nemsis_copilot_router  # noqa: E402
from core_app.api.nemsis_pack_router import router as nemsis_pack_router  # noqa: E402
from core_app.api.nemsis_router import router as nemsis_router  # noqa: E402
from core_app.api.nemsis_submissions_router import router as nemsis_submissions_router  # noqa: E402
from core_app.api.neris_copilot_router import router as neris_copilot_router  # noqa: E402
from core_app.api.neris_incident_router import router as neris_incident_router  # noqa: E402
from core_app.api.neris_pack_router import router as neris_wi_pack_router  # noqa: E402
from core_app.api.neris_router import router as neris_router  # noqa: E402
from core_app.api.neris_tenant_router import router as neris_tenant_router  # noqa: E402
from core_app.api.onboarding_router import router as onboarding_router  # noqa: E402
from core_app.api.ops_command_router import router as ops_command_router  # noqa: E402
from core_app.api.patient_identity_router import (
    dup_router as identity_dup_router,
)
from core_app.api.patient_identity_router import (
    merge_router as identity_merge_router,
)
from core_app.api.patient_identity_router import (  # noqa: E402
    router as patient_identity_router,
)
from core_app.api.patient_portal_router import router as patient_portal_router  # noqa: E402
from core_app.api.patient_router import router as patient_router  # noqa: E402
from core_app.api.payments_router import router as payments_router  # noqa: E402
from core_app.api.platform_incidents_router import router as platform_incidents_router  # noqa: E402
from core_app.api.platform_core_router import router as platform_core_router
from core_app.api.policy_router import router as policy_router  # noqa: E402
from core_app.api.portal_billing_router import router as portal_billing_router  # noqa: E402
from core_app.api.pricebook_router import router as pricebook_router  # noqa: E402
from core_app.api.pricing_router import router as pricing_router  # noqa: E402
from core_app.api.public_pricing_router import router as public_pricing_router  # noqa: E402
from core_app.api.quantum_csv_router import quantum_csv_router  # noqa: E402
from core_app.api.realtime_router import router as realtime_router  # noqa: E402
from core_app.api.relationship_command_router import (
    router as relationship_command_router,  # noqa: E402
)
from core_app.api.relationship_history_router import (
    facility_router as rel_history_facility_router,
)
from core_app.api.relationship_history_router import (
    general_router as rel_history_general_router,
)
from core_app.api.relationship_history_router import (  # noqa: E402
    patient_router as rel_history_patient_router,
)
from core_app.api.responsible_party_router import (
    link_router as responsible_party_link_router,
)
from core_app.api.responsible_party_router import (  # noqa: E402
    router as responsible_party_router,
)
from core_app.api.roi_funnel_router import router as roi_funnel_router  # noqa: E402
from core_app.api.roi_router import router as roi_router  # noqa: E402
from core_app.api.role_management_router import router as role_management_router  # noqa: E402
from core_app.api.scheduling_router import router as scheduling_router  # noqa: E402
from core_app.api.signatures_router import router as signatures_router  # noqa: E402
from core_app.api.sms_webhook_router import router as sms_webhook_router  # noqa: E402
from core_app.api.staffing_router import router as staffing_router  # noqa: E402
from core_app.api.statements_router import router as statements_router  # noqa: E402
from core_app.api.stripe_webhook_router import router as stripe_webhook_router  # noqa: E402
from core_app.api.support_router import router as support_router  # noqa: E402
from core_app.api.sync_router import router as sync_router  # noqa: E402
from core_app.api.system_health_router import router as system_health_router  # noqa: E402
from core_app.api.systems_router import router as systems_router  # noqa: E402
from core_app.api.tech_copilot_router import router as tech_copilot_router  # noqa: E402
from core_app.api.template_router import router as template_router  # noqa: E402
from core_app.api.tracking_router import router as tracking_router  # noqa: E402
from core_app.api.transportlink_router import router as transportlink_router  # noqa: E402
from core_app.api.trip_router import router as trip_router  # noqa: E402
from core_app.api.visibility_router import router as visibility_router  # noqa: E402
from core_app.api.vital_router import router as vital_router  # noqa: E402
from core_app.api.voice_advanced_router import router as voice_advanced_router  # noqa: E402
from core_app.api.voice_webhook_router import router as voice_webhook_router  # noqa: E402
from core_app.api.weather_router import router as weather_router  # noqa: E402
from core_app.billing.edi_router import router as edi_router  # noqa: E402

app = FastAPI(title=settings.app_name)
configure_otel(app)

_allowed_origins = [
    "https://www.fusionemsquantum.com",
    "https://fusionemsquantum.com",
    "https://app.fusionemsquantum.com",
    "https://api.fusionemsquantum.com",
]
if settings.debug:
    _allowed_origins.extend(
        ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Tenant-ID",
        "X-Correlation-ID",
        "X-Request-ID",
    ],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Correlation-ID"],
    max_age=600,
)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(PHILockMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(TenantRateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    trace_id = getattr(request.state, "correlation_id", None)
    return JSONResponse(status_code=exc.status_code, content=exc.to_response(trace_id=trace_id))


# --- Routers with /api/v1 prefix ---
app.include_router(document_vault_router)
app.include_router(founder_comms_router)
app.include_router(accreditation_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(governance_router, prefix="/api/v1")
app.include_router(policy_router, prefix="/api/v1")
app.include_router(role_management_router, prefix="/api/v1")
app.include_router(fhir_router, prefix="/api/v1")
app.include_router(interop_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(incident_router, prefix="/api/v1")
app.include_router(microsoft_auth_router, prefix="/api/v1")
app.include_router(nemsis_router)
app.include_router(neris_router)
app.include_router(patient_router, prefix="/api/v1")
app.include_router(payments_router)
app.include_router(realtime_router, prefix="/api/v1")
app.include_router(roi_router, prefix="/api/v1")
app.include_router(vital_router, prefix="/api/v1")

# --- Routers without prefix ---
app.include_router(ai_platform_router)
app.include_router(ai_router)
app.include_router(analytics_router)
app.include_router(ar_router)
app.include_router(auth_rep_router)
app.include_router(billing_router)
app.include_router(cad_calls_router)
app.include_router(cad_units_router)
app.include_router(cases_router)
app.include_router(claim_packet_router)
app.include_router(cms_gate_router)
app.include_router(compliance_command_router)
app.include_router(dea_compliance_router)
app.include_router(compliance_pack_index_router)
app.include_router(crewlink_router)
app.include_router(doc_kit_router)
app.include_router(documents_router)
app.include_router(edi_router)
app.include_router(epcr_capture_router)
app.include_router(epcr_customization_router)
app.include_router(epcr_router)
app.include_router(clinical_workflow_router)
app.include_router(events_router)
app.include_router(export_offboarding_router)
app.include_router(export_status_router)
app.include_router(exports_router)
app.include_router(fax_router)
app.include_router(fax_webhook_router)
app.include_router(fire_epcr_router)
app.include_router(fire_ops_router)
app.include_router(fire_statements_router)
app.include_router(fleet_intelligence_router)
app.include_router(fleet_router)
app.include_router(founder_agents_router)
app.include_router(founder_copilot_router)
app.include_router(founder_billing_voice_router)
app.include_router(founder_documents_router)
app.include_router(founder_graph_router)
app.include_router(founder_router)
app.include_router(founder_specialty_ops_command_router)
app.include_router(founder_records_command_router)
app.include_router(founder_integration_command_router)
app.include_router(founder_ops_command_router)
app.include_router(hems_router)
app.include_router(icd10_router)
app.include_router(terminology_router)
app.include_router(imports_router)
app.include_router(kitlink_compliance_router)
app.include_router(kitlink_router)
app.include_router(legal_requests_router)
app.include_router(lob_router)
app.include_router(lob_webhook_router)
app.include_router(mdt_router)
app.include_router(metrics_router)
app.include_router(mobile_ops_router)
app.include_router(nemsis_compliance_studio_router)
app.include_router(nemsis_pack_router)
app.include_router(nemsis_submissions_router)
app.include_router(nemsis_copilot_router)
app.include_router(platform_incidents_router)
app.include_router(tech_copilot_router)
app.include_router(neris_copilot_router)
app.include_router(neris_incident_router)
app.include_router(neris_tenant_router)
app.include_router(neris_wi_pack_router)
app.include_router(onboarding_router)
app.include_router(pricebook_router)
app.include_router(pricing_router)
app.include_router(public_pricing_router)
app.include_router(roi_funnel_router)
app.include_router(scheduling_router)
app.include_router(patient_portal_router)
app.include_router(portal_billing_router)
app.include_router(offboarding_router)
app.include_router(founder_export_router)
app.include_router(signatures_router)
app.include_router(sms_webhook_router)
app.include_router(statements_router)
app.include_router(stripe_webhook_router)
app.include_router(support_router)
app.include_router(system_health_router)
app.include_router(systems_router)
app.include_router(template_router)
app.include_router(tracking_router)
app.include_router(transportlink_router)
app.include_router(dispatch_router)
app.include_router(crewlink_paging_router)
app.include_router(staffing_router)
app.include_router(ops_command_router)
app.include_router(trip_router)
app.include_router(visibility_router)
app.include_router(voice_advanced_router)
app.include_router(voice_webhook_router)
app.include_router(weather_router)
app.include_router(sync_router)

# --- CRM / Relationship routers (self-prefixed) ---
app.include_router(patient_identity_router)
app.include_router(identity_dup_router)
app.include_router(identity_merge_router)
app.include_router(responsible_party_router)
app.include_router(responsible_party_link_router)
app.include_router(facility_router)
app.include_router(rel_history_patient_router)
app.include_router(rel_history_facility_router)
app.include_router(rel_history_general_router)
app.include_router(contact_preference_router)
app.include_router(relationship_command_router)

# --- Customer Success Platform routers (self-prefixed) ---
app.include_router(customer_success_router)
app.include_router(founder_success_command_router)

# --- Platform Core Directive routers (self-prefixed) ---
app.include_router(platform_core_router)
app.include_router(tax_advisor_router, prefix="/api")
app.include_router(accounting_router, prefix="/api")
app.include_router(quantum_csv_router, prefix="/api")
app.include_router(dataset_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/healthz")
async def healthz() -> JSONResponse:
    checks: dict[str, str] = {}
    warnings: dict[str, str] = {}

    # Redis is optional for readiness unless explicitly required.
    # This prevents ALB/ECS health check loops when Redis is briefly unavailable during startup.
    redis_required = os.getenv("REDIS_REQUIRED", "").strip().lower() in {"1", "true", "yes", "on"}

    # Database check
    try:
        async with async_engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        checks["db"] = "ok"
    except (SQLAlchemyError, OSError, TimeoutError):
        checks["db"] = "unreachable"

    # Redis check
    redis_ok = False
    if settings.redis_url:
        try:
            async with aioredis.from_url(settings.redis_url, socket_connect_timeout=2) as r:
                await r.ping()
            redis_ok = True
            checks["redis"] = "ok"
        except (RedisError, OSError, TimeoutError):
            checks["redis"] = "unreachable"
            warnings["redis"] = "unreachable"
    else:
        checks["redis"] = "not_configured"
        redis_ok = not redis_required
        if redis_required:
            warnings["redis"] = "required_but_not_configured"

    healthy = checks["db"] == "ok" and (redis_ok or not redis_required)

    if not healthy:
        logger.error("HEALTHZ DEGRADED: checks=%s warnings=%s", checks, warnings)

    content: dict[str, object] = {
        "status": "ok" if healthy else "degraded",
        "checks": checks,
        "integrations": settings.integration_state_table(),
    }
    if warnings:
        content["warnings"] = warnings
    return JSONResponse(
        content=content,
        status_code=200 if healthy else 503,
    )


@app.get("/api/healthz")
async def api_healthz() -> JSONResponse:
    return await healthz()


@app.on_event("startup")
def _seed_document_vault_catalog() -> None:
    """Idempotent vault catalog seed — runs once per process start."""
    from core_app.db.session import SessionLocal  # noqa: PLC0415
    from core_app.services.document_vault_service import DocumentVaultService  # noqa: PLC0415

    db = SessionLocal()
    try:
        DocumentVaultService(db).seed_vault_catalog()
        logger.info("vault.catalog.seeded")
    except Exception as exc:  # pragma: no cover — seed failure must never crash startup
        logger.error("vault.catalog.seed_failed error=%s", exc)
    finally:
        db.close()

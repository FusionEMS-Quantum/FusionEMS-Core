from __future__ import annotations

import base64
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    get_current_user,
    require_role,
)
from core_app.billing.ar_aging import compute_ar_aging, compute_revenue_forecast
from core_app.billing.artifacts import store_edi_artifact
from core_app.billing.edi_service import EDIService
from core_app.billing.pre_submission_rules import PreSubmissionRulesEngine
from core_app.billing.validation import BillingValidator
from core_app.billing.x12_835 import parse_835
from core_app.billing.x12_837p import build_837p_ambulance
from core_app.core.config import get_settings
from core_app.documents.s3_storage import default_exports_bucket, presign_get, put_bytes
from core_app.fax.telnyx_service import TelnyxConfig, TelnyxNotConfigured, send_sms
from core_app.integrations.officeally import (
    OfficeAllyClientError,
    OfficeAllySftpConfig,
    poll_claim_status_responses,
    poll_eligibility_responses,
    poll_era_files,
    submit_270_eligibility_inquiry,
    submit_276_claim_status_inquiry,
    submit_837_via_sftp,
)
from core_app.models.billing import Claim as ClaimModel
from core_app.payments.stripe_service import (
    StripeConfig,
    StripeNotConfigured,
    create_patient_checkout_session,
)
from core_app.schemas.auth import CurrentUser
from core_app.schemas.billing import (
    AppealStrategyOut,
    AppealStrategyRequest,
    BillingHealthScoreOut,
    DenialPredictionOut,
    PreSubmissionVerdictOut,
    RuleResultOut,
)
from core_app.services.billing_ai_service import BillingAIService
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])


class SubmitOfficeAllyRequest(BaseModel):
    submitter_id: str = Field(..., description="X12 ISA/GS sender id")
    receiver_id: str = Field(..., description="X12 receiver id")
    billing_npi: str
    billing_tax_id: str
    service_lines: list[dict[str, Any]] = Field(default_factory=list)


class EraImportRequest(BaseModel):
    x12_base64: str


class PaymentLinkRequest(BaseModel):
    account_id: uuid.UUID
    amount_cents: int
    patient_phone: str
    success_url: str
    cancel_url: str


@router.post("/cases/{case_id}/validate")
async def validate_case(
    case_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    validator = BillingValidator(db, tenant_id=current.tenant_id)

    try:
        result = validator.validate_case(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="billing_case_not_found")

    missing = result["missing_docs"]

    # Create missing-doc tasks idempotently: (case_id, doc_type)
    created_tasks: list[dict[str, Any]] = []
    existing = svc.repo("missing_document_tasks").list(
        tenant_id=current.tenant_id, limit=5000
    )
    existing_keys = {
        (t["data"].get("owner_entity_id"), t["data"].get("doc_type")) for t in existing
    }

    for doc_type in missing:
        key = (str(case_id), doc_type)
        if key in existing_keys:
            continue
        task = await svc.create(
            table="missing_document_tasks",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "owner_entity_type": "billing_case",
                "owner_entity_id": str(case_id),
                "doc_type": doc_type,
                "status": "open",
                "created_reason": "billing_prevalidation",
            },
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        created_tasks.append(task)

    payload = {
        "case_id": str(case_id),
        "missing_docs": missing,
        "risk_score": result["risk_score"],
        "risk_flags": result["risk_flags"],
        "created_task_ids": [t["id"] for t in created_tasks],
    }
    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.billing.case.validated",
        tenant_id=current.tenant_id,
        entity_type="billing_case",
        entity_id=str(case_id),
        event_type="BILLING_CASE_VALIDATED",
        payload=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return payload


@router.post("/cases/{case_id}/submit-officeally")
async def submit_officeally(
    case_id: uuid.UUID,
    body: SubmitOfficeAllyRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Generates an 837 artifact, stores it in S3 (exports bucket), records an edi_artifact row,
    and optionally uploads via Office Ally SFTP if configured.
    """
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    case = svc.repo("billing_cases").get(tenant_id=current.tenant_id, record_id=case_id)
    if not case:
        raise HTTPException(status_code=404, detail="billing_case_not_found")

    # Resolve patient + claim info from stored JSON (minimal required fields)
    patient = case["data"].get("patient", {})
    claim = {
        "claim_id": case["data"].get("claim_id", str(case_id)),
        "dos": case["data"].get("dos"),
        "member_id": case["data"].get("member_id", ""),
        "billing_name": case["data"].get("billing_name", "FUSIONEMSQUANTUM"),
        "billing_address1": case["data"].get("billing_address1", "UNKNOWN"),
        "billing_city": case["data"].get("billing_city", "UNKNOWN"),
        "billing_state": case["data"].get("billing_state", "WI"),
        "billing_zip": case["data"].get("billing_zip", "00000"),
        "submitter_name": case["data"].get("submitter_name", "FUSIONEMSQUANTUM"),
        "submitter_contact": case["data"].get("submitter_contact", "BILLING"),
        "submitter_phone": case["data"].get("submitter_phone", "0000000000"),
        "receiver_name": "OFFICEALLY",
    }

    x12_text, env = build_837p_ambulance(
        submitter_id=body.submitter_id,
        receiver_id=body.receiver_id,
        billing_npi=body.billing_npi,
        billing_tax_id=body.billing_tax_id,
        patient=patient,
        claim=claim,
        service_lines=body.service_lines or case["data"].get("service_lines", []),
    )
    file_name = f"837P_{case_id}_{env.isa_control}.x12"
    artifact = store_edi_artifact(
        db=db,
        tenant_id=current.tenant_id,
        artifact_type="837",
        file_name=file_name,
        content=x12_text.encode("utf-8"),
        content_type="text/plain",
    )

    edi_row = await svc.create(
        table="edi_artifacts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "billing_case_id": str(case_id),
            "type": "837P",
            "bucket": artifact["bucket"],
            "key": artifact["key"],
            "isa_control": env.isa_control,
            "gs_control": env.gs_control,
            "st_control": env.st_control,
            "status": "stored",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    # Attempt SFTP upload if configured
    settings = get_settings()
    uploaded_path = None
    if settings.officeally_sftp_host and settings.officeally_sftp_username:
        try:
            cfg = OfficeAllySftpConfig(
                host=settings.officeally_sftp_host,
                port=settings.officeally_sftp_port,
                username=settings.officeally_sftp_username,
                password=settings.officeally_sftp_password,
                remote_dir=settings.officeally_sftp_remote_dir or "/",
            )
            uploaded_path = submit_837_via_sftp(
                cfg=cfg, file_name=file_name, x12_bytes=x12_text.encode("utf-8")
            )
            await svc.update(
                table="edi_artifacts",
                tenant_id=current.tenant_id,
                record_id=uuid.UUID(str(edi_row["id"])),
                actor_user_id=current.user_id,
                expected_version=edi_row["version"],
                patch={"status": "uploaded", "officeally_remote_path": uploaded_path},
                correlation_id=getattr(request.state, "correlation_id", None),
            )
        except OfficeAllyClientError as e:
            await svc.update(
                table="edi_artifacts",
                tenant_id=current.tenant_id,
                record_id=uuid.UUID(str(edi_row["id"])),
                actor_user_id=current.user_id,
                expected_version=edi_row["version"],
                patch={"status": "upload_failed", "error": str(e)},
                correlation_id=getattr(request.state, "correlation_id", None),
            )

    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.billing.edi.837.created",
        tenant_id=current.tenant_id,
        entity_type="edi_artifact",
        entity_id=uuid.UUID(str(edi_row["id"])),
        event_type="EDI_837_CREATED",
        payload={
            "billing_case_id": str(case_id),
            "edi_artifact_id": edi_row["id"],
            "uploaded_path": uploaded_path,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {
        "edi_artifact": edi_row,
        "download_url": artifact["download_url"],
        "officeally_uploaded_path": uploaded_path,
    }


@router.post("/eras/import")
async def import_era(
    body: EraImportRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    try:
        x12 = base64.b64decode(body.x12_base64.encode("utf-8")).decode(
            "utf-8", errors="replace"
        )
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_base64")

    parsed = parse_835(x12)

    # Store ERA artifact to S3 for audit
    bucket = default_exports_bucket()
    if not bucket:
        raise HTTPException(status_code=500, detail="exports_bucket_not_configured")
    key = f"tenants/{current.tenant_id}/edi/835/ERA_{uuid.uuid4()}.x12"
    put_bytes(
        bucket=bucket, key=key, content=x12.encode("utf-8"), content_type="text/plain"
    )
    era_row = await svc.create(
        table="eras",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"bucket": bucket, "key": key, "denials_count": len(parsed["denials"])},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    for d in parsed["denials"]:
        await svc.create(
            table="denials",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "era_id": era_row["id"],
                "claim_id": d["claim_id"],
                "group_code": d["group_code"],
                "reason_code": d["reason_code"],
                "amount": d["amount"],
            },
            correlation_id=getattr(request.state, "correlation_id", None),
        )

    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.billing.era.imported",
        tenant_id=current.tenant_id,
        entity_type="era",
        entity_id=era_row["id"],
        event_type="ERA_IMPORTED",
        payload={"era_id": era_row["id"], "denials_count": len(parsed["denials"])},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {
        "era": era_row,
        "denials": parsed["denials"],
        "download_url": presign_get(bucket=bucket, key=key),
    }


@router.post("/claims/{claim_id}/appeal/generate")
async def generate_appeal(
    claim_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Generates a deterministic appeal letter (text) and stores it as an export artifact.
    """
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    claim = svc.repo("claims").get(tenant_id=current.tenant_id, record_id=claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="claim_not_found")

    bucket = default_exports_bucket()
    if not bucket:
        raise HTTPException(status_code=500, detail="exports_bucket_not_configured")

    denial_reason = claim["data"].get("denial_reason", "Denial reason not recorded.")
    payer = claim["data"].get("payer_name", "PAYER")
    patient = claim["data"].get("patient_name", "PATIENT")
    dos = claim["data"].get("dos", "UNKNOWN")

    letter = (
        f"APPEAL LETTER\n"
        f"Payer: {payer}\n"
        f"Patient: {patient}\n"
        f"Date of Service: {dos}\n"
        f"Claim ID: {claim_id}\n\n"
        f"This letter serves as a formal appeal for the denial of the above claim.\n"
        f"Denial stated: {denial_reason}\n\n"
        f"We request reconsideration and reprocessing of this claim based on documented medical necessity,\n"
        f"appropriate coding, and supporting documentation on file.\n\n"
        f"Sincerely,\nFusionEMS Quantum Billing\n"
    )
    key = f"tenants/{current.tenant_id}/appeals/appeal_{claim_id}.txt"
    put_bytes(
        bucket=bucket,
        key=key,
        content=letter.encode("utf-8"),
        content_type="text/plain",
    )

    appeal_row = await svc.create(
        table="appeals",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "claim_id": str(claim_id),
            "bucket": bucket,
            "key": key,
            "status": "generated",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.billing.appeal.generated",
        tenant_id=current.tenant_id,
        entity_type="appeal",
        entity_id=appeal_row["id"],
        event_type="APPEAL_GENERATED",
        payload={"appeal_id": appeal_row["id"], "claim_id": str(claim_id)},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"appeal": appeal_row, "download_url": presign_get(bucket=bucket, key=key)}


@router.post("/payment/link")
async def create_payment_link(
    body: PaymentLinkRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Stripe-only: creates a hosted checkout session and sends the link via Telnyx SMS.
    Stores ONLY Stripe session IDs/status.
    """
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    settings = get_settings()

    # Stripe session
    try:
        sess = create_patient_checkout_session(
            cfg=StripeConfig(
                secret_key=settings.stripe_secret_key,
                webhook_secret=settings.stripe_webhook_secret or None,
            ),
            amount_cents=body.amount_cents,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            metadata={
                "tenant_id": current.tenant_id,
                "account_id": str(body.account_id),
            },
        )
    except StripeNotConfigured as e:
        raise HTTPException(status_code=500, detail=str(e))

    link_row = await svc.create(
        table="patient_payment_links",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "account_id": str(body.account_id),
            "amount_cents": body.amount_cents,
            "stripe_session_id": sess["id"],
            "status": "created",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    # Send SMS
    try:
        tel = TelnyxConfig(
            api_key=settings.telnyx_api_key,
            messaging_profile_id=settings.telnyx_messaging_profile_id or None,
        )
        send_sms(
            cfg=tel,
            from_number=settings.telnyx_from_number,
            to_number=body.patient_phone,
            text=f"Your payment link: {sess['url']}",
        )
    except TelnyxNotConfigured as e:
        # SMS failure shouldn't delete payment link
        await svc.update(
            table="patient_payment_links",
            tenant_id=current.tenant_id,
            record_id=uuid.UUID(str(link_row["id"])),
            actor_user_id=current.user_id,
            expected_version=link_row["version"],
            patch={"status": "sms_failed", "sms_error": str(e)},
            correlation_id=getattr(request.state, "correlation_id", None),
        )

    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.billing.payment_link.created",
        tenant_id=current.tenant_id,
        entity_type="patient_payment_link",
        entity_id=uuid.UUID(str(link_row["id"])),
        event_type="PAYMENT_LINK_CREATED",
        payload={"payment_link_id": link_row["id"], "stripe_session_id": sess["id"]},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"payment_link": link_row, "stripe": sess}


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    current: CurrentUser = Depends(
        get_current_user
    ),  # protected endpoint; public webhook should be separate path in pricing_router
    db: Session = Depends(db_session_dependency),
):
    raise HTTPException(status_code=400, detail="Use /api/v1/public/webhooks/stripe")


@router.get("/ar-aging")
async def get_ar_aging(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "billing", "admin"])
    report = compute_ar_aging(db, current.tenant_id)
    return {
        "as_of_date": report.as_of_date,
        "total_ar_cents": report.total_ar_cents,
        "total_claims": report.total_claims,
        "avg_days_in_ar": report.avg_days_in_ar,
        "buckets": [
            {"label": b.label, "count": b.count, "total_cents": b.total_cents}
            for b in report.buckets
        ],
        "payer_breakdown": report.payer_breakdown,
    }


@router.get("/revenue-forecast")
async def get_revenue_forecast(
    months: int = 3,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "billing", "admin"])
    return compute_revenue_forecast(db, current.tenant_id, months=months)


# ── Pre-Submission Rules Engine ───────────────────────────────────────────────


@router.post(
    "/claims/{claim_id}/pre-submission-check",
    response_model=PreSubmissionVerdictOut,
)
async def pre_submission_check(
    claim_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Run all pre-submission rules against a claim before 837 generation."""
    require_role(current, ["founder", "billing", "admin"])
    claim = db.query(ClaimModel).filter(
        ClaimModel.id == claim_id,
        ClaimModel.tenant_id == current.tenant_id,
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="claim_not_found")

    engine = PreSubmissionRulesEngine(db)
    verdict = engine.evaluate(claim)
    db.commit()
    return PreSubmissionVerdictOut(
        claim_id=verdict.claim_id,
        submittable=verdict.submittable,
        results=[
            RuleResultOut(
                rule_id=r.rule_id,
                severity=r.severity.value,
                passed=r.passed,
                what_is_wrong=r.what_is_wrong,
                why_it_matters=r.why_it_matters,
                what_to_do_next=r.what_to_do_next,
            )
            for r in verdict.results
        ],
        blocking_count=verdict.blocking_count,
        warning_count=verdict.warning_count,
        checked_at=verdict.checked_at,
    )


# ── Billing AI Endpoints ─────────────────────────────────────────────────────


@router.post(
    "/claims/{claim_id}/denial-risk",
    response_model=DenialPredictionOut,
)
async def denial_risk_prediction(
    claim_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """AI-powered denial risk scoring for a claim."""
    require_role(current, ["founder", "billing", "admin"])
    claim = db.query(ClaimModel).filter(
        ClaimModel.id == claim_id,
        ClaimModel.tenant_id == current.tenant_id,
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="claim_not_found")

    ai = BillingAIService(db)
    prediction = ai.predict_denial_risk(claim)
    return DenialPredictionOut(
        claim_id=prediction.claim_id,
        risk_score=prediction.risk_score,
        risk_level=prediction.risk_level,
        top_risk_factors=prediction.top_risk_factors,
        recommended_actions=prediction.recommended_actions,
        confidence=prediction.confidence,
        model_version=prediction.model_version,
    )


@router.post(
    "/claims/{claim_id}/appeal-strategy",
    response_model=AppealStrategyOut,
)
async def appeal_strategy(
    claim_id: uuid.UUID,
    body: AppealStrategyRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """AI-powered appeal strategy recommendation for a denied claim."""
    require_role(current, ["founder", "billing", "admin"])
    claim = db.query(ClaimModel).filter(
        ClaimModel.id == claim_id,
        ClaimModel.tenant_id == current.tenant_id,
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="claim_not_found")

    ai = BillingAIService(db)
    strategy = ai.recommend_appeal_strategy(claim, body.denial_code)
    return AppealStrategyOut(
        claim_id=strategy.claim_id,
        denial_code=strategy.denial_code,
        recommended_strategy=strategy.recommended_strategy,
        supporting_evidence=strategy.supporting_evidence,
        estimated_success_pct=strategy.estimated_success_pct,
        confidence=strategy.confidence,
        model_version=strategy.model_version,
    )


@router.get(
    "/health-score",
    response_model=BillingHealthScoreOut,
)
async def billing_health_score(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Composite billing health score for the current tenant."""
    require_role(current, ["founder", "billing", "admin"])
    ai = BillingAIService(db)
    score = ai.compute_health_score(current.tenant_id)
    return BillingHealthScoreOut(
        tenant_id=score.tenant_id,
        overall_score=score.overall_score,
        grade=score.grade,
        factors=score.factors,
        recommendations=score.recommendations,
        computed_at=score.computed_at,
    )


# ── Office Ally Clearinghouse: Eligibility / Claim Status / ERA ────────────


class EligibilityInquiryRequest(BaseModel):
    patient_id: str = Field(..., description="Patient UUID")
    member_id: str = Field(..., description="Insurance member ID")
    payer_id: str = Field(default="", description="Payer identifier")
    service_date: str = Field(default="", description="Date of service YYYYMMDD")


class ClaimStatusInquiryRequest(BaseModel):
    claim_id: str = Field(..., description="Claim UUID")
    member_id: str = Field(default="", description="Insurance member ID")
    payer_id: str = Field(default="", description="Payer identifier")


def _get_sftp_config() -> OfficeAllySftpConfig:
    """Build OfficeAllySftpConfig from application settings."""
    settings = get_settings()
    return OfficeAllySftpConfig(
        host=getattr(settings, "OFFICEALLY_SFTP_HOST", ""),
        port=int(getattr(settings, "OFFICEALLY_SFTP_PORT", 22)),
        username=getattr(settings, "OFFICEALLY_SFTP_USER", ""),
        password=getattr(settings, "OFFICEALLY_SFTP_PASS", ""),
        remote_dir=getattr(settings, "OFFICEALLY_SFTP_DIR", "/outbound"),
        inbound_dir=getattr(settings, "OFFICEALLY_SFTP_INBOUND_DIR", "/inbound"),
        era_dir=getattr(settings, "OFFICEALLY_SFTP_ERA_DIR", "/era"),
        eligibility_dir=getattr(settings, "OFFICEALLY_SFTP_ELIGIBILITY_DIR", "/eligibility"),
        claim_status_dir=getattr(settings, "OFFICEALLY_SFTP_CLAIM_STATUS_DIR", "/claim_status"),
    )


@router.post("/eligibility/inquire")
async def submit_eligibility_inquiry(
    body: EligibilityInquiryRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Submit a 270 Eligibility Inquiry to the clearinghouse via SFTP."""
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    # Build minimal 270 X12 envelope
    isa_control = str(uuid.uuid4().int)[:9].zfill(9)
    x12_lines = [
        f"ISA*00*          *00*          *ZZ*FUSIONEMS      *ZZ*OFFICEALLY     *000000*0000*^*00501*{isa_control}*0*P*:~",
        "GS*HS*FUSIONEMS*OFFICEALLY*20250101*0000*1*X*005010X279A1~",
        "ST*270*0001*005010X279A1~",
        "BHT*0022*13*ELG001*20250101*0000~",
        "HL*1**20*1~",
        f"NM1*PR*2*{body.payer_id or 'UNKNOWN'}*****PI*{body.payer_id or 'UNKNOWN'}~",
        "HL*2*1*22*1~",
        "NM1*1P*2*FUSIONEMS*****XX*0000000000~",
        "HL*3*2*23*0~",
        f"NM1*IL*1*PATIENT*****MI*{body.member_id}~",
        f"DTP*291*D8*{body.service_date or '20250101'}~",
        "EQ*30~",
        "SE*12*0001~",
        "GE*1*1~",
        f"IEA*1*{isa_control}~",
    ]
    x12_text = "\n".join(x12_lines)
    x12_bytes = x12_text.encode("utf-8")
    file_name = f"270_{current.tenant_id}_{body.patient_id}_{isa_control}.x12"

    cfg = _get_sftp_config()
    try:
        remote_path = submit_270_eligibility_inquiry(
            cfg=cfg, file_name=file_name, x12_bytes=x12_bytes,
        )
    except OfficeAllyClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Track the inquiry in the domination table
    record = await svc.create(
        table="edi_artifacts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "entity_type": "eligibility_inquiry",
            "patient_id": body.patient_id,
            "member_id": body.member_id,
            "payer_id": body.payer_id,
            "file_type": "270",
            "file_name": file_name,
            "remote_path": remote_path,
            "status": "submitted",
            "submitted_at": str(uuid.uuid4())[:8],
        },
    )
    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.billing.eligibility.submitted",
        tenant_id=current.tenant_id,
        entity_id=str(record["id"]),
        entity_type="eligibility_inquiry",
        event_type="ELIGIBILITY_INQUIRY_SUBMITTED",
        payload={"patient_id": body.patient_id, "file_name": file_name},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"inquiry_id": str(record["id"]), "file_name": file_name, "status": "submitted"}


@router.post("/eligibility/poll")
async def poll_eligibility(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Poll clearinghouse for 271 Eligibility Response files via SFTP."""
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    cfg = _get_sftp_config()

    try:
        files = poll_eligibility_responses(cfg=cfg, max_files=50)
    except OfficeAllyClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    ingested: list[dict[str, Any]] = []
    for f in files:
        record = await svc.create(
            table="edi_artifacts",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "entity_type": "eligibility_response",
                "file_type": "271",
                "file_name": f["filename"],
                "content_preview": f["content"][:500],
                "size_bytes": f["size_bytes"],
                "status": "ingested",
            },
        )
        ingested.append({"artifact_id": str(record["id"]), "filename": f["filename"]})

    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.billing.eligibility.polled",
        tenant_id=current.tenant_id,
        entity_id=None,
        entity_type="eligibility_response",
        event_type="ELIGIBILITY_RESPONSES_POLLED",
        payload={"file_count": len(ingested)},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"polled_count": len(ingested), "files": ingested}


@router.post("/claims/status-inquiry")
async def submit_claim_status_inquiry(
    body: ClaimStatusInquiryRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Submit a 276 Claim Status Inquiry to the clearinghouse via SFTP."""
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    isa_control = str(uuid.uuid4().int)[:9].zfill(9)
    x12_lines = [
        f"ISA*00*          *00*          *ZZ*FUSIONEMS      *ZZ*OFFICEALLY     *000000*0000*^*00501*{isa_control}*0*P*:~",
        "GS*HN*FUSIONEMS*OFFICEALLY*20250101*0000*1*X*005010X212~",
        "ST*276*0001*005010X212~",
        "BHT*0010*13*CSI001*20250101*0000~",
        "HL*1**20*1~",
        f"NM1*PR*2*{body.payer_id or 'UNKNOWN'}*****PI*{body.payer_id or 'UNKNOWN'}~",
        "HL*2*1*21*1~",
        "NM1*41*2*FUSIONEMS*****46*000000000~",
        "HL*3*2*19*0~",
        f"NM1*IL*1*PATIENT*****MI*{body.member_id or 'UNKNOWN'}~",
        f"TRN*1*{body.claim_id}*FUSIONEMS~",
        f"REF*BLT*{body.claim_id}~",
        "SE*12*0001~",
        "GE*1*1~",
        f"IEA*1*{isa_control}~",
    ]
    x12_text = "\n".join(x12_lines)
    x12_bytes = x12_text.encode("utf-8")
    file_name = f"276_{current.tenant_id}_{body.claim_id}_{isa_control}.x12"

    cfg = _get_sftp_config()
    try:
        remote_path = submit_276_claim_status_inquiry(
            cfg=cfg, file_name=file_name, x12_bytes=x12_bytes,
        )
    except OfficeAllyClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    record = await svc.create(
        table="edi_artifacts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "entity_type": "claim_status_inquiry",
            "claim_id": body.claim_id,
            "file_type": "276",
            "file_name": file_name,
            "remote_path": remote_path,
            "status": "submitted",
        },
    )
    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.billing.claim-status.submitted",
        tenant_id=current.tenant_id,
        entity_id=str(record["id"]),
        entity_type="claim_status_inquiry",
        event_type="CLAIM_STATUS_INQUIRY_SUBMITTED",
        payload={"claim_id": body.claim_id, "file_name": file_name},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"inquiry_id": str(record["id"]), "file_name": file_name, "status": "submitted"}


@router.post("/claims/status-poll")
async def poll_claim_status(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Poll clearinghouse for 277 Claim Status Response files, ingest via EDIService."""
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    edi_svc = EDIService(db, publisher, current.tenant_id)
    cfg = _get_sftp_config()

    try:
        files = poll_claim_status_responses(cfg=cfg, max_files=50)
    except OfficeAllyClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    results: list[dict[str, Any]] = []
    for f in files:
        parsed = edi_svc.parse_277(f["content"])
        record = await svc.create(
            table="edi_artifacts",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "entity_type": "claim_status_response",
                "file_type": "277",
                "file_name": f["filename"],
                "size_bytes": f["size_bytes"],
                "parsed_claim_ids": parsed.get("claim_ids", []),
                "parsed_status_codes": parsed.get("status_codes", []),
                "status": "ingested",
            },
        )
        results.append({
            "artifact_id": str(record["id"]),
            "filename": f["filename"],
            "claim_ids": parsed.get("claim_ids", []),
            "status_codes": parsed.get("status_codes", []),
        })

    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.billing.claim-status.polled",
        tenant_id=current.tenant_id,
        entity_id=None,
        entity_type="claim_status_response",
        event_type="CLAIM_STATUS_RESPONSES_POLLED",
        payload={"file_count": len(results)},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"polled_count": len(results), "results": results}


@router.post("/eras/poll")
async def poll_eras(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Poll clearinghouse for 835 ERA files, parse and ingest via EDIService."""
    require_role(current, ["founder", "billing", "admin"])
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    edi_svc = EDIService(db, publisher, current.tenant_id)
    cfg = _get_sftp_config()

    try:
        files = poll_era_files(cfg=cfg, max_files=50)
    except OfficeAllyClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    results: list[dict[str, Any]] = []
    for f in files:
        parsed = await edi_svc.parse_835(f["content"])
        record = await svc.create(
            table="edi_artifacts",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            data={
                "entity_type": "era_remittance",
                "file_type": "835",
                "file_name": f["filename"],
                "size_bytes": f["size_bytes"],
                "payment_amount": parsed.get("payment_amount", 0),
                "check_number": parsed.get("check_number", ""),
                "claim_count": len(parsed.get("claims", [])),
                "status": "ingested",
            },
        )
        results.append({
            "artifact_id": str(record["id"]),
            "filename": f["filename"],
            "payment_amount": parsed.get("payment_amount", 0),
            "check_number": parsed.get("check_number", ""),
            "claim_count": len(parsed.get("claims", [])),
        })

    publisher.publish_sync(
        topic=f"tenant.{current.tenant_id}.billing.era.polled",
        tenant_id=current.tenant_id,
        entity_id=None,
        entity_type="era_remittance",
        event_type="ERA_FILES_POLLED",
        payload={"file_count": len(results)},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"polled_count": len(results), "results": results}

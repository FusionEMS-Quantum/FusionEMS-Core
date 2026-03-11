"""
Founder Communications Router
================================
All endpoints require founder-only authenticated session.
Prefix: /v1/founder/comms
Tags:   Founder Communications
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_app.api.dependencies import require_founder_only_audited
from core_app.db.session import get_db_session as db_session_dependency
from core_app.schemas.auth import CurrentUser
from core_app.services.founder_communications_service import FounderCommunicationsService

router = APIRouter(prefix="/v1/founder/comms", tags=["Founder Communications"])

_founder_guard = require_founder_only_audited()


def _svc(db: Session) -> FounderCommunicationsService:
    return FounderCommunicationsService(db)


# ── Request/Response schemas ──────────────────────────────────────────────────

class InitiateCallRequest(BaseModel):
    to_number: str = Field(..., min_length=7, max_length=20)
    correlation_id: str | None = None


class SendSMSRequest(BaseModel):
    to_number: str = Field(..., min_length=7, max_length=20)
    body: str = Field(..., min_length=1, max_length=1600)
    display_name: str | None = None
    correlation_id: str | None = None


class SendFaxRequest(BaseModel):
    to_number: str = Field(..., min_length=7, max_length=20)
    media_url: str = Field(..., min_length=10)
    subject: str | None = None
    correlation_id: str | None = None


class SendEmailRequest(BaseModel):
    to_email: str = Field(..., min_length=5, max_length=254)
    subject: str = Field(..., min_length=1, max_length=256)
    body_html: str = Field(..., min_length=1)
    correlation_id: str | None = None


class RecipientAddress(BaseModel):
    name: str
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str = Field(..., min_length=2, max_length=2)
    zip: str = Field(..., min_length=5, max_length=10)


class SendPrintMailRequest(BaseModel):
    recipient_address: RecipientAddress
    body_html: str = Field(..., min_length=1)
    subject_line: str | None = None
    correlation_id: str | None = None


class DispatchAlertRequest(BaseModel):
    channel: str = Field(..., pattern="^(email|sms|voice|audit_log)$")
    severity: str = Field(..., pattern="^(info|warning|critical)$")
    subject: str = Field(..., min_length=1, max_length=256)
    message: str = Field(..., min_length=1)
    source_system: str | None = None
    correlation_id: str | None = None


class UpsertAudioConfigRequest(BaseModel):
    alert_type: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    audio_url: str | None = None
    tts_script: str | None = None
    is_enabled: bool = True
    priority: int = 0


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    channel: str = Field(..., pattern="^(email|sms|fax|voice|print_mail)$")
    body_template: str = Field(..., min_length=1)
    subject: str | None = None
    variables: list[dict[str, Any]] | None = None


class RenderTemplateRequest(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)


class AIDraftRequest(BaseModel):
    channel: str = Field(..., pattern="^(email|sms|fax|voice|print_mail)$")
    context: str = Field(..., min_length=10, max_length=4000)
    tone: str = Field(default="professional", pattern="^(professional|formal|concise|urgent)$")


class CreateBAATemplateRequest(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=128)
    body_html: str = Field(..., min_length=1)
    version_tag: str = "v1.0"
    variables: list[dict[str, Any]] | None = None
    effective_date: str | None = None
    is_current: bool = False
    notes: str | None = None


class RenderBAARequest(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)


class CreateWisconsinTemplateRequest(BaseModel):
    doc_type: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    body_html: str = Field(..., min_length=1)
    version_tag: str = "v1.0"
    variables: list[dict[str, Any]] | None = None
    effective_date: str | None = None
    is_current: bool = False
    wi_statute_reference: str | None = None
    notes: str | None = None


class RenderWisconsinRequest(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)


# ── VOICE ─────────────────────────────────────────────────────────────────────

@router.post("/calls")
def initiate_call(
    body: InitiateCallRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).initiate_outbound_call(body.to_number, correlation_id=body.correlation_id)


@router.get("/calls")
def list_calls(
    limit: int = 50,
    offset: int = 0,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> list[dict[str, Any]]:
    return _svc(db).list_calls(limit=min(limit, 200), offset=offset)


@router.get("/calls/{call_id}")
def get_call(
    call_id: str,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    result = _svc(db).get_call(call_id)
    if not result:
        from fastapi import HTTPException  # noqa: PLC0415
        raise HTTPException(status_code=404, detail="Call record not found")
    return result


# ── SMS ───────────────────────────────────────────────────────────────────────

@router.post("/sms")
def send_sms(
    body: SendSMSRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).send_sms(
        body.to_number,
        body.body,
        display_name=body.display_name,
        correlation_id=body.correlation_id,
    )


@router.get("/sms/threads")
def list_sms_threads(
    archived: bool = False,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> list[dict[str, Any]]:
    return _svc(db).list_sms_threads(archived=archived)


@router.get("/sms/threads/{thread_id}")
def get_sms_thread(
    thread_id: str,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    result = _svc(db).get_sms_thread(thread_id)
    if not result:
        from fastapi import HTTPException  # noqa: PLC0415
        raise HTTPException(status_code=404, detail="SMS thread not found")
    return result


# ── FAX ───────────────────────────────────────────────────────────────────────

@router.post("/fax")
def send_fax(
    body: SendFaxRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).send_fax(
        body.to_number,
        body.media_url,
        subject=body.subject,
        correlation_id=body.correlation_id,
    )


@router.get("/fax")
def list_faxes(
    limit: int = 50,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> list[dict[str, Any]]:
    return _svc(db).list_faxes(limit=min(limit, 200))


# ── EMAIL ─────────────────────────────────────────────────────────────────────

@router.post("/email")
def send_email(
    body: SendEmailRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).send_email(
        body.to_email,
        body.subject,
        body.body_html,
        correlation_id=body.correlation_id,
    )


# ── PRINT / MAIL ──────────────────────────────────────────────────────────────

@router.post("/print-mail")
def send_print_mail(
    body: SendPrintMailRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).send_print_mail(
        body.recipient_address.model_dump(exclude_none=True),
        body.body_html,
        subject_line=body.subject_line,
        correlation_id=body.correlation_id,
    )


@router.get("/print-mail")
def list_print_mail(
    limit: int = 50,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> list[dict[str, Any]]:
    return _svc(db).list_print_mail(limit=min(limit, 200))


# ── ALERTS ────────────────────────────────────────────────────────────────────

@router.post("/alerts")
def dispatch_alert(
    body: DispatchAlertRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).dispatch_alert(
        body.channel,
        body.severity,
        body.subject,
        body.message,
        source_system=body.source_system,
        correlation_id=body.correlation_id,
    )


@router.get("/alerts")
def list_alerts(
    unacknowledged_only: bool = False,
    limit: int = 100,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> list[dict[str, Any]]:
    return _svc(db).list_alerts(unacknowledged_only=unacknowledged_only, limit=min(limit, 500))


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).acknowledge_alert(alert_id)


# ── AUDIO CONFIG ──────────────────────────────────────────────────────────────

@router.get("/audio-config")
def list_audio_configs(
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> list[dict[str, Any]]:
    return _svc(db).list_audio_configs()


@router.put("/audio-config")
def upsert_audio_config(
    body: UpsertAudioConfigRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).upsert_audio_config(
        body.alert_type,
        body.display_name,
        audio_url=body.audio_url,
        tts_script=body.tts_script,
        is_enabled=body.is_enabled,
        priority=body.priority,
    )


# ── TEMPLATES ─────────────────────────────────────────────────────────────────

@router.get("/templates")
def list_templates(
    channel: str | None = None,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> list[dict[str, Any]]:
    return _svc(db).list_templates(channel=channel)


@router.get("/templates/{template_id}")
def get_template(
    template_id: str,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    result = _svc(db).get_template(template_id)
    if not result:
        from fastapi import HTTPException  # noqa: PLC0415
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.post("/templates")
def create_template(
    body: CreateTemplateRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).create_template(
        body.name,
        body.channel,
        body.body_template,
        subject=body.subject,
        variables=body.variables,
    )


@router.post("/templates/{template_id}/render")
def render_template(
    template_id: str,
    body: RenderTemplateRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, str]:
    return _svc(db).render_template(template_id, body.variables)


# ── AI DRAFT ─────────────────────────────────────────────────────────────────

@router.post("/ai/draft")
def ai_draft_message(
    body: AIDraftRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).ai_draft_message(body.channel, body.context, tone=body.tone)


# ── BAA TEMPLATES ─────────────────────────────────────────────────────────────

@router.get("/baa-templates")
def list_baa_templates(
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> list[dict[str, Any]]:
    return _svc(db).list_baa_templates()


@router.get("/baa-templates/{template_id}")
def get_baa_template(
    template_id: str,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    result = _svc(db).get_baa_template(template_id)
    if not result:
        from fastapi import HTTPException  # noqa: PLC0415
        raise HTTPException(status_code=404, detail="BAA template not found")
    return result


@router.post("/baa-templates")
def create_baa_template(
    body: CreateBAATemplateRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).create_baa_template(
        body.template_name,
        body.body_html,
        version_tag=body.version_tag,
        variables=body.variables,
        effective_date=body.effective_date,
        is_current=body.is_current,
        notes=body.notes,
    )


@router.post("/baa-templates/{template_id}/render")
def render_baa(
    template_id: str,
    body: RenderBAARequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, str]:
    return _svc(db).render_baa(template_id, body.variables)


# ── WISCONSIN DOC TEMPLATES ───────────────────────────────────────────────────

@router.get("/wisconsin-docs")
def list_wisconsin_templates(
    doc_type: str | None = None,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> list[dict[str, Any]]:
    return _svc(db).list_wisconsin_templates(doc_type=doc_type)


@router.post("/wisconsin-docs")
def create_wisconsin_template(
    body: CreateWisconsinTemplateRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).create_wisconsin_template(
        body.doc_type,
        body.display_name,
        body.body_html,
        version_tag=body.version_tag,
        variables=body.variables,
        effective_date=body.effective_date,
        is_current=body.is_current,
        wi_statute_reference=body.wi_statute_reference,
        notes=body.notes,
    )


@router.post("/wisconsin-docs/{template_id}/render")
def render_wisconsin_doc(
    template_id: str,
    body: RenderWisconsinRequest,
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, str]:
    return _svc(db).render_wisconsin_doc(template_id, body.variables)

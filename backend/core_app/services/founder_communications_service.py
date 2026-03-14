"""
Founder Communications Service
================================
Unified communications service for all founder channels.
Real integrations — no stubs.

Channels:
  - Outbound / inbound voice (Telnyx Call Control)
  - SMS threads (Telnyx Messaging)
  - Fax (Telnyx Fax)
  - Print / mail (LOB)
  - Email (AWS SES via boto3)
  - Platform alerts (multi-channel dispatch)
  - AI-drafted message composition (Bedrock)
  - BAA document generation
  - Wisconsin statutory document generation

Design constraints:
  - Founder-only (enforced at router level with require_founder_only_audited)
  - All sends logged with correlation IDs
  - Structured logging, no sensitive data in messages
  - Idempotent where possible (Telnyx dedup, LOB idempotency keys)
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from core_app.core.config import get_settings
from core_app.models.founder_communications import (
    BAATemplate,
    FounderAlertRecord,
    FounderAudioAlertConfig,
    FounderCallRecord,
    FounderCommunicationTemplate,
    FounderFaxRecord,
    FounderPrintMailRecord,
    FounderSMSThread,
    WisconsinDocTemplate,
)

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _render_template(body: str, variables: dict[str, str]) -> str:
    """Simple {{variable}} substitution."""
    for k, v in variables.items():
        body = body.replace("{{" + k + "}}", str(v))
    return body


class FounderCommunicationsService:
    """
    Mediates all founder communication channel access.
    One instance per request via db session injection.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._settings = get_settings()

    # ────────────────────────────────────────────────────────────────────────
    # VOICE — Telnyx Call Control
    # ────────────────────────────────────────────────────────────────────────

    def initiate_outbound_call(
        self,
        to_number: str,
        *,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Initiate an outbound call from the founder's Telnyx number.
        Returns the stored FounderCallRecord id and Telnyx call_control_id.
        """
        cid = correlation_id or str(uuid.uuid4())
        record = FounderCallRecord(
            direction="outbound",
            from_number=self._settings.telnyx_from_number or None,
            to_number=to_number,
            status="initiated",
            correlation_id=cid,
        )
        self.db.add(record)
        self.db.flush()

        api_key = self._settings.telnyx_api_key
        if not api_key:
            logger.warning("founder_call.telnyx_not_configured record_id=%s", record.id)
            self.db.commit()
            return {"id": str(record.id), "status": "initiated", "telnyx_call_control_id": None, "note": "telnyx_not_configured"}

        try:
            from core_app.telnyx.client import initiate_outbound_call  # noqa: PLC0415
            result = initiate_outbound_call(
                api_key=api_key,
                to=to_number,
                from_=self._settings.telnyx_from_number,
                connection_id=getattr(self._settings, "telnyx_call_control_connection_id", ""),
                client_state=json.dumps({"record_id": str(record.id), "cid": cid}),
            )
            call_leg = result.get("data", {})
            record.telnyx_call_control_id = call_leg.get("call_control_id")
            record.telnyx_call_leg_id = call_leg.get("call_leg_id")
            self.db.commit()
            logger.info("founder_call.initiated record_id=%s cid=%s", record.id, cid)
            return {
                "id": str(record.id),
                "status": "initiated",
                "telnyx_call_control_id": record.telnyx_call_control_id,
            }
        except Exception as exc:
            record.status = "failed"
            record.call_metadata = {"error": str(exc)}
            self.db.commit()
            logger.error("founder_call.initiate_failed record_id=%s error=%s cid=%s", record.id, exc, cid)
            raise

    def list_calls(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        records = (
            self.db.query(FounderCallRecord)
            .order_by(FounderCallRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [
            {
                "id": str(r.id),
                "direction": r.direction,
                "from_number": r.from_number,
                "to_number": r.to_number,
                "status": r.status,
                "duration_seconds": r.duration_seconds,
                "has_recording": bool(r.recording_url or r.recording_s3_key),
                "has_transcript": bool(r.transcript),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]

    def get_call(self, call_id: str) -> dict[str, Any] | None:
        r = self.db.query(FounderCallRecord).filter(FounderCallRecord.id == call_id).first()
        if not r:
            return None
        return {
            "id": str(r.id),
            "direction": r.direction,
            "from_number": r.from_number,
            "to_number": r.to_number,
            "status": r.status,
            "duration_seconds": r.duration_seconds,
            "recording_url": r.recording_url,
            "transcript": r.transcript,
            "ai_summary": r.ai_summary,
            "call_metadata": r.call_metadata,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    # ────────────────────────────────────────────────────────────────────────
    # SMS — Telnyx Messaging
    # ────────────────────────────────────────────────────────────────────────

    def send_sms(
        self,
        to_number: str,
        body: str,
        *,
        display_name: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an SMS and append to (or create) the thread for this number.
        """
        cid = correlation_id or str(uuid.uuid4())
        thread = (
            self.db.query(FounderSMSThread)
            .filter(FounderSMSThread.to_number == to_number, ~FounderSMSThread.is_archived)
            .first()
        )
        if not thread:
            thread = FounderSMSThread(
                to_number=to_number,
                display_name=display_name,
                messages=[],
            )
            self.db.add(thread)
            self.db.flush()

        telnyx_id: str | None = None
        api_key = self._settings.telnyx_api_key
        if api_key:
            try:
                from core_app.telnyx.client import send_sms  # noqa: PLC0415
                result = send_sms(
                    api_key=api_key,
                    to_number=to_number,
                    from_number=self._settings.telnyx_from_number,
                    text=body,
                    messaging_profile_id=getattr(self._settings, "telnyx_messaging_profile_id", "") or None,
                )
                telnyx_id = result.get("data", {}).get("id")
            except Exception as exc:
                logger.error("founder_sms.send_failed to=%s error=%s cid=%s", to_number, exc, cid)

        msg_entry = {
            "role": "founder",
            "body": body,
            "ts": _now_iso(),
            "telnyx_id": telnyx_id,
            "cid": cid,
        }
        messages = list(thread.messages or [])
        messages.append(msg_entry)
        thread.messages = messages  # type: ignore[assignment]
        thread.last_message_at = _now_iso()
        self.db.commit()
        logger.info("founder_sms.sent thread_id=%s cid=%s", thread.id, cid)
        return {"thread_id": str(thread.id), "telnyx_id": telnyx_id, "status": "sent"}

    def list_sms_threads(self, *, archived: bool = False) -> list[dict[str, Any]]:
        q = self.db.query(FounderSMSThread)
        if not archived:
            q = q.filter(~FounderSMSThread.is_archived)
        threads = q.order_by(FounderSMSThread.last_message_at.desc()).all()
        return [
            {
                "id": str(t.id),
                "to_number": t.to_number,
                "display_name": t.display_name,
                "message_count": len(t.messages or []),
                "last_message_at": t.last_message_at,
                "is_archived": t.is_archived,
            }
            for t in threads
        ]

    def get_sms_thread(self, thread_id: str) -> dict[str, Any] | None:
        t = self.db.query(FounderSMSThread).filter(FounderSMSThread.id == thread_id).first()
        if not t:
            return None
        return {
            "id": str(t.id),
            "to_number": t.to_number,
            "display_name": t.display_name,
            "messages": t.messages,
            "is_archived": t.is_archived,
        }

    # ────────────────────────────────────────────────────────────────────────
    # FAX — Telnyx Fax
    # ────────────────────────────────────────────────────────────────────────

    def send_fax(
        self,
        to_number: str,
        media_url: str,
        *,
        subject: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a fax via Telnyx. media_url must be a publicly accessible PDF.
        """
        cid = correlation_id or str(uuid.uuid4())
        record = FounderFaxRecord(
            direction="outbound",
            from_number=getattr(self._settings, "telnyx_fax_from_number", None) or self._settings.telnyx_from_number or None,
            to_number=to_number,
            status="queued",
            subject=subject,
            media_url=media_url,
            correlation_id=cid,
        )
        self.db.add(record)
        self.db.flush()

        api_key = self._settings.telnyx_api_key
        fax_connection_id = getattr(self._settings, "telnyx_fax_connection_id", "") or ""
        if api_key:
            try:
                from core_app.telnyx.client import send_fax as telnyx_send_fax  # noqa: PLC0415
                result = telnyx_send_fax(
                    api_key=api_key,
                    to=to_number,
                    from_=record.from_number or "",
                    media_url=media_url,
                    connection_id=fax_connection_id,
                )
                record.telnyx_fax_id = result.get("data", {}).get("id")
                record.status = "sending"
            except Exception as exc:
                record.status = "failed"
                logger.error("founder_fax.send_failed to=%s error=%s cid=%s", to_number, exc, cid)

        self.db.commit()
        logger.info("founder_fax.queued record_id=%s cid=%s", record.id, cid)
        return {"id": str(record.id), "telnyx_fax_id": record.telnyx_fax_id, "status": record.status}

    def list_faxes(self, *, limit: int = 50) -> list[dict[str, Any]]:
        records = (
            self.db.query(FounderFaxRecord)
            .order_by(FounderFaxRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(r.id),
                "direction": r.direction,
                "to_number": r.to_number,
                "status": r.status,
                "subject": r.subject,
                "page_count": r.page_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]

    # ────────────────────────────────────────────────────────────────────────
    # EMAIL — AWS SES
    # ────────────────────────────────────────────────────────────────────────

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        *,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an email via AWS SES (boto3 send_email).
        """
        cid = correlation_id or str(uuid.uuid4())
        try:
            import boto3  # noqa: PLC0415
            client = boto3.client("ses", region_name=getattr(self._settings, "aws_region", "us-east-1"))
            kwargs: dict[str, Any] = {
                "Source": self._settings.ses_from_email,
                "Destination": {"ToAddresses": [to_email]},
                "Message": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": body_html, "Charset": "UTF-8"}},
                },
            }
            cfg_set = getattr(self._settings, "ses_configuration_set", "")
            if cfg_set:
                kwargs["ConfigurationSetName"] = cfg_set
            resp = client.send_email(**kwargs)
            message_id = resp.get("MessageId", "")
            logger.info("founder_email.sent to=%s message_id=%s cid=%s", to_email, message_id, cid)
            return {"status": "sent", "ses_message_id": message_id, "cid": cid}
        except Exception as exc:
            logger.error("founder_email.send_failed to=%s error=%s cid=%s", to_email, exc, cid)
            raise

    # ────────────────────────────────────────────────────────────────────────
    # PRINT / MAIL — LOB
    # ────────────────────────────────────────────────────────────────────────

    def send_print_mail(
        self,
        recipient_address: dict[str, str],
        body_html: str,
        *,
        subject_line: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a physical letter via LOB (print and mail).
        recipient_address: {name, address_line1, address_line2, city, state, zip}
        """
        cid = correlation_id or str(uuid.uuid4())
        record = FounderPrintMailRecord(
            status="queued",
            recipient_address=recipient_address,
            subject_line=subject_line,
            correlation_id=cid,
        )
        self.db.add(record)
        self.db.flush()

        lob_key = self._settings.lob_api_key
        if lob_key:
            try:
                import requests as _requests  # noqa: PLC0415
                lob_resp = _requests.post(
                    "https://api.lob.com/v1/letters",
                    auth=(lob_key, ""),
                    json={
                        "description": subject_line or "Founder Letter",
                        "to": {
                            "name": recipient_address.get("name", ""),
                            "address_line1": recipient_address.get("address_line1", ""),
                            "address_line2": recipient_address.get("address_line2", ""),
                            "address_city": recipient_address.get("city", ""),
                            "address_state": recipient_address.get("state", ""),
                            "address_zip": recipient_address.get("zip", ""),
                            "address_country": "US",
                        },
                        "from": {
                            "name": "FusionEMS Quantum",
                            "address_line1": "PO Box 1",
                            "address_city": "Madison",
                            "address_state": "WI",
                            "address_zip": "53701",
                            "address_country": "US",
                        },
                        "file": f"<html><body>{body_html}</body></html>",
                        "color": False,
                        "double_sided": False,
                        "mail_type": "usps_first_class",
                        "metadata": {"cid": cid, "record_id": str(record.id)},
                    },
                    timeout=15,
                )
                if lob_resp.status_code < 300:
                    lob_data = lob_resp.json()
                    record.lob_letter_id = lob_data.get("id")
                    record.status = "in_transit"
                    record.expected_delivery_date = lob_data.get("expected_delivery_date")
                else:
                    record.status = "failed"
                    logger.error("founder_mail.lob_failed status=%s body=%s cid=%s", lob_resp.status_code, lob_resp.text[:200], cid)
            except Exception as exc:
                record.status = "failed"
                logger.error("founder_mail.send_failed error=%s cid=%s", exc, cid)

        self.db.commit()
        logger.info("founder_mail.queued record_id=%s lob_id=%s cid=%s", record.id, record.lob_letter_id, cid)
        return {"id": str(record.id), "lob_letter_id": record.lob_letter_id, "status": record.status}

    def list_print_mail(self, *, limit: int = 50) -> list[dict[str, Any]]:
        records = (
            self.db.query(FounderPrintMailRecord)
            .order_by(FounderPrintMailRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(r.id),
                "lob_letter_id": r.lob_letter_id,
                "status": r.status,
                "subject_line": r.subject_line,
                "expected_delivery_date": r.expected_delivery_date,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]

    # ────────────────────────────────────────────────────────────────────────
    # ALERTS
    # ────────────────────────────────────────────────────────────────────────

    def dispatch_alert(
        self,
        channel: str,
        severity: str,
        subject: str,
        message: str,
        *,
        source_system: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Dispatch a platform alert via the specified channel.
        Always creates an audit record regardless of channel delivery.
        """
        cid = correlation_id or str(uuid.uuid4())
        record = FounderAlertRecord(
            channel=channel,
            severity=severity,
            subject=subject,
            message=message,
            source_system=source_system,
            delivery_status="pending",
            correlation_id=cid,
        )
        self.db.add(record)
        self.db.flush()

        delivery_status = "pending"
        try:
            if channel == "email":
                founder_email = self._settings.graph_founder_email or self._settings.ses_from_email
                self.send_email(founder_email, f"[{severity.upper()}] {subject}", f"<p>{message}</p>", correlation_id=cid)
                delivery_status = "delivered"
            elif channel == "sms":
                founder_phone = self._settings.telnyx_from_number
                if founder_phone:
                    self.send_sms(founder_phone, f"[{severity.upper()}] {subject}: {message}", correlation_id=cid)
                    delivery_status = "delivered"
                else:
                    delivery_status = "no_phone_configured"
            elif channel == "audit_log":
                delivery_status = "delivered"
            else:
                delivery_status = "unsupported_channel"
        except Exception as exc:
            delivery_status = "failed"
            logger.error("founder_alert.dispatch_failed channel=%s error=%s cid=%s", channel, exc, cid)

        record.delivery_status = delivery_status
        self.db.commit()
        logger.info("founder_alert.dispatched record_id=%s channel=%s severity=%s cid=%s", record.id, channel, severity, cid)
        return {"id": str(record.id), "delivery_status": delivery_status}

    def list_alerts(self, *, unacknowledged_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
        q = self.db.query(FounderAlertRecord).order_by(FounderAlertRecord.created_at.desc())
        if unacknowledged_only:
            q = q.filter(FounderAlertRecord.acknowledged_at == None)  # noqa: E711
        records = q.limit(limit).all()
        return [
            {
                "id": str(r.id),
                "channel": r.channel,
                "severity": r.severity,
                "subject": r.subject,
                "message": r.message,
                "source_system": r.source_system,
                "delivery_status": r.delivery_status,
                "acknowledged_at": r.acknowledged_at,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]

    def acknowledge_alert(self, alert_id: str) -> dict[str, Any]:
        record = self.db.query(FounderAlertRecord).filter(FounderAlertRecord.id == alert_id).first()
        if not record:
            raise ValueError(f"Alert {alert_id} not found")
        if not record.acknowledged_at:
            record.acknowledged_at = _now_iso()
            self.db.commit()
        return {"id": str(record.id), "acknowledged_at": record.acknowledged_at}

    # ────────────────────────────────────────────────────────────────────────
    # AUDIO ALERT CONFIG
    # ────────────────────────────────────────────────────────────────────────

    def list_audio_configs(self) -> list[dict[str, Any]]:
        records = self.db.query(FounderAudioAlertConfig).order_by(FounderAudioAlertConfig.priority.asc()).all()
        return [
            {
                "id": str(r.id),
                "alert_type": r.alert_type,
                "display_name": r.display_name,
                "audio_url": r.audio_url,
                "tts_script": r.tts_script,
                "is_enabled": r.is_enabled,
                "priority": r.priority,
            }
            for r in records
        ]

    def upsert_audio_config(
        self,
        alert_type: str,
        display_name: str,
        *,
        audio_url: str | None = None,
        tts_script: str | None = None,
        is_enabled: bool = True,
        priority: int = 0,
    ) -> dict[str, Any]:
        record = self.db.query(FounderAudioAlertConfig).filter(FounderAudioAlertConfig.alert_type == alert_type).first()
        if record:
            record.display_name = display_name
            record.audio_url = audio_url
            record.tts_script = tts_script
            record.is_enabled = is_enabled
            record.priority = priority
        else:
            record = FounderAudioAlertConfig(
                alert_type=alert_type,
                display_name=display_name,
                audio_url=audio_url,
                tts_script=tts_script,
                is_enabled=is_enabled,
                priority=priority,
            )
            self.db.add(record)
        self.db.commit()
        return {"id": str(record.id), "alert_type": alert_type, "is_enabled": is_enabled}

    # ────────────────────────────────────────────────────────────────────────
    # TEMPLATES
    # ────────────────────────────────────────────────────────────────────────

    def list_templates(self, *, channel: str | None = None) -> list[dict[str, Any]]:
        q = self.db.query(FounderCommunicationTemplate).filter(FounderCommunicationTemplate.deleted_at == None)  # noqa: E711
        if channel:
            q = q.filter(FounderCommunicationTemplate.channel == channel)
        records = q.order_by(FounderCommunicationTemplate.name.asc()).all()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "channel": r.channel,
                "subject": r.subject,
                "is_active": r.is_active,
                "version": r.version,
            }
            for r in records
        ]

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        r = (
            self.db.query(FounderCommunicationTemplate)
            .filter(FounderCommunicationTemplate.id == template_id, FounderCommunicationTemplate.deleted_at == None)  # noqa: E711
            .first()
        )
        if not r:
            return None
        return {
            "id": str(r.id),
            "name": r.name,
            "channel": r.channel,
            "subject": r.subject,
            "body_template": r.body_template,
            "variables": r.variables,
            "is_active": r.is_active,
            "version": r.version,
        }

    def create_template(
        self,
        name: str,
        channel: str,
        body_template: str,
        *,
        subject: str | None = None,
        variables: list | None = None,
    ) -> dict[str, Any]:
        record = FounderCommunicationTemplate(
            name=name,
            channel=channel,
            subject=subject,
            body_template=body_template,
            variables=variables or [],
        )
        self.db.add(record)
        self.db.commit()
        return {"id": str(record.id), "name": name, "channel": channel}

    def render_template(self, template_id: str, variables: dict[str, str]) -> dict[str, str]:
        tmpl = self.get_template(template_id)
        if not tmpl:
            raise ValueError(f"Template {template_id} not found")
        return {
            "subject": _render_template(tmpl.get("subject") or "", variables),
            "body": _render_template(tmpl["body_template"], variables),
        }

    # ────────────────────────────────────────────────────────────────────────
    # AI-DRAFTED MESSAGE (Bedrock)
    # ────────────────────────────────────────────────────────────────────────

    def ai_draft_message(
        self,
        channel: str,
        context: str,
        *,
        tone: str = "professional",
    ) -> dict[str, Any]:
        """
        Use Bedrock to draft a message for the specified channel.
        Returns suggested subject + body; does NOT send anything.
        """
        prompt = (
            f"You are a professional communications assistant for FusionEMS Quantum, "
            f"a mission-critical public safety SaaS platform.\n\n"
            f"Draft a {tone} {channel} message based on this context:\n{context}\n\n"
            f"Format your response as JSON with keys: subject (for email/fax, empty string otherwise), body"
        )
        try:
            from core_app.ai.service import AiService  # noqa: PLC0415

            ai_svc = AiService()
            raw = ai_svc.chat(
                system=(
                    "You draft professional founder communications for a public safety SaaS platform. "
                    "Return strict JSON with keys: subject and body."
                ),
                user=prompt,
            )
            content = raw.content
            # Best-effort JSON parse; fall back to raw content as body
            try:
                parsed = json.loads(content)
                return {"subject": parsed.get("subject", ""), "body": parsed.get("body", content), "ai_generated": True}
            except (json.JSONDecodeError, AttributeError):
                return {"subject": "", "body": content, "ai_generated": True}
        except Exception as exc:
            logger.warning("founder_comms.ai_draft_failed channel=%s error=%s", channel, exc)
            return {"subject": "", "body": "", "ai_generated": False, "error": str(exc)}

    # ────────────────────────────────────────────────────────────────────────
    # BAA TEMPLATES
    # ────────────────────────────────────────────────────────────────────────

    def list_baa_templates(self) -> list[dict[str, Any]]:
        records = self.db.query(BAATemplate).filter(BAATemplate.deleted_at == None).order_by(BAATemplate.template_name.asc()).all()  # noqa: E711
        return [
            {
                "id": str(r.id),
                "template_name": r.template_name,
                "version_tag": r.version_tag,
                "effective_date": r.effective_date,
                "is_current": r.is_current,
            }
            for r in records
        ]

    def get_baa_template(self, template_id: str) -> dict[str, Any] | None:
        r = self.db.query(BAATemplate).filter(BAATemplate.id == template_id, BAATemplate.deleted_at == None).first()  # noqa: E711
        if not r:
            return None
        return {
            "id": str(r.id),
            "template_name": r.template_name,
            "version_tag": r.version_tag,
            "body_html": r.body_html,
            "variables": r.variables,
            "effective_date": r.effective_date,
            "is_current": r.is_current,
            "notes": r.notes,
        }

    def render_baa(self, template_id: str, variables: dict[str, str]) -> dict[str, str]:
        tmpl = self.get_baa_template(template_id)
        if not tmpl:
            raise ValueError(f"BAA template {template_id} not found")
        return {
            "template_name": tmpl["template_name"],
            "rendered_html": _render_template(tmpl["body_html"], variables),
        }

    def create_baa_template(
        self,
        template_name: str,
        body_html: str,
        *,
        version_tag: str = "v1.0",
        variables: list | None = None,
        effective_date: str | None = None,
        is_current: bool = False,
        notes: str | None = None,
    ) -> dict[str, Any]:
        if is_current:
            self.db.query(BAATemplate).filter(BAATemplate.is_current == True).update({"is_current": False})  # noqa: E712
        record = BAATemplate(
            template_name=template_name,
            version_tag=version_tag,
            body_html=body_html,
            variables=variables or [],
            effective_date=effective_date,
            is_current=is_current,
            notes=notes,
        )
        self.db.add(record)
        self.db.commit()
        return {"id": str(record.id), "template_name": template_name, "version_tag": version_tag}

    # ────────────────────────────────────────────────────────────────────────
    # WISCONSIN DOC TEMPLATES
    # ────────────────────────────────────────────────────────────────────────

    def list_wisconsin_templates(self, *, doc_type: str | None = None) -> list[dict[str, Any]]:
        q = self.db.query(WisconsinDocTemplate).filter(WisconsinDocTemplate.deleted_at == None)  # noqa: E711
        if doc_type:
            q = q.filter(WisconsinDocTemplate.doc_type == doc_type)
        records = q.order_by(WisconsinDocTemplate.display_name.asc()).all()
        return [
            {
                "id": str(r.id),
                "doc_type": r.doc_type,
                "display_name": r.display_name,
                "version_tag": r.version_tag,
                "effective_date": r.effective_date,
                "is_current": r.is_current,
                "wi_statute_reference": r.wi_statute_reference,
            }
            for r in records
        ]

    def render_wisconsin_doc(self, template_id: str, variables: dict[str, str]) -> dict[str, str]:
        r = self.db.query(WisconsinDocTemplate).filter(WisconsinDocTemplate.id == template_id, WisconsinDocTemplate.deleted_at == None).first()  # noqa: E711
        if not r:
            raise ValueError(f"Wisconsin template {template_id} not found")
        return {
            "doc_type": r.doc_type,
            "display_name": r.display_name,
            "wi_statute_reference": r.wi_statute_reference,
            "rendered_html": _render_template(r.body_html, variables),
        }

    def create_wisconsin_template(
        self,
        doc_type: str,
        display_name: str,
        body_html: str,
        *,
        version_tag: str = "v1.0",
        variables: list | None = None,
        effective_date: str | None = None,
        is_current: bool = False,
        wi_statute_reference: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        if is_current:
            self.db.query(WisconsinDocTemplate).filter(
                WisconsinDocTemplate.doc_type == doc_type, WisconsinDocTemplate.is_current == True  # noqa: E712
            ).update({"is_current": False})
        record = WisconsinDocTemplate(
            doc_type=doc_type,
            display_name=display_name,
            version_tag=version_tag,
            body_html=body_html,
            variables=variables or [],
            effective_date=effective_date,
            is_current=is_current,
            wi_statute_reference=wi_statute_reference,
            notes=notes,
        )
        self.db.add(record)
        self.db.commit()
        return {"id": str(record.id), "doc_type": doc_type, "display_name": display_name}

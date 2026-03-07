"""
Billing Communications Service
================================
STRICTLY BILLING ONLY — Telnyx is the SMS/voice rail for patient billing.
CrewLink is the ops paging rail. These two must never overlap.

Boundary enforcement:
- This service only handles patient billing messages (balance notices, payment links,
  appointment reminders, statement notifications, self-pay reminders).
- Operational content (dispatch, paging, crew alerts) is BLOCKED at the keyword level.
- All sends are logged with correlation IDs and are idempotent via message deduplication.
- Opt-out (STOP) management is enforced before every send.
"""
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.core.config import get_settings
from core_app.core.errors import AppError
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

logger = logging.getLogger(__name__)

# ── Ops keyword blocklist (billing channel must never carry these) ─────────────
_OPS_BLOCKLIST = re.compile(
    r"\b(dispatch|code\s*3|code\s*1|responding|en\s*route|unit\s*\d+|"
    r"crewlink|paging|page\s+crew|scene|ems\s+call|ambulance\s+call|"
    r"mission\s+id|incident\s+id|cad\s+call)\b",
    re.IGNORECASE,
)


class BillingCommunicationService:
    """
    Billing-only communications service.
    Uses Telnyx for SMS, LOB for physical mail.
    Every method enforces the ops/billing boundary.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._settings = get_settings()
        self._svc = DominationService(db, get_event_publisher())

    # ── Boundary guard ────────────────────────────────────────────────────────

    def _assert_billing_content(self, message: str) -> None:
        """Raises AppError if operational keywords are detected in billing message."""
        if _OPS_BLOCKLIST.search(message):
            raise AppError(
                code="OPS_CONTENT_IN_BILLING_CHANNEL",
                message=(
                    "Operational content detected in billing SMS channel. "
                    "Use CrewLink for dispatch paging. Telnyx is billing-only."
                ),
                status_code=422,
            )

    # ── SMS (Telnyx) ──────────────────────────────────────────────────────────

    async def send_patient_balance_sms(
        self,
        tenant_id: str,
        patient_id: str,
        to_phone: str,
        message: str,
        dedup_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> dict:
        """
        Send a billing SMS via Telnyx. STRICTLY BILLING ONLY.

        - Enforces ops content boundary.
        - Checks opt-out status before sending.
        - Idempotent: same dedup_key within 24h is skipped.
        - Logs every send attempt with full audit trail.
        - Never raises on Telnyx transient errors — logs and returns status.
        """
        corr = correlation_id or str(uuid.uuid4())
        dedup_key = dedup_key or f"sms:{tenant_id}:{patient_id}:{hash(message) & 0xFFFF}"

        self._assert_billing_content(message)

        # ── Opt-out check ────────────────────────────────────────────────────
        if await self._is_opted_out(tenant_id, to_phone):
            logger.info(
                "billing_sms_opted_out tenant=%s phone=%.6s dedup=%s",
                tenant_id, to_phone, dedup_key,
            )
            return {"status": "OPTED_OUT", "dedup_key": dedup_key}

        # ── Idempotency ───────────────────────────────────────────────────────
        existing = self.db.execute(
            text(
                "SELECT id, status FROM billing_sms_log "
                "WHERE tenant_id = :tid AND dedup_key = :dk "
                "AND created_at > now() - INTERVAL '24 hours' LIMIT 1"
            ),
            {"tid": tenant_id, "dk": dedup_key},
        ).mappings().first()

        if existing and existing["status"] in ("SENT", "DELIVERED"):
            logger.info(
                "billing_sms_duplicate_skipped tenant=%s dedup=%s",
                tenant_id, dedup_key,
            )
            return {"status": "DUPLICATE", "dedup_key": dedup_key, "id": str(existing["id"])}

        # ── Log attempt ───────────────────────────────────────────────────────
        log_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO billing_sms_log "
                "(id, tenant_id, patient_id, to_phone, message, status, "
                " dedup_key, correlation_id, created_at, updated_at) "
                "VALUES (:id, :tid, :pid, :phone, :msg, 'QUEUED', "
                " :dk, :corr, now(), now())"
            ),
            {
                "id": log_id, "tid": tenant_id, "pid": patient_id,
                "phone": to_phone, "msg": message,
                "dk": dedup_key, "corr": corr,
            },
        )
        self.db.flush()

        # ── Send via Telnyx ───────────────────────────────────────────────────
        api_key = self._settings.telnyx_api_key
        from_number = self._settings.telnyx_from_number

        if not api_key or api_key.startswith("REPLACE"):
            logger.warning(
                "billing_sms_telnyx_not_configured tenant=%s log_id=%s",
                tenant_id, log_id,
            )
            self.db.execute(
                text("UPDATE billing_sms_log SET status = 'NOT_CONFIGURED', updated_at = now() WHERE id = :id"),
                {"id": log_id},
            )
            return {"status": "NOT_CONFIGURED", "log_id": log_id}

        try:
            from core_app.telnyx.client import send_sms, TelnyxApiError

            result = send_sms(
                api_key=api_key,
                from_number=from_number,
                to_number=to_phone,
                text=message,
            )
            telnyx_message_id = (
                result.get("data", {}).get("id") or result.get("id", "")
            )
            self.db.execute(
                text(
                    "UPDATE billing_sms_log "
                    "SET status = 'SENT', telnyx_message_id = :tmid, updated_at = now() "
                    "WHERE id = :id"
                ),
                {"tmid": telnyx_message_id, "id": log_id},
            )
            logger.info(
                "billing_sms_sent tenant=%s log_id=%s telnyx_id=%s",
                tenant_id, log_id, telnyx_message_id,
            )
            return {"status": "SENT", "log_id": log_id, "telnyx_message_id": telnyx_message_id}

        except Exception as exc:
            logger.error(
                "billing_sms_send_failed tenant=%s log_id=%s error=%s",
                tenant_id, log_id, exc,
            )
            self.db.execute(
                text(
                    "UPDATE billing_sms_log "
                    "SET status = 'FAILED', error_detail = :err, updated_at = now() "
                    "WHERE id = :id"
                ),
                {"err": str(exc)[:500], "id": log_id},
            )
            # Non-fatal: return failed status, don't crash the caller
            return {"status": "FAILED", "log_id": log_id, "error": str(exc)}

    # ── LOB physical mail ─────────────────────────────────────────────────────

    async def trigger_mailed_statement(
        self,
        tenant_id: str,
        claim_id: str,
        recipient: dict,
        template_id: str = "STATEMENT_V1",
        correlation_id: Optional[str] = None,
    ) -> dict:
        """
        Trigger a physical mailed statement via LOB.

        - Idempotent: same claim_id + template won't be mailed twice.
        - Records LOB letter_id for delivery tracking.
        - Failures are logged and returned — never silently dropped.
        """
        corr = correlation_id or str(uuid.uuid4())

        # ── Idempotency ───────────────────────────────────────────────────────
        existing = self.db.execute(
            text(
                "SELECT id, lob_letter_id, status FROM mail_fulfillment_records "
                "WHERE tenant_id = :tid AND claim_id = :cid AND template_id = :tmpl "
                "AND status NOT IN ('FAILED', 'REJECTED') LIMIT 1"
            ),
            {"tid": tenant_id, "cid": claim_id, "tmpl": template_id},
        ).mappings().first()

        if existing:
            logger.info(
                "mail_fulfillment_duplicate_skipped tenant=%s claim=%s status=%s",
                tenant_id, claim_id, existing["status"],
            )
            return {
                "status": "DUPLICATE",
                "id": str(existing["id"]),
                "lob_letter_id": existing.get("lob_letter_id"),
            }

        # ── Insert record ─────────────────────────────────────────────────────
        record_id = str(uuid.uuid4())
        self.db.execute(
            text(
                "INSERT INTO mail_fulfillment_records "
                "(id, tenant_id, claim_id, template_id, recipient_name, "
                " address_line1, address_line2, city, state, zip, "
                " status, correlation_id, created_at, updated_at) "
                "VALUES (:id, :tid, :cid, :tmpl, :name, :addr1, :addr2, "
                " :city, :state, :zip, 'CREATED', :corr, now(), now())"
            ),
            {
                "id": record_id, "tid": tenant_id, "cid": claim_id,
                "tmpl": template_id,
                "name": recipient.get("name", "")[:200],
                "addr1": recipient.get("address1", "")[:200],
                "addr2": recipient.get("address2", "")[:100],
                "city": recipient.get("city", "")[:100],
                "state": recipient.get("state", "")[:10],
                "zip": recipient.get("zip", "")[:20],
                "corr": corr,
            },
        )
        self.db.flush()

        # ── Send via LOB ──────────────────────────────────────────────────────
        lob_api_key = self._settings.lob_api_key
        if not lob_api_key or lob_api_key.startswith("REPLACE"):
            logger.warning(
                "mail_fulfillment_lob_not_configured tenant=%s record_id=%s",
                tenant_id, record_id,
            )
            self.db.execute(
                text(
                    "UPDATE mail_fulfillment_records "
                    "SET status = 'NOT_CONFIGURED', updated_at = now() WHERE id = :id"
                ),
                {"id": record_id},
            )
            return {"status": "NOT_CONFIGURED", "record_id": record_id}

        try:
            import requests as _req

            lob_payload = {
                "description": f"Statement for claim {claim_id}",
                "to": {
                    "name": recipient.get("name", "Patient"),
                    "address_line1": recipient.get("address1", ""),
                    "address_line2": recipient.get("address2", ""),
                    "address_city": recipient.get("city", ""),
                    "address_state": recipient.get("state", ""),
                    "address_zip": recipient.get("zip", ""),
                    "address_country": "US",
                },
                "from": {
                    "name": recipient.get("from_name", "FusionEMS Billing"),
                    "address_line1": recipient.get("from_address1", ""),
                    "address_city": recipient.get("from_city", ""),
                    "address_state": recipient.get("from_state", ""),
                    "address_zip": recipient.get("from_zip", ""),
                    "address_country": "US",
                },
                "file": f"<html><body>Statement for {claim_id}</body></html>",
                "color": False,
                "metadata": {"claim_id": claim_id, "tenant_id": tenant_id, "correlation_id": corr},
            }

            resp = _req.post(
                "https://api.lob.com/v1/letters",
                auth=(lob_api_key, ""),
                json=lob_payload,
                timeout=30,
            )
            resp.raise_for_status()
            lob_data = resp.json()
            lob_letter_id = lob_data.get("id", "")

            self.db.execute(
                text(
                    "UPDATE mail_fulfillment_records "
                    "SET status = 'MAILED', lob_letter_id = :lid, updated_at = now() "
                    "WHERE id = :id"
                ),
                {"lid": lob_letter_id, "id": record_id},
            )
            logger.info(
                "mail_fulfillment_sent tenant=%s record_id=%s lob_id=%s",
                tenant_id, record_id, lob_letter_id,
            )
            return {"status": "MAILED", "record_id": record_id, "lob_letter_id": lob_letter_id}

        except Exception as exc:
            logger.error(
                "mail_fulfillment_send_failed tenant=%s record_id=%s error=%s",
                tenant_id, record_id, exc,
            )
            self.db.execute(
                text(
                    "UPDATE mail_fulfillment_records "
                    "SET status = 'FAILED', error_detail = :err, updated_at = now() "
                    "WHERE id = :id"
                ),
                {"err": str(exc)[:500], "id": record_id},
            )
            return {"status": "FAILED", "record_id": record_id, "error": str(exc)}

    # ── Opt-out management ────────────────────────────────────────────────────

    async def _is_opted_out(self, tenant_id: str, phone: str) -> bool:
        """Check if a phone number has opted out of billing SMS for this tenant."""
        result = self.db.execute(
            text(
                "SELECT 1 FROM billing_sms_opt_outs "
                "WHERE tenant_id = :tid AND phone = :phone AND opted_out = TRUE LIMIT 1"
            ),
            {"tid": tenant_id, "phone": phone},
        ).first()
        return result is not None

    async def record_opt_out(self, tenant_id: str, phone: str, source: str = "STOP_REPLY") -> None:
        """Record a STOP/opt-out for a phone number. Called by Telnyx webhook handler."""
        self.db.execute(
            text(
                "INSERT INTO billing_sms_opt_outs "
                "(id, tenant_id, phone, opted_out, source, created_at) "
                "VALUES (:id, :tid, :phone, TRUE, :src, now()) "
                "ON CONFLICT (tenant_id, phone) DO UPDATE SET opted_out = TRUE, source = :src"
            ),
            {
                "id": str(uuid.uuid4()),
                "tid": tenant_id,
                "phone": phone,
                "src": source,
            },
        )
        logger.info(
            "billing_sms_opt_out_recorded tenant=%s phone=%.6s source=%s",
            tenant_id, phone, source,
        )

    async def record_opt_in(self, tenant_id: str, phone: str) -> None:
        """Record UNSTOP / opt-in re-enrollment."""
        self.db.execute(
            text(
                "INSERT INTO billing_sms_opt_outs "
                "(id, tenant_id, phone, opted_out, source, created_at) "
                "VALUES (:id, :tid, :phone, FALSE, 'UNSTOP_REPLY', now()) "
                "ON CONFLICT (tenant_id, phone) DO UPDATE SET opted_out = FALSE"
            ),
            {"id": str(uuid.uuid4()), "tid": tenant_id, "phone": phone},
        )

    async def get_sms_log(
        self,
        tenant_id: str,
        patient_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Return billing SMS audit log for a tenant."""
        where = "WHERE tenant_id = :tid"
        params: dict = {"tid": tenant_id, "limit": limit}
        if patient_id:
            where += " AND patient_id = :pid"
            params["pid"] = patient_id

        rows = self.db.execute(
            text(
                f"SELECT id, patient_id, to_phone, status, dedup_key, "
                f"telnyx_message_id, correlation_id, created_at, updated_at "
                f"FROM billing_sms_log {where} "
                f"ORDER BY created_at DESC LIMIT :limit"
            ),
            params,
        ).mappings().all()
        return [dict(r) for r in rows]

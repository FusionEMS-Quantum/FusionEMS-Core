from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import time
from datetime import UTC, datetime
from typing import Any

import boto3

from core_app.documents.classifier import classify_text

logger = logging.getLogger(__name__)

FAX_DOCS_TABLE = "fax_documents"
_TEXTRACT_POLL_INTERVAL_S = 5
_TEXTRACT_MAX_POLLS = 60


def lambda_handler(event: dict[str, Any], context: Any) -> None:
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            process_fax_classify(body)
        except Exception as exc:
            logger.exception(
                "fax_classify_record_failed message_id=%s error=%s",
                record.get("messageId", ""),
                exc,
            )
            raise


def process_fax_classify(message: dict[str, Any]) -> None:
    fax_id: str = message.get("fax_id", "")
    tenant_id: str | None = message.get("tenant_id")
    s3_key: str = message.get("s3_key", "")
    message.get("sha256")
    case_id: str | None = message.get("case_id")

    logger.info(
        "fax_classify_start fax_id=%s tenant_id=%s s3_key=%s",
        fax_id,
        tenant_id,
        s3_key,
    )

    if not fax_id or not s3_key:
        logger.warning("fax_classify_missing_fields fax_id=%s s3_key=%s", fax_id, s3_key)
        return

    if not tenant_id:
        logger.warning("fax_classify_missing_tenant fax_id=%s", fax_id)
        return

    bucket = os.environ.get("S3_BUCKET_DOCS", "")
    extracted_text = _extract_text(s3_key=s3_key, bucket=bucket)
    doc_type = _classify_document(s3_key=s3_key, extracted_text=extracted_text)
    refined_case_id = case_id or _match_case_from_text(extracted_text, tenant_id)
    status = "classified" if doc_type and doc_type != "other" else "unclassified"

    _persist_results(
        fax_id=fax_id,
        doc_type=doc_type,
        case_id=refined_case_id,
        status=status,
        extracted_text=extracted_text,
        s3_key=s3_key,
        tenant_id=tenant_id,
    )

    # Compute match suggestions and persist match status.
    try:
        _match_and_persist(
            fax_id=fax_id,
            tenant_id=tenant_id,
            ocr_text=extracted_text,
        )
    except Exception as exc:
        logger.warning("fax_classify_match_failed fax_id=%s error=%s", fax_id, exc)

    logger.info(
        "fax_classify_done fax_id=%s doc_type=%s case_id=%s status=%s",
        fax_id,
        doc_type,
        refined_case_id,
        status,
    )


def _extract_text(*, s3_key: str, bucket: str) -> str:
    if not bucket:
        logger.warning("fax_classify_no_bucket s3_key=%s — S3_BUCKET_DOCS not set", s3_key)
        return ""

    textract = boto3.client("textract")

    try:
        start_resp = textract.start_document_text_detection(
            DocumentLocation={"S3Object": {"Bucket": bucket, "Name": s3_key}}
        )
    except Exception as exc:
        logger.error("fax_classify_textract_start_failed s3_key=%s error=%s", s3_key, exc)
        return ""

    job_id: str = start_resp["JobId"]
    logger.info("fax_classify_textract_started s3_key=%s job_id=%s", s3_key, job_id)

    lines: list[str] = []
    next_token: str | None = None

    for attempt in range(_TEXTRACT_MAX_POLLS):
        time.sleep(_TEXTRACT_POLL_INTERVAL_S)
        try:
            kwargs: dict[str, Any] = {"JobId": job_id}
            if next_token:
                kwargs["NextToken"] = next_token
            resp = textract.get_document_text_detection(**kwargs)
        except Exception as exc:
            logger.error(
                "fax_classify_textract_poll_failed job_id=%s attempt=%d error=%s",
                job_id,
                attempt,
                exc,
            )
            return ""

        job_status: str = resp.get("JobStatus", "")

        if job_status == "FAILED":
            logger.error(
                "fax_classify_textract_job_failed job_id=%s status_message=%s",
                job_id,
                resp.get("StatusMessage", ""),
            )
            return ""

        if job_status == "SUCCEEDED":
            for block in resp.get("Blocks", []):
                if block.get("BlockType") == "LINE":
                    lines.append(block.get("Text", ""))
            next_token = resp.get("NextToken")
            if not next_token:
                break
        else:
            logger.debug("fax_classify_textract_in_progress job_id=%s attempt=%d", job_id, attempt)
    else:
        logger.error(
            "fax_classify_textract_timeout job_id=%s after %d polls",
            job_id,
            _TEXTRACT_MAX_POLLS,
        )
        return ""

    text = "\n".join(lines)
    logger.info("fax_classify_textract_done job_id=%s characters=%d", job_id, len(text))
    return text


def _classify_document(*, s3_key: str, extracted_text: str) -> str | None:
    if extracted_text.strip():
        return classify_text(extracted_text)

    key_lower = s3_key.lower()
    if "facesheet" in key_lower or "face_sheet" in key_lower:
        return "facesheet"
    if "eob" in key_lower or "explanation" in key_lower:
        return "eob"
    if "auth" in key_lower or "authorization" in key_lower:
        return "auth"
    if "insurance" in key_lower:
        return "insurance_card"
    if "pcs" in key_lower:
        return "pcs"
    if "denial" in key_lower:
        return "denial_letter"
    if "appeal" in key_lower:
        return "appeal_response"
    return None


def _match_case_from_text(text: str, tenant_id: str | None) -> str | None:
    matches = re.findall(r"\b\d{6,12}\b", text)
    if matches:
        return matches[0]
    return None


def _persist_results(
    *,
    fax_id: str,
    doc_type: str | None,
    case_id: str | None,
    status: str,
    extracted_text: str,
    s3_key: str,
    tenant_id: str | None,
) -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error("fax_classify_persist_skipped DATABASE_URL not set")
        return

    try:
        import psycopg

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                # RLS requires tenant context.
                if tenant_id:
                    cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
                cur.execute(
                    """
                    UPDATE fax_documents
                    SET doc_type = %s,
                        case_id  = %s,
                        status   = %s,
                        updated_at = %s
                    WHERE fax_id = %s
                    """,
                    (doc_type, case_id, status, datetime.now(UTC).isoformat(), fax_id),
                )
            conn.commit()
    except Exception as exc:
        logger.error("fax_classify_persist_failed fax_id=%s error=%s", fax_id, exc)


def _match_and_persist(*, fax_id: str, tenant_id: str, ocr_text: str) -> None:
    """Best-effort match computation and persistence.

    Persists match state in document_matches (domination JSONB) and emits a fax_events
    timeline event. This worker is triggered by the classify queue, which is the
    only fax pipeline queue currently wired in IaC.
    """

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.warning("fax_match_persist_skipped DATABASE_URL not set")
        return

    if not ocr_text.strip():
        _persist_document_match(
            fax_id=fax_id,
            tenant_id=tenant_id,
            match_status="unmatched",
            matched_claim_id=None,
            suggested_matches=[],
            match_type=None,
            confidence=None,
            patient_name=None,
            database_url=database_url,
        )
        return

    try:
        import sqlalchemy as sa
        import sqlalchemy.orm as sa_orm
    except Exception:
        logger.warning("fax_match_sqlalchemy_unavailable")
        return

    engine = sa.create_engine(database_url, pool_pre_ping=True)
    session_factory = sa_orm.sessionmaker(bind=engine)
    db = session_factory()
    try:
        db.execute(sa.text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)})
        from core_app.fax.claim_matcher import ClaimMatcher

        matcher = ClaimMatcher(db, tenant_id)
        matches = matcher.match_claim_probabilistic(ocr_text, fax_date="")

        if not matches:
            _persist_document_match(
                fax_id=fax_id,
                tenant_id=tenant_id,
                match_status="unmatched",
                matched_claim_id=None,
                suggested_matches=[],
                match_type=None,
                confidence=None,
                patient_name=None,
                database_url=database_url,
            )
            return

        best = matches[0]
        best_conf = float(best.get("confidence") or 0.0)
        best_claim_id = str(best.get("claim_id") or "").strip()
        best_claim_data = best.get("claim_data") if isinstance(best.get("claim_data"), dict) else {}
        patient_name = (
            str(best_claim_data.get("patient_name") or "").strip()
            if isinstance(best_claim_data, dict)
            else ""
        ) or None

        if best.get("score", 0) >= 80 and best_claim_id:
            with contextlib.suppress(Exception):
                matcher.attach_to_claim(
                    fax_id,
                    best_claim_id,
                    "auto_probabilistic",
                    actor="auto_classify_worker",
                )
            _persist_document_match(
                fax_id=fax_id,
                tenant_id=tenant_id,
                match_status="matched",
                matched_claim_id=best_claim_id,
                suggested_matches=[],
                match_type="auto_probabilistic",
                confidence=best_conf,
                patient_name=patient_name,
                database_url=database_url,
            )
            with contextlib.suppress(Exception):
                _emit_fax_event(
                    tenant_id=tenant_id,
                    fax_id=fax_id,
                    event_type="fax_match_auto_matched",
                    payload={
                        "match_status": "matched",
                        "matched_claim_id": best_claim_id,
                        "match_type": "auto_probabilistic",
                        "confidence": best_conf,
                    },
                    database_url=database_url,
                )
            return

        suggestions: list[dict[str, Any]] = []
        for m in matches[:5]:
            cid = str(m.get("claim_id") or "").strip()
            if not cid:
                continue
            cdata = m.get("claim_data") if isinstance(m.get("claim_data"), dict) else {}
            pname = str(cdata.get("patient_name") or "").strip() if isinstance(cdata, dict) else ""
            suggestions.append(
                {
                    "claim_id": cid,
                    "patient_name": pname or None,
                    "score": float(m.get("confidence") or 0.0),
                }
            )

        _persist_document_match(
            fax_id=fax_id,
            tenant_id=tenant_id,
            match_status="review",
            matched_claim_id=None,
            suggested_matches=suggestions,
            match_type="suggested",
            confidence=best_conf,
            patient_name=None,
            database_url=database_url,
        )
        with contextlib.suppress(Exception):
            _emit_fax_event(
                tenant_id=tenant_id,
                fax_id=fax_id,
                event_type="fax_match_suggested",
                payload={
                    "match_status": "review",
                    "suggestion_count": len(suggestions),
                    "top_confidence": best_conf,
                },
                database_url=database_url,
            )
    finally:
        db.close()
        engine.dispose()


def _persist_document_match(
    *,
    fax_id: str,
    tenant_id: str,
    match_status: str,
    matched_claim_id: str | None,
    suggested_matches: list[dict[str, Any]],
    match_type: str | None,
    confidence: float | None,
    patient_name: str | None,
    database_url: str,
) -> None:
    now = datetime.now(UTC).isoformat()
    patch = {
        "fax_id": fax_id,
        "match_status": match_status,
        "matched_claim_id": matched_claim_id,
        "suggested_matches": suggested_matches,
        "match_type": match_type,
        "confidence": confidence,
        "patient_name": patient_name,
        "updated_at": now,
    }

    try:
        import psycopg

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
                existing = cur.execute(
                    "SELECT id FROM document_matches "
                    "WHERE tenant_id = %s AND deleted_at IS NULL AND data->>'fax_id' = %s "
                    "ORDER BY updated_at DESC LIMIT 1",
                    (tenant_id, fax_id),
                ).fetchone()
                patch_json = json.dumps(patch, default=str)
                if existing and existing[0]:
                    cur.execute(
                        "UPDATE document_matches "
                        "SET data = data || %s::jsonb, version = version + 1, updated_at = now() "
                        "WHERE tenant_id = %s AND id = %s",
                        (patch_json, tenant_id, str(existing[0])),
                    )
                else:
                    cur.execute(
                        "INSERT INTO document_matches (tenant_id, data) VALUES (%s, %s::jsonb)",
                        (tenant_id, patch_json),
                    )
            conn.commit()
    except Exception as exc:
        logger.error("fax_match_persist_failed fax_id=%s error=%s", fax_id, exc)


def _emit_fax_event(
    *, tenant_id: str, fax_id: str, event_type: str, payload: dict[str, Any], database_url: str
) -> None:
    now = datetime.now(UTC).isoformat()
    data = {
        "fax_id": fax_id,
        "event_type": event_type,
        "source": "fax_classify_worker",
        "received_at": now,
        **payload,
    }
    try:
        import psycopg

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
                cur.execute(
                    "INSERT INTO fax_events (tenant_id, data) VALUES (%s::uuid, %s::jsonb)",
                    (tenant_id, json.dumps(data, default=str)),
                )
            conn.commit()
    except Exception as exc:
        logger.warning("fax_event_emit_failed fax_id=%s error=%s", fax_id, exc)

from __future__ import annotations

# pyright: reportMissingImports=false

# ruff: noqa: I001

# pylint: disable=import-error

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
import sqlalchemy.orm as sa_orm

logger = logging.getLogger(__name__)


def lambda_handler(event: dict, context: Any) -> None:
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            process_fax_match(body)
        except Exception as exc:
            logger.exception(
                "fax_match_record_failed message_id=%s error=%s",
                record.get("messageId", ""),
                exc,
            )
            raise


def process_fax_match(message: dict) -> None:
    fax_id: str = message.get("fax_id", "")
    tenant_id: str | None = message.get("tenant_id")
    s3_key: str = message.get("s3_key", "")
    ocr_text: str = message.get("ocr_text", "")
    fax_date: str = message.get("fax_date", "")

    correlation_id = message.get("correlation_id") or str(uuid.uuid4())
    logger.info("fax_match_start fax_id=%s correlation_id=%s", fax_id, correlation_id)

    if not fax_id or not tenant_id:
        logger.warning(
            "fax_match_missing_fields fax_id=%s tenant_id=%s correlation_id=%s",
            fax_id,
            tenant_id,
            correlation_id,
        )
        return

    database_url_idem = os.environ.get("DATABASE_URL", "")
    if database_url_idem:
        try:
            _engine = sa.create_engine(database_url_idem, pool_pre_ping=True)
            _Session = sa_orm.sessionmaker(bind=_engine)
            db = _Session()
            try:
                # RLS requires tenant context for tenant-scoped tables.
                db.execute(sa.text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)})
                existing = db.execute(
                    sa.text(
                        "SELECT data->>'match_status' as status FROM document_matches WHERE data->>'fax_id' = :fid AND tenant_id = :tid LIMIT 1"
                    ),
                    {"fid": fax_id, "tid": str(tenant_id)},
                ).fetchone()
                if existing and existing.status in ("matched", "review"):
                    logger.info(
                        "fax_match_skip_already_processed fax_id=%s status=%s correlation_id=%s",
                        fax_id,
                        existing.status,
                        correlation_id,
                    )
                    return
            finally:
                db.close()
                _engine.dispose()
        except Exception as _idem_exc:
            logger.warning(
                "fax_match_idempotency_check_failed fax_id=%s error=%s correlation_id=%s",
                fax_id,
                _idem_exc,
                correlation_id,
            )

    database_url = os.environ.get("DATABASE_URL", "")
    bucket = os.environ.get("S3_BUCKET_DOCS", "")

    qr_payload: dict | None = None
    if s3_key and bucket:
        qr_payload = _try_decode_qr_from_pdf(bucket=bucket, s3_key=s3_key)

    if qr_payload:
        logger.info(
            "fax_match_qr_decoded fax_id=%s payload_claim_id=%s correlation_id=%s",
            fax_id,
            qr_payload.get("claim_id"),
            correlation_id,
        )
        match_result = _match_by_qr(
            fax_id=fax_id,
            tenant_id=tenant_id,
            qr_payload=qr_payload,
            database_url=database_url,
        )
        if match_result:
            _persist_status(
                fax_id=fax_id,
                tenant_id=tenant_id,
                match_status="matched",
                matched_claim_id=match_result["claim_id"],
                suggested_matches=None,
                match_type="qr_match",
                confidence=1.0,
                patient_name=match_result.get("patient_name"),
                database_url=database_url,
            )
            logger.info(
                "fax_match_auto_matched_qr fax_id=%s claim_id=%s correlation_id=%s",
                fax_id,
                match_result["claim_id"],
                correlation_id,
            )
            return

    if ocr_text:
        matches = _match_probabilistic(
            fax_id=fax_id,
            tenant_id=tenant_id,
            ocr_text=ocr_text,
            fax_date=fax_date,
            database_url=database_url,
        )
        if matches:
            best = matches[0]
            if best["score"] >= 80:
                _attach_claim(
                    fax_id=fax_id,
                    tenant_id=tenant_id,
                    claim_id=best["claim_id"],
                    attachment_type="auto_probabilistic",
                    database_url=database_url,
                )
                _persist_status(
                    fax_id=fax_id,
                    tenant_id=tenant_id,
                    match_status="matched",
                    matched_claim_id=best["claim_id"],
                    suggested_matches=None,
                    match_type="auto_probabilistic",
                    confidence=float(best.get("confidence") or 0.0),
                    patient_name=str((best.get("claim_data") or {}).get("patient_name") or "") or None,
                    database_url=database_url,
                )
                logger.info(
                    "fax_match_auto_matched_prob fax_id=%s claim_id=%s score=%s correlation_id=%s",
                    fax_id,
                    best["claim_id"],
                    best["score"],
                    correlation_id,
                )
                return

            _persist_status(
                fax_id=fax_id,
                tenant_id=tenant_id,
                match_status="review",
                matched_claim_id=None,
                suggested_matches=matches[:5],
                match_type="suggested",
                confidence=float(best.get("confidence") or 0.0),
                patient_name=None,
                database_url=database_url,
            )
            logger.info(
                "fax_match_suggested fax_id=%s top_score=%s correlation_id=%s",
                fax_id,
                best["score"],
                correlation_id,
            )
            return

    _persist_status(
        fax_id=fax_id,
        tenant_id=tenant_id,
        match_status="unmatched",
        matched_claim_id=None,
        suggested_matches=None,
        match_type=None,
        confidence=None,
        patient_name=None,
        database_url=database_url,
    )
    logger.info("fax_match_unmatched fax_id=%s correlation_id=%s", fax_id, correlation_id)


def _try_decode_qr_from_pdf(*, bucket: str, s3_key: str) -> dict | None:
    try:
        import boto3

        s3 = boto3.client("s3")
        resp = s3.get_object(Bucket=bucket, Key=s3_key)
        pdf_bytes: bytes = resp["Body"].read()
    except Exception as exc:
        logger.warning("fax_match_s3_download_failed s3_key=%s error=%s", s3_key, exc)
        return None

    first_page_bytes: bytes = pdf_bytes
    try:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count > 0:
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            first_page_bytes = pix.tobytes("png")
        doc.close()
    except Exception as exc:
        logger.debug("fax_match_fitz_unavailable error=%s — using raw pdf bytes", exc)

    try:
        from core_app.fax.claim_matcher import ClaimMatcher

        matcher = ClaimMatcher.__new__(ClaimMatcher)
        return matcher.decode_qr_payload(first_page_bytes)
    except Exception as exc:
        logger.debug("fax_match_qr_decode_failed error=%s", exc)
        return None


def _match_by_qr(
    *,
    fax_id: str,
    tenant_id: str,
    qr_payload: dict,
    database_url: str,
) -> dict | None:
    if not database_url:
        return None
    try:
        engine = sa.create_engine(database_url, pool_pre_ping=True)
        session_factory = sa_orm.sessionmaker(bind=engine)
        db = session_factory()
        try:
            from core_app.fax.claim_matcher import ClaimMatcher

            matcher = ClaimMatcher(db, tenant_id)
            result = matcher.match_claim_by_qr(qr_payload)
            if result:
                claim_id = str(result.get("id", ""))
                matcher.attach_to_claim(fax_id, claim_id, "qr_match", actor="auto_qr")
                cdata = result.get("data") or {}
                if isinstance(cdata, str):
                    try:
                        cdata = json.loads(cdata)
                    except Exception:
                        cdata = {}
                patient_name = None
                if isinstance(cdata, dict):
                    patient_name = str(cdata.get("patient_name") or "").strip() or None
                return {"claim_id": claim_id, "patient_name": patient_name}
            return None
        finally:
            db.close()
            engine.dispose()
    except Exception as exc:
        logger.error("fax_match_by_qr_failed fax_id=%s error=%s", fax_id, exc)
        return None


def _match_probabilistic(
    *,
    fax_id: str,
    tenant_id: str,
    ocr_text: str,
    fax_date: str,
    database_url: str,
) -> list[dict]:
    if not database_url:
        return []
    try:
        engine = sa.create_engine(database_url, pool_pre_ping=True)
        session_factory = sa_orm.sessionmaker(bind=engine)
        db = session_factory()
        try:
            from core_app.fax.claim_matcher import ClaimMatcher

            matcher = ClaimMatcher(db, tenant_id)
            return matcher.match_claim_probabilistic(ocr_text, fax_date=fax_date)
        finally:
            db.close()
            engine.dispose()
    except Exception as exc:
        logger.error("fax_match_probabilistic_failed fax_id=%s error=%s", fax_id, exc)
        return []


def _attach_claim(
    *,
    fax_id: str,
    tenant_id: str,
    claim_id: str,
    attachment_type: str,
    database_url: str,
) -> None:
    if not database_url:
        return
    try:
        engine = sa.create_engine(database_url, pool_pre_ping=True)
        session_factory = sa_orm.sessionmaker(bind=engine)
        db = session_factory()
        try:
            from core_app.fax.claim_matcher import ClaimMatcher

            matcher = ClaimMatcher(db, tenant_id)
            matcher.attach_to_claim(fax_id, claim_id, attachment_type, actor="auto_worker")
        finally:
            db.close()
            engine.dispose()
    except Exception as exc:
        logger.error(
            "fax_match_attach_failed fax_id=%s claim_id=%s error=%s", fax_id, claim_id, exc
        )


def _persist_status(
    *,
    fax_id: str,
    tenant_id: str,
    match_status: str,
    matched_claim_id: str | None,
    suggested_matches: list[dict] | None,
    match_type: str | None,
    confidence: float | None,
    patient_name: str | None,
    database_url: str,
) -> None:
    if not database_url:
        logger.error("fax_match_persist_skipped DATABASE_URL not set")
        return

    now = datetime.now(UTC).isoformat()
    # Normalize suggestions for the portal UI (score is 0..1).
    normalized_suggestions: list[dict[str, Any]] = []
    for item in suggested_matches or []:
        claim_id = str(item.get("claim_id") or "").strip()
        if not claim_id:
            continue
        claim_data = item.get("claim_data") if isinstance(item.get("claim_data"), dict) else {}
        pname = str(claim_data.get("patient_name") or "").strip() or None
        score = item.get("confidence")
        try:
            score_f = float(score) if score is not None else None
        except Exception:
            score_f = None
        normalized_suggestions.append(
            {
                "claim_id": claim_id,
                "patient_name": pname,
                "score": score_f,
            }
        )
    suggested_json = json.dumps(normalized_suggestions, default=str)

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

                patch = {
                    "fax_id": fax_id,
                    "match_status": match_status,
                    "matched_claim_id": matched_claim_id,
                    "suggested_matches": json.loads(suggested_json),
                    "match_type": match_type,
                    "confidence": confidence,
                    "patient_name": patient_name,
                    "updated_at": now,
                }
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

                cur.execute(
                    "UPDATE fax_documents SET updated_at = %s WHERE fax_id = %s",
                    (now, fax_id),
                )
            conn.commit()
    except Exception as exc:
        logger.error("fax_match_persist_failed fax_id=%s error=%s", fax_id, exc)

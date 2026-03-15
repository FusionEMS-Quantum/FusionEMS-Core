from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any, cast

import boto3
import psycopg

from core_app.telnyx.client import TelnyxApiError, TelnyxNotConfigured, send_fax

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def lambda_handler(event: dict[str, Any], context: Any) -> None:
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            process_fax_send(body)
        except Exception as exc:
            logger.exception(
                "fax_send_record_failed message_id=%s error=%s",
                record.get("messageId", ""),
                exc,
            )
            raise


def process_fax_send(message: dict[str, Any]) -> None:
    fax_job_id = str(message.get("fax_job_id") or "").strip()
    tenant_id = str(message.get("tenant_id") or "").strip()
    correlation_id = str(message.get("correlation_id") or "").strip() or str(uuid.uuid4())

    if not fax_job_id or not tenant_id:
        logger.warning(
            "fax_send_missing_fields fax_job_id=%s tenant_id=%s correlation_id=%s",
            fax_job_id,
            tenant_id,
            correlation_id,
        )
        return

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error(
            "fax_send_disabled reason=DATABASE_URL_not_set fax_job_id=%s tenant_id=%s correlation_id=%s",
            fax_job_id,
            tenant_id,
            correlation_id,
        )
        return

    settings = _settings_from_env()

    job = _load_fax_job(database_url=database_url, tenant_id=tenant_id, fax_job_id=fax_job_id)
    if job is None:
        logger.warning(
            "fax_send_job_not_found fax_job_id=%s tenant_id=%s correlation_id=%s",
            fax_job_id,
            tenant_id,
            correlation_id,
        )
        return

    version = int(job["version"])
    data = cast(dict[str, Any], job.get("data") or {})

    status = str(data.get("status") or "").lower()
    if status in {"sent", "delivered", "failed", "canceled"}:
        logger.info(
            "fax_send_skip_already_terminal fax_job_id=%s tenant_id=%s status=%s correlation_id=%s",
            fax_job_id,
            tenant_id,
            status,
            correlation_id,
        )
        return

    to_number = str(
        data.get("to")
        or data.get("to_number")
        or data.get("destination")
        or data.get("destination_number")
        or ""
    ).strip()
    from_number = str(data.get("from") or data.get("from_number") or data.get("source") or "").strip()

    if not to_number:
        _patch_status(
            database_url=database_url,
            tenant_id=tenant_id,
            fax_job_id=fax_job_id,
            expected_version=version,
            patch={"status": "failed", "error": "missing_to_number", "failed_at": _utcnow()},
        )
        logger.warning(
            "fax_send_failed_missing_to fax_job_id=%s tenant_id=%s correlation_id=%s",
            fax_job_id,
            tenant_id,
            correlation_id,
        )
        return

    if not from_number:
        from_number = settings.get("TELNYX_FROM_NUMBER", "")

    if not from_number:
        _patch_status(
            database_url=database_url,
            tenant_id=tenant_id,
            fax_job_id=fax_job_id,
            expected_version=version,
            patch={"status": "failed", "error": "missing_from_number", "failed_at": _utcnow()},
        )
        logger.warning(
            "fax_send_failed_missing_from fax_job_id=%s tenant_id=%s correlation_id=%s",
            fax_job_id,
            tenant_id,
            correlation_id,
        )
        return

    connection_id = str(data.get("telnyx_connection_id") or data.get("connection_id") or "").strip()
    if not connection_id:
        connection_id = settings.get("TELNYX_FAX_CONNECTION_ID", "")

    api_key = settings.get("TELNYX_API_KEY", "")
    if not api_key or not connection_id:
        _patch_status(
            database_url=database_url,
            tenant_id=tenant_id,
            fax_job_id=fax_job_id,
            expected_version=version,
            patch={
                "status": "pending_configuration",
                "error": "telnyx_not_configured",
                "updated_at": _utcnow(),
            },
        )
        logger.warning(
            "fax_send_pending_config fax_job_id=%s tenant_id=%s api_key_set=%s connection_id_set=%s correlation_id=%s",
            fax_job_id,
            tenant_id,
            bool(api_key),
            bool(connection_id),
            correlation_id,
        )
        return

    media_url = str(data.get("media_url") or "").strip()
    if not media_url:
        media_url = _resolve_media_url(database_url=database_url, tenant_id=tenant_id, data=data)

    if not media_url:
        _patch_status(
            database_url=database_url,
            tenant_id=tenant_id,
            fax_job_id=fax_job_id,
            expected_version=version,
            patch={"status": "failed", "error": "missing_media", "failed_at": _utcnow()},
        )
        logger.warning(
            "fax_send_failed_missing_media fax_job_id=%s tenant_id=%s correlation_id=%s",
            fax_job_id,
            tenant_id,
            correlation_id,
        )
        return

    _patch_status(
        database_url=database_url,
        tenant_id=tenant_id,
        fax_job_id=fax_job_id,
        expected_version=version,
        patch={"status": "sending", "last_attempt_at": _utcnow()},
    )

    client_state = json.dumps(
        {"tenant_id": tenant_id, "fax_job_id": fax_job_id, "correlation_id": correlation_id},
        separators=(",", ":"),
    )

    try:
        resp = send_fax(
            api_key=api_key,
            connection_id=connection_id,
            to=to_number,
            from_=from_number,
            media_url=media_url,
            client_state=client_state,
        )
    except (TelnyxNotConfigured, TelnyxApiError) as exc:
        _patch_status_retry_safe(
            database_url=database_url,
            tenant_id=tenant_id,
            fax_job_id=fax_job_id,
            patch={
                "status": "failed",
                "error": f"telnyx_send_failed:{type(exc).__name__}",
                "failed_at": _utcnow(),
            },
        )
        logger.error(
            "fax_send_telnyx_failed fax_job_id=%s tenant_id=%s error=%s correlation_id=%s",
            fax_job_id,
            tenant_id,
            str(exc),
            correlation_id,
        )
        return
    except Exception:
        _patch_status_retry_safe(
            database_url=database_url,
            tenant_id=tenant_id,
            fax_job_id=fax_job_id,
            patch={"status": "failed", "error": "unexpected_error", "failed_at": _utcnow()},
        )
        logger.exception(
            "fax_send_unexpected_error fax_job_id=%s tenant_id=%s correlation_id=%s",
            fax_job_id,
            tenant_id,
            correlation_id,
        )
        return

    fax_id = str(((resp.get("data") or {}) if isinstance(resp, dict) else {}).get("id") or "")
    _patch_status_retry_safe(
        database_url=database_url,
        tenant_id=tenant_id,
        fax_job_id=fax_job_id,
        patch={
            "status": "sent",
            "sent_at": _utcnow(),
            "telnyx_fax_id": fax_id,
        },
    )

    logger.info(
        "fax_send_sent fax_job_id=%s tenant_id=%s telnyx_fax_id=%s correlation_id=%s",
        fax_job_id,
        tenant_id,
        fax_id,
        correlation_id,
    )


def _settings_from_env() -> dict[str, str]:
    return {
        "TELNYX_API_KEY": os.environ.get("TELNYX_API_KEY", ""),
        "TELNYX_FROM_NUMBER": os.environ.get("TELNYX_FROM_NUMBER", ""),
        "TELNYX_FAX_CONNECTION_ID": os.environ.get("TELNYX_FAX_CONNECTION_ID", ""),
        "S3_BUCKET_DOCS": os.environ.get("S3_BUCKET_DOCS", ""),
    }


def _load_fax_job(*, database_url: str, tenant_id: str, fax_job_id: str) -> dict[str, Any] | None:
    try:
        with (
            psycopg.connect(database_url) as conn,
            conn.cursor(row_factory=psycopg.rows.dict_row) as cur,
        ):
            cur.execute(
                "SELECT id, tenant_id, version, data FROM fax_jobs "
                "WHERE tenant_id = %s AND id = %s AND deleted_at IS NULL LIMIT 1",
                (tenant_id, fax_job_id),
            )
            row = cur.fetchone()
            return cast(dict[str, Any], row) if row else None
    except Exception as exc:
        logger.error(
            "fax_send_db_load_failed fax_job_id=%s tenant_id=%s error=%s",
            fax_job_id,
            tenant_id,
            exc,
        )
        return None


def _resolve_media_url(*, database_url: str, tenant_id: str, data: dict[str, Any]) -> str:
    # Priority 1: bucket + key already provided on the job
    bucket = str(data.get("bucket") or data.get("s3_bucket") or "").strip()
    s3_key = str(data.get("s3_key") or data.get("key") or "").strip()

    # Priority 2: document_id points to domination documents table
    if not (bucket and s3_key):
        document_id = str(data.get("document_id") or "").strip()
        if document_id:
            doc = _load_domination_record(
                database_url=database_url,
                table="documents",
                tenant_id=tenant_id,
                record_id=document_id,
            )
            if doc:
                doc_data = cast(dict[str, Any], doc.get("data") or {})
                bucket = str(doc_data.get("bucket") or bucket or "").strip()
                s3_key = str(doc_data.get("s3_key") or doc_data.get("key") or s3_key or "").strip()

    # Priority 3: fall back to env docs bucket if only key is present
    if not bucket and s3_key:
        bucket = os.environ.get("S3_BUCKET_DOCS", "")

    if not bucket or not s3_key:
        return ""

    try:
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        if not region:
            logger.warning(
                "fax_send_presign_skipped reason=AWS_REGION_not_set tenant_id=%s",
                tenant_id,
            )
            return ""
        s3 = boto3.client("s3", region_name=region)
        return str(
            s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": s3_key},
                ExpiresIn=3600,
            )
        )
    except Exception as exc:
        logger.error(
            "fax_send_presign_failed tenant_id=%s bucket_set=%s s3_key_present=%s error=%s",
            tenant_id,
            bool(bucket),
            bool(s3_key),
            exc,
        )
        return ""


def _load_domination_record(
    *, database_url: str, table: str, tenant_id: str, record_id: str
) -> dict[str, Any] | None:
    try:
        with (
            psycopg.connect(database_url) as conn,
            conn.cursor(row_factory=psycopg.rows.dict_row) as cur,
        ):
            cur.execute(
                f"SELECT id, tenant_id, version, data FROM {table} "  # nosec B608 — table is a caller-controlled literal ("documents"), never from user input
                "WHERE tenant_id = %s AND id = %s AND deleted_at IS NULL LIMIT 1",
                (tenant_id, record_id),
            )
            row = cur.fetchone()
            return cast(dict[str, Any], row) if row else None
    except Exception as exc:
        logger.warning(
            "fax_send_load_domination_record_failed table=%s record_id=%s tenant_id=%s error=%s",
            table,
            record_id,
            tenant_id,
            exc,
        )
        return None


def _patch_status(
    *,
    database_url: str,
    tenant_id: str,
    fax_job_id: str,
    expected_version: int,
    patch: dict[str, Any],
) -> bool:
    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE fax_jobs "
                    "SET version = version + 1, updated_at = now(), data = data || %s::jsonb "
                    "WHERE tenant_id = %s AND id = %s AND deleted_at IS NULL AND version = %s",
                    (
                        json.dumps(patch, default=str),
                        tenant_id,
                        fax_job_id,
                        expected_version,
                    ),
                )
            conn.commit()
        return True
    except Exception as exc:
        logger.warning(
            "fax_send_patch_failed fax_job_id=%s tenant_id=%s expected_version=%s error=%s",
            fax_job_id,
            tenant_id,
            expected_version,
            exc,
        )
        return False


def _patch_status_retry_safe(
    *, database_url: str, tenant_id: str, fax_job_id: str, patch: dict[str, Any]
) -> None:
    # Best-effort: handle version conflicts by refetching once.
    job = _load_fax_job(database_url=database_url, tenant_id=tenant_id, fax_job_id=fax_job_id)
    if not job:
        return
    expected_version = int(job["version"])
    if _patch_status(
        database_url=database_url,
        tenant_id=tenant_id,
        fax_job_id=fax_job_id,
        expected_version=expected_version,
        patch=patch,
    ):
        return

    job2 = _load_fax_job(database_url=database_url, tenant_id=tenant_id, fax_job_id=fax_job_id)
    if not job2:
        return
    expected_version2 = int(job2["version"])
    _patch_status(
        database_url=database_url,
        tenant_id=tenant_id,
        fax_job_id=fax_job_id,
        expected_version=expected_version2,
        patch=patch,
    )

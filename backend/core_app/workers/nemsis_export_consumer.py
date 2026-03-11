"""NEMSIS Export Consumer Worker — polls SQS queue and submits ePCR XML to state API.

Processes messages from the NEMSIS export queue:
- nemsis.epcr.export → submits individual ePCR XML
- nemsis.batch.export → submits batch ePCR XML

Updates submission records through the full lifecycle:
PENDING → SUBMITTED → ACCEPTED / REJECTED
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

NEMSIS_EXPORT_QUEUE_URL = os.environ.get("NEMSIS_EXPORT_QUEUE_URL", "")
_POLL_INTERVAL_SECONDS = 15
_VISIBILITY_TIMEOUT = 120
_MAX_MESSAGES = 5


async def nemsis_export_consumer_loop(stop: asyncio.Event) -> None:
    """Main consumer loop — runs until stop event is set."""
    await asyncio.sleep(15)  # initial delay
    logger.info(
        "nemsis_export_consumer_started queue_url=%s",
        NEMSIS_EXPORT_QUEUE_URL or "(not set)",
    )

    if not NEMSIS_EXPORT_QUEUE_URL:
        logger.warning("nemsis_export_consumer_disabled reason=NEMSIS_EXPORT_QUEUE_URL_not_set")
        return

    import boto3

    sqs = boto3.client("sqs")

    while not stop.is_set():
        try:
            resp = sqs.receive_message(
                QueueUrl=NEMSIS_EXPORT_QUEUE_URL,
                MaxNumberOfMessages=_MAX_MESSAGES,
                WaitTimeSeconds=10,
                VisibilityTimeout=_VISIBILITY_TIMEOUT,
                AttributeNames=["All"],
            )

            messages = resp.get("Messages", [])
            if not messages:
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                continue

            for msg in messages:
                receipt = msg.get("ReceiptHandle", "")
                body: dict[str, Any] = {}
                try:
                    body = json.loads(msg.get("Body", "{}"))
                    await _process_message(body)
                    sqs.delete_message(
                        QueueUrl=NEMSIS_EXPORT_QUEUE_URL,
                        ReceiptHandle=receipt,
                    )
                except Exception:
                    logger.exception(
                        "nemsis_export_consumer_message_failed job_id=%s",
                        body.get("job_id", "unknown"),
                    )

        except Exception:
            logger.exception("nemsis_export_consumer_poll_error")
            await asyncio.sleep(_POLL_INTERVAL_SECONDS * 2)


async def _process_message(body: dict[str, Any]) -> None:
    """Route message to the appropriate handler."""
    job_type = body.get("job_type", "")
    job_id = body.get("job_id", str(uuid.uuid4()))
    correlation_id = body.get("correlation_id") or job_id

    logger.info(
        "nemsis_export_processing job_id=%s job_type=%s tenant_id=%s",
        job_id,
        job_type,
        body.get("tenant_id", ""),
    )

    if job_type == "nemsis.epcr.export":
        await _handle_epcr_export(body, correlation_id)
    elif job_type == "nemsis.batch.export":
        await _handle_batch_export(body, correlation_id)
    else:
        logger.warning(
            "nemsis_export_unknown_job_type job_type=%s job_id=%s", job_type, job_id
        )


async def _handle_epcr_export(body: dict[str, Any], correlation_id: str) -> None:
    """Build ePCR XML and submit to NEMSIS state API."""
    from core_app.integrations.state_api_client import NEMSISStateClient
    from core_app.services.nemsis_service import NEMSISExportService

    job_id = body.get("job_id", "")
    record = body.get("payload", {})

    svc = NEMSISExportService()

    # Validate completeness before submission
    validation = svc.validate_completeness(record)
    if not validation["complete"]:
        logger.warning(
            "nemsis_epcr_incomplete job_id=%s missing=%s correlation_id=%s",
            job_id,
            validation["missing_fields"],
            correlation_id,
        )
        await _update_submission_status(
            job_id=job_id,
            tenant_id=body.get("tenant_id", ""),
            status="validation_failed",
            response={
                "validation": validation,
                "submitted": False,
            },
            correlation_id=correlation_id,
        )
        return

    xml_bytes = svc.build_epcr_xml(record)

    client = NEMSISStateClient()
    result = await client.submit_epcr(xml_bytes, correlation_id=correlation_id)

    status = "accepted" if result.success else "rejected"
    await _update_submission_status(
        job_id=job_id,
        tenant_id=body.get("tenant_id", ""),
        status=status,
        response=result.to_dict(),
        correlation_id=correlation_id,
    )


async def _handle_batch_export(body: dict[str, Any], correlation_id: str) -> None:
    """Build batch ePCR XML and submit to NEMSIS state API."""
    from core_app.integrations.state_api_client import NEMSISStateClient
    from core_app.services.nemsis_service import NEMSISExportService

    job_id = body.get("job_id", "")
    records = body.get("payload", {}).get("records", [])

    if not records:
        logger.warning(
            "nemsis_batch_empty job_id=%s correlation_id=%s", job_id, correlation_id
        )
        return

    svc = NEMSISExportService()
    xml_bytes = svc.build_batch_xml(records)

    client = NEMSISStateClient()
    result = await client.submit_batch(xml_bytes, correlation_id=correlation_id)

    status = "accepted" if result.success else "rejected"
    await _update_submission_status(
        job_id=job_id,
        tenant_id=body.get("tenant_id", ""),
        status=status,
        response=result.to_dict(),
        correlation_id=correlation_id,
    )


async def _update_submission_status(
    *,
    job_id: str,
    tenant_id: str,
    status: str,
    response: dict[str, Any],
    correlation_id: str,
) -> None:
    """Update nemsis_submission_results with submission outcome."""
    try:
        from core_app.db.session import get_db_session_ctx
        from core_app.services.domination_service import DominationService
        from core_app.services.event_publisher import get_event_publisher

        with get_db_session_ctx() as db:
            svc = DominationService(db, get_event_publisher())
            await svc.update(
                table="nemsis_submission_results",
                record_id=uuid.UUID(job_id) if job_id else uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id) if tenant_id else uuid.UUID(int=0),
                actor_user_id=uuid.UUID(int=0),
                expected_version=0,
                patch={
                    "status": status,
                    "submitted_at": datetime.now(UTC).isoformat(),
                    "response_blob": json.dumps(response),
                    "correlation_id": correlation_id,
                },
                correlation_id=correlation_id,
            )

        logger.info(
            "nemsis_submission_updated job_id=%s status=%s correlation_id=%s",
            job_id,
            status,
            correlation_id,
        )
    except Exception:
        logger.exception(
            "nemsis_submission_update_failed job_id=%s correlation_id=%s",
            job_id,
            correlation_id,
        )

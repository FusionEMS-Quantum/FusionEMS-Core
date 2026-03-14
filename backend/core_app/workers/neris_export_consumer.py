"""NERIS Export Consumer Worker — polls SQS queue and submits to state API.

Processes messages from the NERIS export queue:
- neris.entity.export → submits department/entity registration
- neris.incident.export → generates bundle and submits incident report
- neris.cad.linkage → submits CAD-linked incident data

Updates export job status through the full lifecycle:
DRAFT → VALIDATED → QUEUED → SUBMITTED → ACCEPTED / REJECTED
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

NERIS_EXPORT_QUEUE_URL = os.environ.get("NERIS_EXPORT_QUEUE_URL", "")
_POLL_INTERVAL_SECONDS = 15
_VISIBILITY_TIMEOUT = 120
_MAX_MESSAGES = 5


async def neris_export_consumer_loop(stop: asyncio.Event) -> None:
    """Main consumer loop — runs until stop event is set."""
    await asyncio.sleep(10)  # initial delay to let app boot
    logger.info("neris_export_consumer_started queue_url=%s", NERIS_EXPORT_QUEUE_URL or "(not set)")

    if not NERIS_EXPORT_QUEUE_URL:
        logger.warning("neris_export_consumer_disabled reason=NERIS_EXPORT_QUEUE_URL_not_set")
        return

    import boto3

    sqs = boto3.client("sqs")

    while not stop.is_set():
        try:
            resp = sqs.receive_message(
                QueueUrl=NERIS_EXPORT_QUEUE_URL,
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
                        QueueUrl=NERIS_EXPORT_QUEUE_URL,
                        ReceiptHandle=receipt,
                    )
                except Exception:
                    logger.exception(
                        "neris_export_consumer_message_failed job_id=%s",
                        body.get("job_id", "unknown"),
                    )
                    # Message returns to queue after visibility timeout

        except Exception:
            logger.exception("neris_export_consumer_poll_error")
            await asyncio.sleep(_POLL_INTERVAL_SECONDS * 2)


async def _process_message(body: dict[str, Any]) -> None:
    """Route message to the appropriate handler based on job_type."""
    job_type = body.get("job_type", "")
    job_id = body.get("job_id", str(uuid.uuid4()))
    tenant_id = body.get("tenant_id", "")
    department_id = body.get("department_id", "")
    correlation_id = body.get("correlation_id") or job_id

    logger.info(
        "neris_export_processing job_id=%s job_type=%s tenant_id=%s department_id=%s",
        job_id,
        job_type,
        tenant_id,
        department_id,
    )

    if job_type == "neris.entity.export":
        await _handle_entity_export(body, correlation_id)
    elif job_type == "neris.incident.export":
        await _handle_incident_export(body, correlation_id)
    elif job_type == "neris.cad.linkage":
        await _handle_cad_linkage(body, correlation_id)
    else:
        logger.warning(
            "neris_export_unknown_job_type job_type=%s job_id=%s", job_type, job_id
        )


async def _handle_entity_export(body: dict[str, Any], correlation_id: str) -> None:
    """Submit department entity registration to NERIS state API."""
    from core_app.integrations.state_api_client import NERISStateClient

    job_id = body.get("job_id", "")
    payload = body.get("payload", {})

    client = NERISStateClient()
    result = await client.submit_entity(payload, correlation_id=correlation_id)

    await _update_export_job_status(
        job_id=job_id,
        tenant_id=body.get("tenant_id", ""),
        success=result.success,
        status_code=result.status_code,
        response=result.to_dict(),
        correlation_id=correlation_id,
    )


async def _handle_incident_export(body: dict[str, Any], correlation_id: str) -> None:
    """Generate bundle and submit incident report to NERIS state API."""
    from core_app.integrations.state_api_client import NERISStateClient

    job_id = body.get("job_id", "")
    payload = body.get("payload", {})

    client = NERISStateClient()
    result = await client.submit_incident(payload, correlation_id=correlation_id)

    await _update_export_job_status(
        job_id=job_id,
        tenant_id=body.get("tenant_id", ""),
        success=result.success,
        status_code=result.status_code,
        response=result.to_dict(),
        correlation_id=correlation_id,
    )


async def _handle_cad_linkage(body: dict[str, Any], correlation_id: str) -> None:
    """Submit CAD-linked incident data to NERIS."""
    from core_app.integrations.state_api_client import NERISStateClient

    job_id = body.get("job_id", "")
    payload = body.get("payload", {})

    client = NERISStateClient()
    result = await client.submit_incident(payload, correlation_id=correlation_id)

    await _update_export_job_status(
        job_id=job_id,
        tenant_id=body.get("tenant_id", ""),
        success=result.success,
        status_code=result.status_code,
        response=result.to_dict(),
        correlation_id=correlation_id,
    )


async def _update_export_job_status(
    *,
    job_id: str,
    tenant_id: str,
    success: bool,
    status_code: int,
    response: dict[str, Any],
    correlation_id: str,
) -> None:
    """Update the neris_export_jobs record with submission outcome."""
    new_state = "ACCEPTED" if success else "REJECTED"

    try:
        from core_app.db.session import get_db_session_ctx
        from core_app.services.domination_service import DominationService
        from core_app.services.event_publisher import get_event_publisher

        with get_db_session_ctx() as db:
            svc = DominationService(db, get_event_publisher())
            await svc.update(
                table="neris_export_jobs",
                record_id=uuid.UUID(job_id) if job_id else uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id) if tenant_id else uuid.UUID(int=0),
                actor_user_id=uuid.UUID(int=0),
                expected_version=0,
                patch={
                    "status": new_state.lower(),
                    "submitted_at": datetime.now(UTC).isoformat(),
                    "response_status_code": status_code,
                    "response_blob": json.dumps(response),
                    "correlation_id": correlation_id,
                },
                correlation_id=correlation_id,
            )

        logger.info(
            "neris_export_job_updated job_id=%s state=%s http_status=%d correlation_id=%s",
            job_id,
            new_state,
            status_code,
            correlation_id,
        )
    except Exception:
        logger.exception(
            "neris_export_job_update_failed job_id=%s correlation_id=%s",
            job_id,
            correlation_id,
        )

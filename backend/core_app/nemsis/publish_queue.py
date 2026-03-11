"""NEMSIS Export Queue — enqueue ePCR export jobs to SQS for async processing."""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

NEMSIS_EXPORT_QUEUE_URL = os.environ.get("NEMSIS_EXPORT_QUEUE_URL", "")


class NEMSISPublishQueue:
    """Publishes ePCR export jobs to SQS for the NEMSIS consumer worker."""

    def __init__(self, sqs_client=None, queue_url: str | None = None):  # type: ignore[no-untyped-def]
        self._queue_url = queue_url or NEMSIS_EXPORT_QUEUE_URL
        self._sqs = sqs_client

    def _get_sqs(self):  # type: ignore[no-untyped-def]
        if self._sqs is None:
            import boto3
            self._sqs = boto3.client("sqs")
        return self._sqs

    def enqueue_epcr_export(
        self, tenant_id: str, record: dict, correlation_id: str | None = None
    ) -> str:
        """Enqueue a single ePCR record for NEMSIS export."""
        return self._enqueue(
            job_type="nemsis.epcr.export",
            tenant_id=tenant_id,
            payload=record,
            correlation_id=correlation_id,
        )

    def enqueue_batch_export(
        self, tenant_id: str, records: list[dict], correlation_id: str | None = None
    ) -> str:
        """Enqueue a batch of ePCR records for NEMSIS export."""
        return self._enqueue(
            job_type="nemsis.batch.export",
            tenant_id=tenant_id,
            payload={"records": records},
            correlation_id=correlation_id,
        )

    def _enqueue(
        self,
        job_type: str,
        tenant_id: str,
        payload: dict,
        correlation_id: str | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        cid = correlation_id or job_id
        message = {
            "job_id": job_id,
            "job_type": job_type,
            "tenant_id": tenant_id,
            "payload": payload,
            "correlation_id": cid,
            "created_at": datetime.now(UTC).isoformat(),
        }

        if not self._queue_url:
            logger.warning(
                "NEMSIS_EXPORT_QUEUE_URL not set; message logged but not sent: %s", job_type
            )
            return job_id

        try:
            sqs = self._get_sqs()
            sqs.send_message(
                QueueUrl=self._queue_url,
                MessageBody=json.dumps(message),
            )
            logger.info("nemsis_queue_enqueued job_id=%s type=%s", job_id, job_type)
        except Exception:
            logger.exception("nemsis_queue_failed job_id=%s type=%s", job_id, job_type)

        return job_id

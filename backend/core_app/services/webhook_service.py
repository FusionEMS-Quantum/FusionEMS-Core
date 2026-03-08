"""Webhook Service — delivery, idempotency, retry queue, dead letter.

Handles outbound webhook delivery with HMAC signature verification,
idempotency key deduplication, exponential backoff retry, and DLQ.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Retry config
_MAX_RETRIES = 5
_BACKOFF_BASE_SECONDS = 2.0
_DELIVERY_TIMEOUT_SECONDS = 10


class WebhookDelivery:
    """In-memory representation of a single webhook delivery attempt."""

    def __init__(
        self,
        *,
        delivery_id: uuid.UUID | None = None,
        event_type: str,
        payload: dict[str, Any],
        target_url: str,
        secret: str,
        tenant_id: uuid.UUID,
        idempotency_key: str,
    ) -> None:
        self.delivery_id = delivery_id or uuid.uuid4()
        self.event_type = event_type
        self.payload = payload
        self.target_url = target_url
        self.secret = secret
        self.tenant_id = tenant_id
        self.idempotency_key = idempotency_key
        self.attempt = 0
        self.last_status_code: int | None = None
        self.last_error: str | None = None
        self.delivered = False
        self.dead_lettered = False


class WebhookService:
    """Manages webhook delivery with retry and dead-letter queue."""

    def __init__(self) -> None:
        self._seen_keys: set[str] = set()
        self._dead_letter: list[WebhookDelivery] = []

    def compute_signature(self, *, payload_bytes: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 signature for webhook payload."""
        return hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

    def verify_signature(
        self, *, payload_bytes: bytes, secret: str, signature: str
    ) -> bool:
        """Verify an inbound webhook signature."""
        expected = self.compute_signature(payload_bytes=payload_bytes, secret=secret)
        return hmac.compare_digest(expected, signature)

    def is_duplicate(self, idempotency_key: str) -> bool:
        """Check if this event was already processed (idempotency guard)."""
        return idempotency_key in self._seen_keys

    async def deliver(self, delivery: WebhookDelivery) -> dict[str, Any]:
        """Attempt delivery with exponential backoff retry.

        Returns delivery result dict. Dead-letters after max retries.
        """
        if self.is_duplicate(delivery.idempotency_key):
            logger.info(
                "webhook_duplicate_skipped",
                extra={"idempotency_key": delivery.idempotency_key},
            )
            return {
                "delivery_id": str(delivery.delivery_id),
                "status": "duplicate_skipped",
                "idempotency_key": delivery.idempotency_key,
            }

        payload_bytes = json.dumps(delivery.payload, default=str).encode("utf-8")
        signature = self.compute_signature(
            payload_bytes=payload_bytes, secret=delivery.secret
        )
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": delivery.event_type,
            "X-Idempotency-Key": delivery.idempotency_key,
            "X-Delivery-ID": str(delivery.delivery_id),
        }

        while delivery.attempt < _MAX_RETRIES:
            delivery.attempt += 1
            try:
                async with httpx.AsyncClient(timeout=_DELIVERY_TIMEOUT_SECONDS) as client:
                    resp = await client.post(
                        delivery.target_url,
                        content=payload_bytes,
                        headers=headers,
                    )
                delivery.last_status_code = resp.status_code
                if 200 <= resp.status_code < 300:
                    delivery.delivered = True
                    self._seen_keys.add(delivery.idempotency_key)
                    logger.info(
                        "webhook_delivered",
                        extra={
                            "delivery_id": str(delivery.delivery_id),
                            "attempt": delivery.attempt,
                            "status_code": resp.status_code,
                        },
                    )
                    return {
                        "delivery_id": str(delivery.delivery_id),
                        "status": "delivered",
                        "attempt": delivery.attempt,
                        "status_code": resp.status_code,
                    }
                delivery.last_error = f"HTTP {resp.status_code}"
            except Exception as exc:
                delivery.last_error = str(exc)
                logger.warning(
                    "webhook_delivery_failed",
                    extra={
                        "delivery_id": str(delivery.delivery_id),
                        "attempt": delivery.attempt,
                        "error": str(exc),
                    },
                )

            # Exponential backoff
            if delivery.attempt < _MAX_RETRIES:
                backoff = _BACKOFF_BASE_SECONDS ** delivery.attempt
                import asyncio
                await asyncio.sleep(min(backoff, 30.0))

        # Dead letter
        delivery.dead_lettered = True
        self._dead_letter.append(delivery)
        logger.error(
            "webhook_dead_lettered",
            extra={
                "delivery_id": str(delivery.delivery_id),
                "attempts": delivery.attempt,
                "last_error": delivery.last_error,
            },
        )
        return {
            "delivery_id": str(delivery.delivery_id),
            "status": "dead_lettered",
            "attempts": delivery.attempt,
            "last_error": delivery.last_error,
        }

    def get_dead_letter_queue(self) -> list[dict[str, Any]]:
        """Return dead-lettered deliveries for inspection/retry."""
        return [
            {
                "delivery_id": str(d.delivery_id),
                "event_type": d.event_type,
                "target_url": d.target_url,
                "attempts": d.attempt,
                "last_error": d.last_error,
                "idempotency_key": d.idempotency_key,
            }
            for d in self._dead_letter
        ]

    async def retry_dead_letter(self, delivery_id: str) -> dict[str, Any]:
        """Retry a specific dead-lettered delivery."""
        for d in self._dead_letter:
            if str(d.delivery_id) == delivery_id:
                d.attempt = 0
                d.dead_lettered = False
                self._dead_letter.remove(d)
                return await self.deliver(d)
        return {"error": "delivery_not_found"}

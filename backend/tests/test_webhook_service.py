"""Tests for WebhookService — HMAC signing, idempotency, retry logic."""
import uuid

import pytest

from core_app.services.webhook_service import WebhookService


@pytest.fixture()
def service() -> WebhookService:
    return WebhookService()


# ── Signature ────────────────────────────────────────────────────────────────


def test_compute_and_verify_signature(service: WebhookService) -> None:
    payload = b'{"event":"incident.created","id":"123"}'
    secret = "test-secret"
    sig = service.compute_signature(payload_bytes=payload, secret=secret)
    assert sig
    assert service.verify_signature(payload_bytes=payload, secret=secret, signature=sig) is True


def test_verify_wrong_signature(service: WebhookService) -> None:
    payload = b'{"event":"incident.created","id":"123"}'
    assert service.verify_signature(payload_bytes=payload, secret="sec", signature="wrong") is False


# ── Idempotency ──────────────────────────────────────────────────────────────


def test_duplicate_detection(service: WebhookService) -> None:
    key = str(uuid.uuid4())
    assert service.is_duplicate(key) is False
    service._seen_keys.add(key)
    assert service.is_duplicate(key) is True


# ── Dead Letter ──────────────────────────────────────────────────────────────


def test_dead_letter_queue_initially_empty(service: WebhookService) -> None:
    assert service.get_dead_letter_queue() == []

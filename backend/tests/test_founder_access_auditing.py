"""Founder-only access boundary auditing tests.

Verifies that:
  1. A non-founder (admin) receives HTTP 403 when hitting any founder-gated endpoint.
  2. The deny decision is persisted to `access_audit_logs` by `AccessAuditService.log_access`
     — once per request, with decision=DENIED.
  3. An authenticated founder receives HTTP 200 (or non-403) from the same endpoint.
  4. The allow decision is persisted to `access_audit_logs` with decision=ALLOWED.

These tests exercise the real `require_founder_only_audited()` dependency chain with
`AccessAuditService.log_access` mocked at the class level so no database is required.
"""
from __future__ import annotations

import uuid
from collections.abc import Generator
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core_app.api.dependencies import db_session_dependency, get_current_user

# Use the main founder router which carries the router-level
# `dependencies=[Depends(require_founder_only_audited())]` gate.
from core_app.api.founder_router import router as founder_router
from core_app.models.access_audit_log import AccessDecision
from core_app.schemas.auth import CurrentUser

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_user(role: str) -> CurrentUser:
    return CurrentUser(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role=role,
    )


class _DBStub:
    """Minimal SQLAlchemy session stub — returns empty lists for all queries."""

    def execute(self, *_args: object, **_kwargs: object) -> _DBStub:
        return self

    def mappings(self) -> _DBStub:
        return self

    def all(self) -> list[object]:
        return []

    def scalars(self) -> _DBStub:
        return self

    def scalar_one_or_none(self) -> None:
        return None

    def first(self) -> None:
        return None


def _build_app(current_user: CurrentUser) -> FastAPI:
    app = FastAPI()
    app.include_router(founder_router)

    def _override_db() -> Generator[_DBStub, None, None]:
        yield _DBStub()

    app.dependency_overrides[db_session_dependency] = _override_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    return app


# ── deny path ────────────────────────────────────────────────────────────────


def test_non_founder_receives_403_and_deny_is_audited() -> None:
    """Admin role must be denied (403) and the deny must be recorded in audit log."""
    admin_user = _make_user("admin")
    app = _build_app(admin_user)
    client = TestClient(app, raise_server_exceptions=False)

    mock_log = MagicMock()
    with patch(
        "core_app.services.access_audit_service.AccessAuditService.log_access",
        mock_log,
    ):
        response = client.get("/api/v1/founder/business/expense-ledger")

    assert response.status_code == 403, (
        f"Expected 403 for admin role, got {response.status_code}"
    )

    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args.kwargs

    assert call_kwargs["decision"] == AccessDecision.DENIED, (
        f"Expected DENIED, got {call_kwargs['decision']}"
    )
    assert call_kwargs["actor_role"] == "admin"
    assert call_kwargs["required_role"] == "founder"
    assert call_kwargs["reason"] == "founder_only"
    assert call_kwargs["actor_user_id"] == admin_user.user_id


def test_billing_role_receives_403_and_deny_is_audited() -> None:
    """Billing role must also be denied — it must never access founder surfaces."""
    billing_user = _make_user("billing")
    app = _build_app(billing_user)
    client = TestClient(app, raise_server_exceptions=False)

    mock_log = MagicMock()
    with patch(
        "core_app.services.access_audit_service.AccessAuditService.log_access",
        mock_log,
    ):
        response = client.get("/api/v1/founder/business/invoices")

    assert response.status_code == 403
    call_kwargs = mock_log.call_args.kwargs
    assert call_kwargs["decision"] == AccessDecision.DENIED
    assert call_kwargs["actor_role"] == "billing"


# ── allow path ───────────────────────────────────────────────────────────────


def test_founder_is_allowed_and_allow_is_audited() -> None:
    """Founder role must pass the gate and the allow must be recorded in audit log."""
    founder_user = _make_user("founder")
    app = _build_app(founder_user)
    client = TestClient(app, raise_server_exceptions=False)

    mock_log = MagicMock()
    with patch(
        "core_app.services.access_audit_service.AccessAuditService.log_access",
        mock_log,
    ):
        response = client.get("/api/v1/founder/business/expense-ledger")

    # 200 or any non-auth failure — the gate passed
    assert response.status_code != 403, (
        f"Founder role must not be denied; got {response.status_code}: {response.text}"
    )
    assert response.status_code != 401

    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args.kwargs
    assert call_kwargs["decision"] == AccessDecision.ALLOWED
    assert call_kwargs["actor_role"] == "founder"
    assert call_kwargs["actor_user_id"] == founder_user.user_id

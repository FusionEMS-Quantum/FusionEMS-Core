"""Tests for the AppError taxonomy and response formatting."""
from core_app.core.errors import AppError, ErrorCodes


def test_app_error_to_response_with_trace_id() -> None:
    err = AppError(code="TEST_ERR", message="Something broke", status_code=500)
    resp = err.to_response(trace_id="abc-123")
    assert resp["error"]["code"] == "TEST_ERR"
    assert resp["error"]["message"] == "Something broke"
    assert resp["error"]["trace_id"] == "abc-123"
    assert resp["error"]["details"] == {}


def test_app_error_to_response_with_details() -> None:
    err = AppError(
        code="VALIDATION",
        message="Invalid input",
        status_code=422,
        details={"field": "name", "constraint": "required"},
    )
    resp = err.to_response(trace_id=None)
    assert resp["error"]["details"]["field"] == "name"
    assert resp["error"]["trace_id"] is None


def test_app_error_to_response_no_trace() -> None:
    err = AppError(code="NOT_FOUND", message="Resource missing", status_code=404)
    resp = err.to_response(trace_id=None)
    assert resp["error"]["trace_id"] is None


def test_error_codes_exist() -> None:
    assert ErrorCodes.INCIDENT_NOT_FOUND == "INCIDENT_NOT_FOUND"
    assert ErrorCodes.TENANT_SCOPE_REQUIRED == "TENANT_SCOPE_REQUIRED"
    assert ErrorCodes.CONCURRENCY_CONFLICT == "CONCURRENCY_CONFLICT"

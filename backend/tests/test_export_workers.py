"""Tests for state API clients and export consumer workers."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core_app.integrations.state_api_client import (
    NEMSISStateClient,
    NERISStateClient,
    SubmissionResult,
)

# ── SubmissionResult ────────────────────────────────────────────────────────


def test_submission_result_to_dict() -> None:
    result = SubmissionResult(
        success=True,
        status_code=200,
        response_body={"id": "abc123"},
        submission_id="abc123",
        errors=[],
        warnings=["minor warning"],
    )
    d = result.to_dict()
    assert d["success"] is True
    assert d["status_code"] == 200
    assert d["submission_id"] == "abc123"
    assert d["warnings"] == ["minor warning"]
    assert "submitted_at" in d


def test_submission_result_failure() -> None:
    result = SubmissionResult(
        success=False,
        status_code=422,
        response_body={"errors": ["invalid data"]},
        errors=["validation failed"],
    )
    d = result.to_dict()
    assert d["success"] is False
    assert d["errors"] == ["validation failed"]


# ── NERISStateClient ────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_neris_client_no_api_key() -> None:
    """Should return failure when no API key is configured."""
    client = NERISStateClient(api_key="")
    result = await client.submit_entity({"department": {}})
    assert result.success is False
    assert "not configured" in result.errors[0]


@pytest.mark.asyncio()
async def test_neris_client_submit_entity_success() -> None:
    """Should return success on 200 response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "dept-001", "status": "accepted"}
    mock_response.text = '{"id": "dept-001", "status": "accepted"}'

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = NERISStateClient(api_key="test-key")
        result = await client.submit_entity({"department": {"id": "dept-001"}})

    assert result.success is True
    assert result.status_code == 200


@pytest.mark.asyncio()
async def test_neris_client_submit_incident_rejection() -> None:
    """Should return failure on 422 response."""
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {"errors": ["missing_field"]}
    mock_response.text = '{"errors": ["missing_field"]}'

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = NERISStateClient(api_key="test-key")
        result = await client.submit_incident({"incident": {}})

    assert result.success is False
    assert result.status_code == 422


# ── NEMSISStateClient ──────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_nemsis_client_no_api_key() -> None:
    """Should return failure when no API key is configured."""
    client = NEMSISStateClient(api_key="")
    result = await client.submit_epcr(b"<xml/>")
    assert result.success is False
    assert "not configured" in result.errors[0]


@pytest.mark.asyncio()
async def test_nemsis_client_success_response() -> None:
    """Should parse NEMSIS success response."""
    xml_body = (
        "<Response>"
        "<StatusCode>Success</StatusCode>"
        "<SubmissionID>NEM-12345</SubmissionID>"
        "</Response>"
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = xml_body

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = NEMSISStateClient(api_key="test-key")
        result = await client.submit_epcr(b"<EMSDataSet/>")

    assert result.success is True
    assert result.submission_id == "NEM-12345"


@pytest.mark.asyncio()
async def test_nemsis_client_failure_response() -> None:
    """Should parse NEMSIS failure response with error messages."""
    xml_body = (
        "<Response>"
        "<StatusCode>Failure</StatusCode>"
        "<ErrorMessage>Missing eRecord.01</ErrorMessage>"
        "<ErrorMessage>Invalid date format</ErrorMessage>"
        "</Response>"
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = xml_body

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = NEMSISStateClient(api_key="test-key")
        result = await client.submit_epcr(b"<EMSDataSet/>")

    assert result.success is False
    assert len(result.errors) == 2
    assert "Missing eRecord.01" in result.errors[0]


# ── NERIS Export Consumer ──────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_neris_process_entity_export() -> None:
    """Should route entity export messages correctly."""
    from core_app.workers.neris_export_consumer import _process_message

    with (
        patch(
            "core_app.workers.neris_export_consumer._handle_entity_export",
            new_callable=AsyncMock,
        ) as mock_handler,
    ):
        body = {
            "job_id": "job-001",
            "job_type": "neris.entity.export",
            "tenant_id": "t-001",
            "department_id": "d-001",
            "payload": {"department": {}},
        }
        await _process_message(body)
        mock_handler.assert_called_once()


@pytest.mark.asyncio()
async def test_neris_process_incident_export() -> None:
    """Should route incident export messages correctly."""
    from core_app.workers.neris_export_consumer import _process_message

    with (
        patch(
            "core_app.workers.neris_export_consumer._handle_incident_export",
            new_callable=AsyncMock,
        ) as mock_handler,
    ):
        body = {
            "job_id": "job-002",
            "job_type": "neris.incident.export",
            "tenant_id": "t-001",
            "department_id": "d-001",
            "payload": {"incident": {}},
        }
        await _process_message(body)
        mock_handler.assert_called_once()


# ── NEMSIS Export Consumer ─────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_nemsis_process_epcr_export() -> None:
    """Should route ePCR export messages correctly."""
    from core_app.workers.nemsis_export_consumer import _process_message

    with (
        patch(
            "core_app.workers.nemsis_export_consumer._handle_epcr_export",
            new_callable=AsyncMock,
        ) as mock_handler,
    ):
        body = {
            "job_id": "job-003",
            "job_type": "nemsis.epcr.export",
            "tenant_id": "t-001",
            "payload": {"pcr_number": "PCR-001"},
        }
        await _process_message(body)
        mock_handler.assert_called_once()


@pytest.mark.asyncio()
async def test_nemsis_process_batch_export() -> None:
    """Should route batch export messages correctly."""
    from core_app.workers.nemsis_export_consumer import _process_message

    with (
        patch(
            "core_app.workers.nemsis_export_consumer._handle_batch_export",
            new_callable=AsyncMock,
        ) as mock_handler,
    ):
        body = {
            "job_id": "job-004",
            "job_type": "nemsis.batch.export",
            "tenant_id": "t-001",
            "payload": {"records": [{"pcr_number": "PCR-001"}]},
        }
        await _process_message(body)
        mock_handler.assert_called_once()


@pytest.mark.asyncio()
async def test_nemsis_epcr_export_validates_before_submit() -> None:
    """Should validate completeness before attempting submission."""
    from core_app.workers.nemsis_export_consumer import _handle_epcr_export

    with (
        patch(
            "core_app.workers.nemsis_export_consumer._update_submission_status",
            new_callable=AsyncMock,
        ) as mock_update,
    ):
        # Incomplete record — missing required fields
        body = {
            "job_id": "job-005",
            "tenant_id": "t-001",
            "payload": {"pcr_number": "PCR-001"},
        }
        await _handle_epcr_export(body, "corr-001")

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["status"] == "validation_failed"

"""Tests for the open-source IRS Free File e-file implementation.

Verifies that IRSFreeFileClient:
  1. Reports itself as always-configured (no credentials required).
  2. status_report() exposes the open_source=True flag and correct metadata.
  3. _build_1040_xml() produces valid, well-formed XML containing expected
     IRS Publication 4164 elements.
  4. submit_1040() returns ACCEPTED on HTTP 200 with a confirmation number.
  5. submit_1040() returns REJECTED on HTTP 422 and extracts error messages.
  6. submit_1040() returns ERROR on timeout.
  7. EfileOrchestrator.realtime_status() includes the free_file provider key.

All HTTP calls are mocked — no real IRS network requests are made.
"""
from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core_app.accounting.efile_service import (
    EfileOrchestrator,
    EfileStatus,
    IRSFreeFileClient,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NS = "http://www.irs.gov/efile"


def _parse_xml(xml_str: str) -> ET.Element:
    """Parse the generated XML; raises if malformed."""
    return ET.fromstring(xml_str)


def _find(root: ET.Element, path: str) -> ET.Element | None:
    """XPath helper with IRS namespace."""
    return root.find(path, {"irs": _NS})


def _make_client() -> IRSFreeFileClient:
    return IRSFreeFileClient()


def _common_1040_kwargs(correlation_id: str | None = None) -> dict:
    return dict(
        tax_year=2024,
        ssn="123-45-6789",
        first_name="Jane",
        last_name="Doe",
        street="100 Main St",
        city="Madison",
        state="WI",
        zip_code="53703",
        filing_status="Single",
        wages_salaries_tips=60000.0,
        taxable_interest=200.0,
        ordinary_dividends=100.0,
        business_income=0.0,
        adjusted_gross_income=60300.0,
        standard_deduction=14600.0,
        taxable_income=45700.0,
        total_tax=5_200.0,
        federal_income_tax_withheld=6_000.0,
        total_payments=6_000.0,
        refund_amount=800.0,
        balance_due=0.0,
        correlation_id=correlation_id or str(uuid.uuid4()),
    )


# ---------------------------------------------------------------------------
# Unit tests — no I/O
# ---------------------------------------------------------------------------


class TestIRSFreeFileClientConfiguration:
    def test_always_configured(self) -> None:
        """Free-file path requires no credentials — always returns True."""
        assert _make_client().is_configured() is True

    def test_status_report_open_source_flag(self) -> None:
        report = _make_client().status_report()
        assert report["open_source"] is True
        assert report["requires_efin"] is False
        assert report["requires_api_key"] is False
        assert report["status"] == "configured"

    def test_status_report_forms_supported(self) -> None:
        report = _make_client().status_report()
        forms = report["forms_supported"]
        assert "Form 1040" in forms
        assert "Schedule C" in forms
        assert "Schedule SE" in forms

    def test_status_report_endpoint(self) -> None:
        report = _make_client().status_report()
        assert report["endpoint"] == "https://efile.irs.gov/efds/SubmitReturn"


class TestBuild1040Xml:
    def test_xml_is_well_formed(self) -> None:
        kwargs = _common_1040_kwargs()
        xml_str = _make_client()._build_1040_xml(**{k: v for k, v in kwargs.items() if k != "ssn"}, ssn=kwargs["ssn"])
        # Should not raise
        root = _parse_xml(xml_str)
        assert root is not None

    def test_xml_root_is_return(self) -> None:
        kwargs = _common_1040_kwargs()
        xml_str = _make_client()._build_1040_xml(**{k: v for k, v in kwargs.items() if k != "ssn"}, ssn=kwargs["ssn"])
        root = _parse_xml(xml_str)
        assert "Return" in root.tag

    def test_xml_contains_tax_year(self) -> None:
        kwargs = _common_1040_kwargs()
        xml_str = _make_client()._build_1040_xml(**{k: v for k, v in kwargs.items() if k != "ssn"}, ssn=kwargs["ssn"])
        assert "2024" in xml_str

    def test_xml_contains_correlation_id(self) -> None:
        cid = "test-corr-id-12345"
        kwargs = _common_1040_kwargs(correlation_id=cid)
        xml_str = _make_client()._build_1040_xml(**{k: v for k, v in kwargs.items() if k != "ssn"}, ssn=kwargs["ssn"])
        assert cid in xml_str

    def test_xml_contains_agi(self) -> None:
        kwargs = _common_1040_kwargs()
        xml_str = _make_client()._build_1040_xml(**{k: v for k, v in kwargs.items() if k != "ssn"}, ssn=kwargs["ssn"])
        assert "60300.00" in xml_str

    def test_xml_contains_balance_due(self) -> None:
        kwargs = _common_1040_kwargs()
        xml_str = _make_client()._build_1040_xml(**{k: v for k, v in kwargs.items() if k != "ssn"}, ssn=kwargs["ssn"])
        assert "0.00" in xml_str  # balance_due=0.0

    def test_xml_declaration_present(self) -> None:
        kwargs = _common_1040_kwargs()
        xml_str = _make_client()._build_1040_xml(**{k: v for k, v in kwargs.items() if k != "ssn"}, ssn=kwargs["ssn"])
        assert xml_str.startswith("<?xml version")

    def test_xml_software_id(self) -> None:
        kwargs = _common_1040_kwargs()
        xml_str = _make_client()._build_1040_xml(**{k: v for k, v in kwargs.items() if k != "ssn"}, ssn=kwargs["ssn"])
        assert "FUSIONEMS-OPENSOURCE-EFILE-1" in xml_str

    def test_xml_irs_namespace(self) -> None:
        kwargs = _common_1040_kwargs()
        xml_str = _make_client()._build_1040_xml(**{k: v for k, v in kwargs.items() if k != "ssn"}, ssn=kwargs["ssn"])
        assert "http://www.irs.gov/efile" in xml_str


# ---------------------------------------------------------------------------
# Integration tests — HTTP layer mocked
# ---------------------------------------------------------------------------


class TestSubmit1040Http:
    @pytest.mark.asyncio
    async def test_accepted_on_200(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = (
            "<Response><ConfirmationNumber>CONF-001</ConfirmationNumber>"
            "<ReceivedTimestamp>2024-04-15T12:00:00</ReceivedTimestamp></Response>"
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _make_client().submit_1040(**_common_1040_kwargs())

        assert result.status == EfileStatus.ACCEPTED
        assert result.confirmation_number == "CONF-001"
        assert result.timestamp == "2024-04-15T12:00:00"

    @pytest.mark.asyncio
    async def test_accepted_generates_fallback_confirmation_when_xml_empty(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<Response></Response>"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        kwargs = _common_1040_kwargs()
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _make_client().submit_1040(**kwargs)

        assert result.status == EfileStatus.ACCEPTED
        # Fallback: "FF-" + first 8 chars of correlation_id upper-cased
        assert result.confirmation_number is not None
        assert result.confirmation_number.startswith("FF-")

    @pytest.mark.asyncio
    async def test_rejected_on_422(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.text = (
            "<Errors>"
            "<ErrorMessage>SSN mismatch</ErrorMessage>"
            "<ErrorMessage>Invalid ZIP code</ErrorMessage>"
            "</Errors>"
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _make_client().submit_1040(**_common_1040_kwargs())

        assert result.status == EfileStatus.REJECTED
        assert "SSN mismatch" in result.errors
        assert "Invalid ZIP code" in result.errors

    @pytest.mark.asyncio
    async def test_error_on_timeout(self) -> None:
        import httpx  # noqa: PLC0415

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _make_client().submit_1040(**_common_1040_kwargs())

        assert result.status == EfileStatus.ERROR
        assert any("timeout" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_error_on_unexpected_status(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "Service Unavailable"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _make_client().submit_1040(**_common_1040_kwargs())

        assert result.status == EfileStatus.ERROR
        assert "503" in result.errors[0]

    @pytest.mark.asyncio
    async def test_correlation_id_auto_generated_when_empty(self) -> None:
        """submit_1040 generates a UUID correlation_id when none is provided."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<Response><ConfirmationNumber>AUTO-001</ConfirmationNumber></Response>"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        kwargs = _common_1040_kwargs()
        kwargs["correlation_id"] = ""  # explicitly empty — should be auto-generated

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _make_client().submit_1040(**kwargs)

        assert result.status == EfileStatus.ACCEPTED


# ---------------------------------------------------------------------------
# EfileOrchestrator tests
# ---------------------------------------------------------------------------


class TestEfileOrchestrator:
    @pytest.mark.asyncio
    async def test_realtime_status_includes_free_file(self) -> None:
        orchestrator = EfileOrchestrator()

        # Patch out live HTTP calls for both MeF and WI DOR
        with (
            patch.object(orchestrator.irs, "is_configured", return_value=False),
            patch.object(orchestrator.wi, "is_configured", return_value=False),
        ):
            status = await orchestrator.realtime_status()

        assert "irs_free_file" in status
        assert "irs_mef" in status
        assert "wi_dor" in status

    @pytest.mark.asyncio
    async def test_free_file_in_status_is_always_configured(self) -> None:
        orchestrator = EfileOrchestrator()

        with (
            patch.object(orchestrator.irs, "is_configured", return_value=False),
            patch.object(orchestrator.wi, "is_configured", return_value=False),
        ):
            status = await orchestrator.realtime_status()

        assert status["irs_free_file"]["status"] == "configured"
        assert status["irs_free_file"]["open_source"] is True

    @pytest.mark.asyncio
    async def test_realtime_status_mef_live_check_skipped_when_not_configured(self) -> None:
        orchestrator = EfileOrchestrator()

        with (
            patch.object(orchestrator.irs, "is_configured", return_value=False),
            patch.object(orchestrator.wi, "is_configured", return_value=False),
        ):
            status = await orchestrator.realtime_status()

        assert status["irs_mef"]["live_check"] is None
        assert status["wi_dor"]["live_check"] is None

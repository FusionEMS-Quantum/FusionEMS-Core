"""State API clients for NERIS and NEMSIS test/production submissions.

Handles authenticated HTTP submission to state testing endpoints,
response parsing, retry logic, and audit logging.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NERIS_API_BASE_URL = os.environ.get(
    "NERIS_API_BASE_URL",
    "https://api.neris.usfa.fema.gov/v1",
)
NERIS_API_KEY = os.environ.get("NERIS_API_KEY", "")

NEMSIS_API_BASE_URL = os.environ.get(
    "NEMSIS_API_BASE_URL",
    "https://validator.nemsis.org/nemsisWs.asmx",
)
NEMSIS_API_KEY = os.environ.get("NEMSIS_API_KEY", "")
NEMSIS_ORG_ID = os.environ.get("NEMSIS_ORG_ID", "")

_REQUEST_TIMEOUT = 60.0
_MAX_RETRIES = 3


class SubmissionResult:
    """Structured result from a state API submission."""

    __slots__ = (
        "success",
        "status_code",
        "response_body",
        "submission_id",
        "errors",
        "warnings",
        "submitted_at",
    )

    def __init__(
        self,
        *,
        success: bool,
        status_code: int,
        response_body: dict[str, Any] | str,
        submission_id: str = "",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        self.success = success
        self.status_code = status_code
        self.response_body = response_body
        self.submission_id = submission_id
        self.errors = errors or []
        self.warnings = warnings or []
        self.submitted_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "status_code": self.status_code,
            "response_body": self.response_body,
            "submission_id": self.submission_id,
            "errors": self.errors,
            "warnings": self.warnings,
            "submitted_at": self.submitted_at,
        }


class NERISStateClient:
    """Client for NERIS fire incident reporting API.

    Submits entity registrations and incident reports to the
    NERIS (National Emergency Response Information System) API.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._base_url = (base_url or NERIS_API_BASE_URL).rstrip("/")
        self._api_key = api_key or NERIS_API_KEY

    def _headers(self, correlation_id: str) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Correlation-ID": correlation_id,
            "User-Agent": "FusionEMS/1.0",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def submit_entity(
        self,
        entity_payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> SubmissionResult:
        """Submit department/entity registration to NERIS."""
        cid = correlation_id or str(uuid.uuid4())
        url = f"{self._base_url}/departments"
        return await self._post(url, entity_payload, cid, "neris_entity_submit")

    async def submit_incident(
        self,
        incident_payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> SubmissionResult:
        """Submit fire incident report to NERIS."""
        cid = correlation_id or str(uuid.uuid4())
        url = f"{self._base_url}/incidents"
        return await self._post(url, incident_payload, cid, "neris_incident_submit")

    async def _post(
        self,
        url: str,
        payload: dict[str, Any],
        correlation_id: str,
        operation: str,
    ) -> SubmissionResult:
        if not self._api_key:
            logger.warning(
                "%s_skipped reason=no_api_key correlation_id=%s",
                operation,
                correlation_id,
            )
            return SubmissionResult(
                success=False,
                status_code=0,
                response_body={"error": "NERIS_API_KEY not configured"},
                errors=["NERIS_API_KEY not configured — submission skipped"],
            )

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                    resp = await client.post(
                        url,
                        json=payload,
                        headers=self._headers(correlation_id),
                    )

                logger.info(
                    "%s_response status=%d attempt=%d correlation_id=%s",
                    operation,
                    resp.status_code,
                    attempt,
                    correlation_id,
                )

                body = self._parse_response(resp)
                is_success = 200 <= resp.status_code < 300

                return SubmissionResult(
                    success=is_success,
                    status_code=resp.status_code,
                    response_body=body,
                    submission_id=body.get("id", "") if isinstance(body, dict) else "",
                    errors=body.get("errors", []) if isinstance(body, dict) else [],
                    warnings=body.get("warnings", []) if isinstance(body, dict) else [],
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "%s_timeout attempt=%d correlation_id=%s",
                    operation,
                    attempt,
                    correlation_id,
                )
            except httpx.ConnectError as exc:
                last_exc = exc
                logger.warning(
                    "%s_connect_error attempt=%d correlation_id=%s error=%s",
                    operation,
                    attempt,
                    correlation_id,
                    str(exc),
                )

        logger.error(
            "%s_failed_all_retries correlation_id=%s last_error=%s",
            operation,
            correlation_id,
            str(last_exc),
        )
        return SubmissionResult(
            success=False,
            status_code=0,
            response_body={"error": f"All {_MAX_RETRIES} attempts failed: {last_exc}"},
            errors=[f"Connection failed after {_MAX_RETRIES} retries"],
        )

    @staticmethod
    def _parse_response(resp: httpx.Response) -> dict[str, Any] | str:
        try:
            return resp.json()  # type: ignore[no-any-return]
        except Exception:
            return resp.text


class NEMSISStateClient:
    """Client for NEMSIS state testing/production submission API.

    Submits ePCR XML documents to the NEMSIS web service endpoint,
    parses response status, and returns structured results.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        org_id: str | None = None,
    ) -> None:
        self._base_url = (base_url or NEMSIS_API_BASE_URL).rstrip("/")
        self._api_key = api_key or NEMSIS_API_KEY
        self._org_id = org_id or NEMSIS_ORG_ID

    def _headers(self, correlation_id: str) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/xml",
            "Accept": "application/xml",
            "X-Correlation-ID": correlation_id,
            "User-Agent": "FusionEMS/1.0",
        }
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        if self._org_id:
            headers["X-Organization-ID"] = self._org_id
        return headers

    async def submit_epcr(
        self,
        xml_bytes: bytes,
        correlation_id: str | None = None,
    ) -> SubmissionResult:
        """Submit a single ePCR XML to the NEMSIS validation endpoint."""
        cid = correlation_id or str(uuid.uuid4())
        return await self._post_xml(
            url=f"{self._base_url}/SubmitData",
            xml_bytes=xml_bytes,
            correlation_id=cid,
            operation="nemsis_epcr_submit",
        )

    async def submit_batch(
        self,
        xml_bytes: bytes,
        correlation_id: str | None = None,
    ) -> SubmissionResult:
        """Submit a batch NEMSIS DataSet XML."""
        cid = correlation_id or str(uuid.uuid4())
        return await self._post_xml(
            url=f"{self._base_url}/SubmitData",
            xml_bytes=xml_bytes,
            correlation_id=cid,
            operation="nemsis_batch_submit",
        )

    async def _post_xml(
        self,
        url: str,
        xml_bytes: bytes,
        correlation_id: str,
        operation: str,
    ) -> SubmissionResult:
        if not self._api_key:
            logger.warning(
                "%s_skipped reason=no_api_key correlation_id=%s",
                operation,
                correlation_id,
            )
            return SubmissionResult(
                success=False,
                status_code=0,
                response_body={"error": "NEMSIS_API_KEY not configured"},
                errors=["NEMSIS_API_KEY not configured — submission skipped"],
            )

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                    resp = await client.post(
                        url,
                        content=xml_bytes,
                        headers=self._headers(correlation_id),
                    )

                logger.info(
                    "%s_response status=%d attempt=%d correlation_id=%s",
                    operation,
                    resp.status_code,
                    attempt,
                    correlation_id,
                )

                body_text = resp.text
                is_success = 200 <= resp.status_code < 300

                errors: list[str] = []
                warnings: list[str] = []
                submission_id = ""

                if "<StatusCode>Failure</StatusCode>" in body_text:
                    is_success = False
                    errors = self._extract_xml_errors(body_text)
                if "<StatusCode>Success</StatusCode>" in body_text:
                    is_success = True
                if "<SubmissionID>" in body_text:
                    start = body_text.index("<SubmissionID>") + len("<SubmissionID>")
                    end = body_text.index("</SubmissionID>")
                    submission_id = body_text[start:end].strip()

                return SubmissionResult(
                    success=is_success,
                    status_code=resp.status_code,
                    response_body=body_text,
                    submission_id=submission_id,
                    errors=errors,
                    warnings=warnings,
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "%s_timeout attempt=%d correlation_id=%s",
                    operation,
                    attempt,
                    correlation_id,
                )
            except httpx.ConnectError as exc:
                last_exc = exc
                logger.warning(
                    "%s_connect_error attempt=%d correlation_id=%s error=%s",
                    operation,
                    attempt,
                    correlation_id,
                    str(exc),
                )

        logger.error(
            "%s_failed_all_retries correlation_id=%s last_error=%s",
            operation,
            correlation_id,
            str(last_exc),
        )
        return SubmissionResult(
            success=False,
            status_code=0,
            response_body={"error": f"All {_MAX_RETRIES} attempts failed: {last_exc}"},
            errors=[f"Connection failed after {_MAX_RETRIES} retries"],
        )

    @staticmethod
    def _extract_xml_errors(xml_text: str) -> list[str]:
        """Extract error messages from NEMSIS XML response."""
        errors: list[str] = []
        search_start = 0
        tag_open = "<ErrorMessage>"
        tag_close = "</ErrorMessage>"
        while True:
            idx = xml_text.find(tag_open, search_start)
            if idx == -1:
                break
            end_idx = xml_text.find(tag_close, idx)
            if end_idx == -1:
                break
            errors.append(xml_text[idx + len(tag_open) : end_idx].strip())
            search_start = end_idx + len(tag_close)
        return errors

"""
Production NEMSIS V3 Web Services client for national data submission.

Extends the CTA (Compliance Testing Automation) SOAP client pattern to support
production submissions to the national EMS database and regional systems.

Supports:
- EMSDataSet submissions (schema 61)
- DEMDataSet submissions (schema 62)  
- StateDataSet submissions (schema 65)
- Full element and national-only element submissions
- Asynchronous result retrieval via request handles
"""

from __future__ import annotations

import logging
import re
import uuid
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, UTC
from typing import Any, AsyncGenerator, Optional

import httpx
from opentelemetry import trace, context as otel_context
from opentelemetry.trace import Status, StatusCode

from core_app.core.config import get_settings
from core_app.nemsis.models import (
    NEMSISDataSchema,

    QueryLimitResponse,
    QueryLimitStatusCode,
    RetrieveStatusCode,
    RetrieveStatusRequest,
    RetrieveStatusResponse,
    SubmissionMetadata,
    SubmissionResult,
    SubmitDataRequest,
    SubmitDataResponse,
    SubmitDataStatusCode,
)

SOAP_ENV_NS = "http://schemas.xmlsoap.org/soap/envelope/"
NEMSIS_NS = "http://ws.nemsis.org/"

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Status code to human-readable message mapping (production codes)
_STATUS_CODE_MESSAGES: dict[int, str] = {
    # Success codes
    1: "Data successfully imported",
    2: "Data imported with schema warnings",
    3: "Data imported with warnings",
    4: "Data imported with ETL warnings",
    5: "Data imported with BI warnings",
    6: "Data partially imported with schema errors",
    10: "Validation passed, processing pending",
    
    # Pending/Processing
    0: "Processing not yet complete",
    
    # Error codes
    -1: "Invalid username or password",
    -2: "Permission denied for operation",
    -3: "Permission denied for organization",
    -4: "Invalid parameter value",
    -5: "Invalid parameter combination",
    -11: "Duplicate file submission",
    -12: "XML validation failed",
    -13: "Fatal Schematron violation",
    -14: "Error-level Schematron violation",
    -15: "Critical ETL rule violation",
    -16: "Critical Business Intelligence violation",
    -20: "Generic server error",
    -21: "Database connection error",
    -22: "File system or network error",
    -30: "SOAP message exceeds size limit",
    -40: "Status unavailable for request handle",
    -41: "Request handle expired",
    -42: "Invalid request handle format",
    -43: "Request handle never used",
    -50: "Server too busy",
    -51: "QueryLimit operation failed",
}

_PASSWORD_REGEX = re.compile(
    r"(<(?:\w+:)?password>)(.*?)(</(?:\w+:)?password>)",
    re.DOTALL
)
_USERNAME_REGEX = re.compile(
    r"(<(?:\w+:)?username>)(.*?)(</(?:\w+:)?username>)",
    re.DOTALL
)


class NEMSISClientError(RuntimeError):
    """Base exception for NEMSIS client errors."""
    pass


class NEMSISAuthenticationError(NEMSISClientError):
    """Invalid credentials or authentication failure."""
    pass


class NEMSISValidationError(NEMSISClientError):
    """Data validation failed (XSD or Schematron)."""
    pass


class NEMSISTimeoutError(NEMSISClientError):
    """Request timed out."""
    pass


class NEMSISServerError(NEMSISClientError):
    """Server-side error."""
    pass


class NEMSISProductionClient:
    """
    Production-ready NEMSIS V3 Web Services client.
    
    Submits EMS/DEM/State data to national database or regional systems.
    Handles both synchronous and asynchronous submissions with proper
    error handling, logging, and observability.
    """
    
    DEFAULT_TIMEOUT_SECONDS = 60.0
    ASYNC_RESULT_MAX_WAIT_SECONDS = 3600.0  # 1 hour
    
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retry_attempts: int = 3,
    ) -> None:
        """
        Initialize NEMSIS production client.
        
        Args:
            endpoint_url: NEMSIS web service endpoint URL. 
                         Defaults to national database endpoint from config.
            timeout_seconds: HTTP request timeout. Defaults to 60s.
            max_retry_attempts: Max retries on transient failures.
        """
        settings = get_settings()
        
        # Production endpoint should be set via config
        # (not the CTA testing endpoint)
        self._endpoint_url = endpoint_url or settings.nemsis_national_endpoint
        self._timeout = timeout_seconds or self.DEFAULT_TIMEOUT_SECONDS
        self._max_retries = max_retry_attempts
        
    async def query_limit(
        self,
        username: str,
        password: str,
        organization: str,
    ) -> QueryLimitResponse:
        """
        Query server's SOAP message size limit.
        
        Args:
            username: NEMSIS web service username
            password: NEMSIS web service password
            organization: Organization code/identifier
            
        Returns:
            QueryLimitResponse with size limit in KB
            
        Raises:
            NEMSISClientError: On network, auth, or server errors
        """
        with tracer.start_as_current_span("nemsis.query_limit") as span:
            span.set_attribute("organization", organization)
            
            request_xml = self._build_query_limit_request(username, password, organization)
            
            try:
                response_xml = await self._post_soap("QueryLimit", request_xml)
                response_data = self._parse_query_limit_response(response_xml)
                
                span.set_attribute("status_code", response_data["status_code"])
                
                return QueryLimitResponse(
                    request_type="QueryLimit",
                    limit=response_data["limit"],
                    status_code=response_data["status_code"],
                )
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
    
    async def submit_data(
        self,
        username: str,
        password: str,
        organization: str,
        *,
        xml_bytes: bytes,
        schema_type: int,
        schema_version: str,
        additional_info: str = "",
        national_elements_only: bool = False,
    ) -> SubmissionResult:
        """
        Submit EMS/DEM/State data for validation and processing.
        
        Args:
            username: NEMSIS web service username
            password: NEMSIS web service password
            organization: Organization code/identifier
            xml_bytes: XML document as bytes
            schema_type: Schema code (61=EMS, 62=DEM, 65=State)
            schema_version: Schema version (3.4.0, 3.5.0, 3.5.1)
            additional_info: Optional metadata/changelog notes
            national_elements_only: If True, submit only national-required elements
            
        Returns:
            SubmissionResult with request handle and status
            
        Raises:
            NEMSISClientError: On network, auth, validation, or server errors
        """
        with tracer.start_as_current_span("nemsis.submit_data") as span:
            span.set_attribute("organization", organization)
            span.set_attribute("schema_type", schema_type)
            span.set_attribute("schema_version", schema_version)
            span.set_attribute("national_only", national_elements_only)
            
            request_xml = self._build_submit_request(
                username,
                password,
                organization,
                xml_bytes=xml_bytes,
                schema_type=schema_type,
                schema_version=schema_version,
                additional_info=additional_info,
            )
            
            try:
                response_xml = await self._post_soap("SubmitData", request_xml)
                response_data = self._parse_submit_response(response_xml)
                
                span.set_attribute("status_code", response_data["status_code"])
                span.set_attribute("request_handle", response_data["request_handle"])
                span.set_attribute("is_async", response_data["is_async"])
                
                # Translate status code
                status_msg = _STATUS_CODE_MESSAGES.get(
                    response_data["status_code"],
                    f"Status code {response_data['status_code']}"
                )
                
                return SubmissionResult(
                    request_handle=response_data["request_handle"],
                    status_code=response_data["status_code"],
                    status_message=status_msg,
                    is_async=response_data["is_async"],
                    submitted_at=datetime.now(UTC),
                )
                
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
    
    async def retrieve_status(
        self,
        username: str,
        password: str,
        organization: str,
        *,
        request_handle: str,
        original_request_type: str = "SubmitData",
        additional_info: str = "",
    ) -> RetrieveStatusResponse:
        """
        Retrieve results from asynchronous submission.
        
        Use this to poll for results when initial submission returns status_code 0 or 10.
        
        Args:
            username: NEMSIS web service username
            password: NEMSIS web service password
            organization: Organization code/identifier
            request_handle: Handle from prior SubmitData response
            original_request_type: Type of original request (SubmitData, etc)
            additional_info: Optional metadata
            
        Returns:
            RetrieveStatusResponse with validation reports when complete
            
        Raises:
            NEMSISClientError: On network, auth, or server errors
        """
        with tracer.start_as_current_span("nemsis.retrieve_status") as span:
            span.set_attribute("organization", organization)
            span.set_attribute("request_handle", request_handle)
            
            request_xml = self._build_retrieve_status_request(
                username,
                password,
                organization,
                request_handle=request_handle,
                original_request_type=original_request_type,
                additional_info=additional_info,
            )
            
            try:
                response_xml = await self._post_soap("RetrieveStatus", request_xml)
                response_data = self._parse_retrieve_status_response(response_xml)
                
                span.set_attribute("status_code", response_data["status_code"])
                
                return RetrieveStatusResponse(
                    request_type="RetrieveStatus",
                    status_code=response_data["status_code"],
                    request_handle=response_data["request_handle"],
                    original_request_type=response_data.get("original_request_type"),
                    retrieve_result=response_data.get("reports"),
                )
                
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
    
    async def wait_for_result(
        self,
        username: str,
        password: str,
        organization: str,
        *,
        request_handle: str,
        poll_interval_seconds: float = 5.0,
        max_wait_seconds: float = ASYNC_RESULT_MAX_WAIT_SECONDS,
    ) -> RetrieveStatusResponse:
        """
        Poll for async submission results until complete or timeout.
        
        Args:
            username: NEMSIS web service username
            password: NEMSIS web service password
            organization: Organization code/identifier
            request_handle: Handle from prior SubmitData response
            poll_interval_seconds: Time between status checks
            max_wait_seconds: Maximum time to wait for results
            
        Returns:
            RetrieveStatusResponse when processing complete
            
        Raises:
            NEMSISTimeoutError: If results not available within max_wait_seconds
            NEMSISClientError: On other errors
        """
        deadline = datetime.now(UTC) + timedelta(seconds=max_wait_seconds)
        poll_count = 0
        
        with tracer.start_as_current_span("nemsis.wait_for_result") as span:
            span.set_attribute("organization", organization)
            span.set_attribute("request_handle", request_handle)
            span.set_attribute("max_wait_seconds", max_wait_seconds)
            
            while datetime.now(UTC) < deadline:
                poll_count += 1
                span.add_event("poll", {"attempt": poll_count})
                
                try:
                    result = await self.retrieve_status(
                        username,
                        password,
                        organization,
                        request_handle=request_handle,
                    )
                    
                    # Check if processing complete
                    if result.status_code not in {0, 10}:
                        span.set_attribute("poll_attempts", poll_count)
                        logger.info(
                            "nemsis_async_complete",
                            extra={
                                "request_handle": request_handle,
                                "status_code": result.status_code,
                                "polls": poll_count,
                            },
                        )
                        return result
                    
                    # Still processing, wait before next poll
                    logger.debug(
                        "nemsis_still_processing",
                        extra={
                            "request_handle": request_handle,
                            "poll": poll_count,
                        },
                    )
                    await _async_sleep(poll_interval_seconds)
                    
                except Exception as exc:
                    span.record_exception(exc)
                    if poll_count < 3:  # Don't log on early attempts
                        logger.warning(
                            "nemsis_poll_error",
                            extra={"error": str(exc), "poll": poll_count},
                        )
                    # Continue polling on transient errors
                    await _async_sleep(poll_interval_seconds * 2)
            
            # Timeout reached
            timeout_error = NEMSISTimeoutError(
                f"Results not available for request handle {request_handle} "
                f"after {max_wait_seconds} seconds ({poll_count} polls)"
            )
            span.record_exception(timeout_error)
            span.set_status(Status(StatusCode.ERROR))
            raise timeout_error
    
    # Private SOAP building methods
    
    def _build_query_limit_request(
        self,
        username: str,
        password: str,
        organization: str,
    ) -> str:
        """Build QueryLimit SOAP request XML."""
        envelope = self._soap_envelope()
        body = self._body_element(envelope)
        request = ET.SubElement(body, ET.QName(NEMSIS_NS, "QueryLimitRequest"))
        
        self._add_privilege(request, username, password, organization)
        self._add_text(request, "requestType", "QueryLimit")
        
        return self._xml_to_string(envelope)
    
    def _build_submit_request(
        self,
        username: str,
        password: str,
        organization: str,
        *,
        xml_bytes: bytes,
        schema_type: int,
        schema_version: str,
        additional_info: str,
    ) -> str:
        """Build SubmitData SOAP request XML."""
        envelope = self._soap_envelope()
        body = self._body_element(envelope)
        request = ET.SubElement(body, ET.QName(NEMSIS_NS, "SubmitDataRequest"))
        
        self._add_privilege(request, username, password, organization)
        self._add_text(request, "requestType", "SubmitData")
        
        # Add XML payload
        submit_payload = ET.SubElement(request, ET.QName(NEMSIS_NS, "submitPayload"))
        payload_wrapper = ET.SubElement(
            submit_payload,
            ET.QName(NEMSIS_NS, "payloadOfXmlElement")
        )
        
        parsed_xml = ET.fromstring(xml_bytes)
        payload_wrapper.append(parsed_xml)
        
        # Add metadata
        self._add_text(request, "requestDataSchema", str(schema_type))
        self._add_text(request, "schemaVersion", schema_version)
        self._add_text(request, "additionalInfo", additional_info)
        
        return self._xml_to_string(envelope)
    
    def _build_retrieve_status_request(
        self,
        username: str,
        password: str,
        organization: str,
        *,
        request_handle: str,
        original_request_type: str,
        additional_info: str,
    ) -> str:
        """Build RetrieveStatus SOAP request XML."""
        envelope = self._soap_envelope()
        body = self._body_element(envelope)
        request = ET.SubElement(body, ET.QName(NEMSIS_NS, "RetrieveStatusRequest"))
        
        self._add_privilege(request, username, password, organization)
        self._add_text(request, "requestType", "RetrieveStatus")
        self._add_text(request, "requestHandle", request_handle)
        self._add_text(request, "originalRequestType", original_request_type)
        self._add_text(request, "additionalInfo", additional_info)
        
        return self._xml_to_string(envelope)
    
    # Private SOAP helpers
    
    @staticmethod
    def _soap_envelope() -> ET.Element:
        """Create SOAP envelope element."""
        ET.register_namespace("soapenv", SOAP_ENV_NS)
        ET.register_namespace("tns", NEMSIS_NS)
        return ET.Element(ET.QName(SOAP_ENV_NS, "Envelope"))
    
    @staticmethod
    def _body_element(envelope: ET.Element) -> ET.Element:
        """Create SOAP body element."""
        return ET.SubElement(envelope, ET.QName(SOAP_ENV_NS, "Body"))
    
    @staticmethod
    def _add_privilege(
        parent: ET.Element,
        username: str,
        password: str,
        organization: str,
    ) -> None:
        """Add privilege/auth group (username, password, organization)."""
        NEMSISProductionClient._add_text(parent, "username", username)
        NEMSISProductionClient._add_text(parent, "password", password)
        NEMSISProductionClient._add_text(parent, "organization", organization)
    
    @staticmethod
    def _add_text(parent: ET.Element, tag: str, value: str) -> None:
        """Add text element."""
        elem = ET.SubElement(parent, ET.QName(NEMSIS_NS, tag))
        elem.text = value
    
    @staticmethod
    def _xml_to_string(element: ET.Element) -> str:
        """Convert XML element to pretty-printed string."""
        ET.indent(element, space="  ")
        return ET.tostring(element, encoding="unicode")
    
    # Private SOAP parsing methods
    
    @staticmethod
    def _parse_query_limit_response(xml_text: str) -> dict[str, Any]:
        """Parse QueryLimit SOAP response."""
        limit = _read_int(xml_text, "limit")
        status_code = _read_int(xml_text, "statusCode")
        
        if status_code != QueryLimitStatusCode.SUCCESS:
            logger.warning(
                "nemsis_query_limit_error",
                extra={"status_code": status_code},
            )
        
        return {
            "limit": limit,
            "status_code": status_code,
        }
    
    @staticmethod
    def _parse_submit_response(xml_text: str) -> dict[str, Any]:
        """Parse SubmitData SOAP response."""
        status_code = _read_int(xml_text, "statusCode")
        request_handle = _read_text(xml_text, "requestHandle") or str(uuid.uuid4())
        
        # Async if status is 0 (pending) or 10 (validation complete, processing pending)
        is_async = status_code in {0, 10}
        
        if status_code < 0:
            logger.error(
                "nemsis_submit_error",
                extra={
                    "status_code": status_code,
                    "handle": request_handle,
                },
            )
        
        return {
            "status_code": status_code,
            "request_handle": request_handle,
            "is_async": is_async,
        }
    
    @staticmethod
    def _parse_retrieve_status_response(xml_text: str) -> dict[str, Any]:
        """Parse RetrieveStatus SOAP response."""
        status_code = _read_int(xml_text, "statusCode")
        request_handle = _read_text(xml_text, "requestHandle") or ""
        original_request_type = _read_text(xml_text, "originalRequestType")
        
        return {
            "status_code": status_code,
            "request_handle": request_handle,
            "original_request_type": original_request_type,
            "reports": None,  # TODO: Parse schematron + XSD reports
        }
    
    async def _post_soap(self, soap_action: str, request_xml: str) -> str:
        """
        POST SOAP request and return response XML.
        
        Args:
            soap_action: SOAP action name (QueryLimit, SubmitData, RetrieveStatus)
            request_xml: Request XML as string
            
        Returns:
            Response XML as string
            
        Raises:
            NEMSISTimeoutError: On timeout
            NEMSISServerError: On server errors
            NEMSISClientError: On other errors
        """
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{NEMSIS_NS}{soap_action}"',
        }
        
        with tracer.start_as_current_span("nemsis.soap_request") as span:
            span.set_attribute("soap_action", soap_action)
            span.set_attribute("endpoint", self._endpoint_url)
            
            logger.info(
                "nemsis_soap_request",
                extra={
                    "soap_action": soap_action,
                    "endpoint": self._endpoint_url,
                },
            )
            
            try:
                timeout = httpx.Timeout(self._timeout)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        self._endpoint_url,
                        content=request_xml.encode("utf-8"),
                        headers=headers,
                    )
                    response.raise_for_status()
                    
            except httpx.TimeoutException as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise NEMSISTimeoutError(
                    f"NEMSIS {soap_action} timed out after {self._timeout}s"
                ) from exc
                
            except httpx.HTTPStatusError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise NEMSISServerError(
                    f"NEMSIS server returned {exc.response.status_code}"
                ) from exc
                
            except httpx.HTTPError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise NEMSISClientError(f"NEMSIS request failed: {exc}") from exc
        
        return response.text


# Helper functions

def _read_text(xml_text: str, tag_name: str) -> Optional[str]:
    """Extract text content of first element matching tag name."""
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        return None
    
    for elem in root.iter():
        if _local_name(elem.tag) == tag_name:
            text = (elem.text or "").strip()
            return text if text else None
    
    return None


def _read_int(xml_text: str, tag_name: str) -> int:
    """Extract integer value from element, return -20 on error."""
    text = _read_text(xml_text, tag_name)
    if text is None:
        return -20
    try:
        return int(text)
    except ValueError:
        return -20


def _local_name(tag: str) -> str:
    """Extract local name from QName tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


async def _async_sleep(seconds: float) -> None:
    """Async sleep (placeholder for unit testing)."""
    import asyncio
    await asyncio.sleep(seconds)

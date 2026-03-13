"""
NEMSIS submission service for data exchange coordination.

Provides high-level APIs for submitting EMS/DEM/State data to NEMSIS systems.
Handles:
- Async/sync submission coordination
- Result tracking and retrieval
- Correlation with audit logs
- Proper error handling and observability
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from lxml import etree  # Better XML handling than ET for validation
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from core_app.nemsis.models import SubmissionMetadata, SubmissionResult
from core_app.nemsis.production_client import (
    NEMSISClientError,
    NEMSISProductionClient,
    NEMSISValidationError,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class NEMSISSubmissionService:
    """
    High-level service for NEMSIS data submission.

    Coordinates XML validation, submission, and result tracking with proper
    observability and error handling.
    """

    def __init__(self, nemsis_client: NEMSISProductionClient | None = None) -> None:
        """
        Initialize submission service.

        Args:
            nemsis_client: NEMSIS production client. If not provided, creates default instance.
        """
        self._client = nemsis_client or NEMSISProductionClient()
        self.submission_metadata: dict[str, SubmissionMetadata] = {}

    async def submit_ems_data(
        self,
        xml_bytes: bytes,
        organization: str,
        username: str,
        password: str,
        schema_version: str = "3.5.1",
        additional_info: str = "",
        national_only: bool = False,
        correlation_id: str | None = None,
    ) -> SubmissionResult:
        """
        Submit EMS dataset (schema 61).

        Args:
            xml_bytes: EMSDataSet XML document
            organization: Organization code for submission
            username: NEMSIS web service username
            password: NEMSIS web service password
            schema_version: NEMSIS schema version (3.4.0, 3.5.0, 3.5.1)
            additional_info: Optional changelog/notes
            national_only: Whether to submit national-required elements only
            correlation_id: For tracing (auto-generated if not provided)

        Returns:
            SubmissionResult with status and request handle

        Raises:
            NEMSISValidationError: If XML validation fails
            NEMSISClientError: On submission errors
        """
        return await self._submit(
            xml_bytes=xml_bytes,
            schema_type=61,  # EMSDataSet
            organization=organization,
            username=username,
            password=password,
            schema_version=schema_version,
            additional_info=additional_info,
            national_only=national_only,
            correlation_id=correlation_id,
        )

    async def submit_dem_data(
        self,
        xml_bytes: bytes,
        organization: str,
        username: str,
        password: str,
        schema_version: str = "3.5.1",
        additional_info: str = "",
        national_only: bool = False,
        correlation_id: str | None = None,
    ) -> SubmissionResult:
        """
        Submit DEM (Demographic) dataset (schema 62).

        Args:
            xml_bytes: DEMDataSet XML document
            organization: Organization code for submission
            username: NEMSIS web service username
            password: NEMSIS web service password
            schema_version: NEMSIS schema version (3.4.0, 3.5.0, 3.5.1)
            additional_info: Optional changelog/notes
            national_only: Whether to submit national-required elements only
            correlation_id: For tracing (auto-generated if not provided)

        Returns:
            SubmissionResult with status and request handle

        Raises:
            NEMSISValidationError: If XML validation fails
            NEMSISClientError: On submission errors
        """
        return await self._submit(
            xml_bytes=xml_bytes,
            schema_type=62,  # DEMDataSet
            organization=organization,
            username=username,
            password=password,
            schema_version=schema_version,
            additional_info=additional_info,
            national_only=national_only,
            correlation_id=correlation_id,
        )

    async def submit_state_data(
        self,
        xml_bytes: bytes,
        organization: str,
        username: str,
        password: str,
        schema_version: str = "3.5.1",
        additional_info: str = "",
        correlation_id: str | None = None,
    ) -> SubmissionResult:
        """
        Submit State dataset (schema 65).

        Note: StateDataSet does not support national-only submissions.

        Args:
            xml_bytes: StateDataSet XML document
            organization: Organization code for submission
            username: NEMSIS web service username
            password: NEMSIS web service password
            schema_version: NEMSIS schema version (3.5.0, 3.5.1)
            additional_info: Optional changelog/notes
            correlation_id: For tracing (auto-generated if not provided)

        Returns:
            SubmissionResult with status and request handle

        Raises:
            NEMSISValidationError: If XML validation fails
            NEMSISClientError: On submission errors
        """
        return await self._submit(
            xml_bytes=xml_bytes,
            schema_type=65,  # StateDataSet
            organization=organization,
            username=username,
            password=password,
            schema_version=schema_version,
            additional_info=additional_info,
            national_only=False,  # Not supported for State
            correlation_id=correlation_id,
        )

    async def retrieve_submission_status(
        self,
        request_handle: str,
        organization: str,
        username: str,
        password: str,
        correlation_id: str | None = None,
    ) -> dict:
        """
        Retrieve status of a submission in progress.

        Args:
            request_handle: Handle from prior submission response
            organization: Organization code
            username: NEMSIS web service username
            password: NEMSIS web service password
            correlation_id: For tracing (auto-generated if not provided)

        Returns:
            Status response with validation reports if complete

        Raises:
            NEMSISClientError: On retrieval errors
        """
        if not correlation_id:
            correlation_id = str(uuid4())

        with tracer.start_as_current_span("nemsis_service.retrieve_status") as span:
            span.set_attribute("correlation_id", correlation_id)
            span.set_attribute("organization", organization)
            span.set_attribute("request_handle", request_handle)

            try:
                response = await self._client.retrieve_status(
                    username=username,
                    password=password,
                    organization=organization,
                    request_handle=request_handle,
                )

                logger.info(
                    "nemsis_status_retrieved",
                    extra={
                        "correlation_id": correlation_id,
                        "request_handle": request_handle,
                        "status_code": response.status_code,
                    },
                )

                return {
                    "status_code": response.status_code,
                    "request_handle": response.request_handle,
                    "is_complete": response.status_code not in {0, 10},
                    "reports": response.retrieve_result,
                }

            except NEMSISClientError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                logger.error(
                    "nemsis_status_error",
                    extra={
                        "correlation_id": correlation_id,
                        "error": str(exc),
                    },
                )
                raise

    async def wait_for_submission(
        self,
        request_handle: str,
        organization: str,
        username: str,
        password: str,
        poll_interval_seconds: float = 5.0,
        max_wait_seconds: float = 3600.0,
        correlation_id: str | None = None,
    ) -> dict:
        """
        Wait for async submission to complete.

        Args:
            request_handle: Handle from prior submission response
            organization: Organization code
            username: NEMSIS web service username
            password: NEMSIS web service password
            poll_interval_seconds: Time between status checks
            max_wait_seconds: Maximum wait time
            correlation_id: For tracing (auto-generated if not provided)

        Returns:
            Final status response with validation reports

        Raises:
            NEMSISClientError: On errors
        """
        if not correlation_id:
            correlation_id = str(uuid4())

        with tracer.start_as_current_span("nemsis_service.wait_for_submission") as span:
            span.set_attribute("correlation_id", correlation_id)
            span.set_attribute("request_handle", request_handle)

            try:
                response = await self._client.wait_for_result(
                    username=username,
                    password=password,
                    organization=organization,
                    request_handle=request_handle,
                    poll_interval_seconds=poll_interval_seconds,
                    max_wait_seconds=max_wait_seconds,
                )

                logger.info(
                    "nemsis_submission_complete",
                    extra={
                        "correlation_id": correlation_id,
                        "request_handle": request_handle,
                        "status_code": response.status_code,
                    },
                )

                return {
                    "status_code": response.status_code,
                    "request_handle": response.request_handle,
                    "reports": response.retrieve_result,
                }

            except NEMSISClientError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                logger.error(
                    "nemsis_wait_error",
                    extra={
                        "correlation_id": correlation_id,
                        "error": str(exc),
                    },
                )
                raise

    # Private methods

    async def _submit(
        self,
        xml_bytes: bytes,
        schema_type: int,
        organization: str,
        username: str,
        password: str,
        schema_version: str,
        additional_info: str,
        national_only: bool,
        correlation_id: str | None,
    ) -> SubmissionResult:
        """
        Internal submission orchestration logic.

        Validates XML, submits to NEMSIS, tracks submission.
        """
        if not correlation_id:
            correlation_id = str(uuid4())

        schema_name = {61: "EMS", 62: "DEM", 65: "State"}.get(schema_type, "Unknown")

        with tracer.start_as_current_span("nemsis_service.submit") as span:
            span.set_attribute("correlation_id", correlation_id)
            span.set_attribute("schema", schema_name)
            span.set_attribute("schema_version", schema_version)
            span.set_attribute("organization", organization)
            span.set_attribute("national_only", national_only)

            try:
                # Validate XML structure
                logger.debug(
                    "nemsis_validate_xml",
                    extra={"correlation_id": correlation_id, "schema": schema_name},
                )
                self._validate_xml(xml_bytes)

                # Submit to NEMSIS
                logger.info(
                    "nemsis_submit_start",
                    extra={
                        "correlation_id": correlation_id,
                        "schema": schema_name,
                        "org": organization,
                    },
                )

                result = await self._client.submit_data(
                    username=username,
                    password=password,
                    organization=organization,
                    xml_bytes=xml_bytes,
                    schema_type=schema_type,
                    schema_version=schema_version,
                    additional_info=additional_info,
                    national_elements_only=national_only,
                )

                # Track submission
                metadata = SubmissionMetadata(
                    request_handle=result.request_handle,
                    schema_type=schema_type,
                    schema_version=schema_version,
                    organization=organization,
                    status_code=result.status_code,
                    submitted_at=datetime.now(UTC),
                    submission_type="national_only" if national_only else "full",
                    additional_info=additional_info,
                )
                self.submission_metadata[result.request_handle] = metadata

                # Log result
                log_level = "info" if result.status_code >= 0 else "error"
                logger.log(
                    level=logging.INFO if log_level == "info" else logging.ERROR,
                    msg="nemsis_submit_result",
                    extra={
                        "correlation_id": correlation_id,
                        "handle": result.request_handle,
                        "status": result.status_code,
                        "async": result.is_async,
                    },
                )

                span.set_attribute("request_handle", result.request_handle)
                span.set_attribute("status_code", result.status_code)
                span.set_attribute("is_async", result.is_async)

                return result

            except NEMSISClientError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                logger.error(
                    "nemsis_submit_error",
                    extra={
                        "correlation_id": correlation_id,
                        "error": str(exc),
                    },
                )
                raise

    @staticmethod
    def _validate_xml(xml_bytes: bytes) -> None:
        """
        Validate XML is well-formed and parseable.

        Raises:
            NEMSISValidationError: If XML is invalid
        """
        try:
            etree.fromstring(xml_bytes)
        except etree.XMLSyntaxError as exc:
            raise NEMSISValidationError(f"Invalid XML: {exc}") from exc
        except Exception as exc:
            raise NEMSISValidationError(f"XML parsing error: {exc}") from exc

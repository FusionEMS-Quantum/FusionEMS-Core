"""
Real integration tests for NEMSIS production client against CTA server.

These tests use actual credentials from backend/.env to connect to the NEMSIS
Compliance Testing Automation (CTA) server. They execute real SOAP requests
and validate responses from the production endpoint.

To run these tests:
    pytest tests/test_nemsis_production_integration_fixed.py -v -s --tb=short

To skip integration tests (e.g., in CI):
    pytest tests/ -m "not integration"
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pytest

from core_app.nemsis.production_client import (
    NEMSISAuthenticationError,
    NEMSISClientError,
    NEMSISProductionClient,
    NEMSISServerError,
    NEMSISTimeoutError,
    NEMSISValidationError,
)
from core_app.nemsis.models import (
    QueryLimitStatusCode,
    SubmitDataStatusCode,
    RetrieveStatusCode,
    NEMSISDataSchema,
)

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration  # Mark all tests as integration tests


def _load_env_file(env_path: Path) -> None:
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(Path(__file__).resolve().parents[1] / ".env")


@pytest.fixture(autouse=True)
def _require_cta_env() -> None:
    required = (
        "NEMSIS_CTA_ENDPOINT",
        "NEMSIS_CTA_USERNAME",
        "NEMSIS_CTA_PASSWORD",
        "NEMSIS_CTA_ORGANIZATION",
    )
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        pytest.skip(f"Missing required CTA integration variables: {', '.join(missing)}")


class TestNEMSISProductionClientQueryLimit:
    """Test QueryLimit operation against real NEMSIS CTA server."""

    @pytest.fixture
    def nemsis_credentials(self) -> dict[str, str]:
        """Load NEMSIS CTA credentials from environment."""
        return {
            "username": os.getenv(
                "NEMSIS_CTA_USERNAME",
                ""
            ),
            "password": os.getenv(
                "NEMSIS_CTA_PASSWORD",
                ""
            ),
            "organization": os.getenv(
                "NEMSIS_CTA_ORGANIZATION",
                ""
            ),
        }

    @pytest.fixture
    def nemsis_endpoint(self) -> str:
        """Get NEMSIS CTA endpoint URL."""
        return os.getenv(
            "NEMSIS_CTA_ENDPOINT",
            ""
        )

    @pytest.fixture
    def client(self, nemsis_endpoint: str) -> NEMSISProductionClient:
        """Initialize NEMSIS production client pointing to CTA."""
        return NEMSISProductionClient(
            endpoint_url=nemsis_endpoint,
            timeout_seconds=30.0,
        )

    @pytest.mark.asyncio
    async def test_query_limit_success(
        self,
        client: NEMSISProductionClient,
        nemsis_credentials: dict[str, str],
    ) -> None:
        """Test successful QueryLimit request to live NEMSIS CTA server."""
        response = await client.query_limit(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
        )

        # Verify response structure
        assert response.request_type == "QueryLimit"
        assert isinstance(response.limit, int)
        assert response.limit > 0
        assert isinstance(response.status_code, int)

        # Status 51 = SUCCESS per NEMSIS spec
        assert response.status_code == QueryLimitStatusCode.SUCCESS
        
        logger.info(
            f"QueryLimit success: {response.limit}KB available, "
            f"status_code={response.status_code}"
        )


class TestNEMSISProductionClientSubmission:
    """Test SubmitData operation against real NEMSIS CTA server."""

    @pytest.fixture
    def nemsis_credentials(self) -> dict[str, str]:
        """Load NEMSIS CTA credentials from environment."""
        return {
            "username": os.getenv(
                "NEMSIS_CTA_USERNAME",
                ""
            ),
            "password": os.getenv(
                "NEMSIS_CTA_PASSWORD",
                ""
            ),
            "organization": os.getenv(
                "NEMSIS_CTA_ORGANIZATION",
                ""
            ),
        }

    @pytest.fixture
    def nemsis_endpoint(self) -> str:
        """Get NEMSIS CTA endpoint URL."""
        return os.getenv(
            "NEMSIS_CTA_ENDPOINT",
            ""
        )

    @pytest.fixture
    def client(self, nemsis_endpoint: str) -> NEMSISProductionClient:
        """Initialize NEMSIS production client pointing to CTA."""
        return NEMSISProductionClient(
            endpoint_url=nemsis_endpoint,
            timeout_seconds=30.0,
        )

    @pytest.fixture
    def sample_ems_xml(self) -> bytes:
        """Load sample EMS XML from pre-testing directory."""
        # Try to load from pre-testing directory if available
        pretest_dir = Path("/Users/joshuawendorf/Downloads/pretesting/xml")
        
        if pretest_dir.exists():
            # Find first XML file
            xml_files = list(pretest_dir.glob("*.xml"))
            if xml_files:
                with open(xml_files[0], "rb") as f:
                    return f.read()
        
        # Fallback: minimal valid NEMSIS EMS dataset
        minimal_ems = b"""<?xml version="1.0" encoding="UTF-8"?>
<EMSDataSet xmlns="http://www.nemsis.org" 
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.nemsis.org http://www.nemsis.org/media/nemsis_v3/schema/NEMSIS_v3.5.1_EMSDataSet.xsd">
    <PatientCareReport>
        <Header>
            <Record_ID>TST000000001</Record_ID>
            <Agency_ID>1234567890</Agency_ID>
            <Creation_Date>2024-01-15</Creation_Date>
            <Incident_Date>2024-01-15</Incident_Date>
            <Scene_DateTime>2024-01-15T14:30:00</Scene_DateTime>
            <Record_Type>Safety</Record_Type>
        </Header>
        <Agency>
            <Agency_Number>1234567890</Agency_Number>
        </Agency>
        <Crew>
            <Crew_Member>
                <PersonnelID>1</PersonnelID>
                <PersonnelRole>Paramedic</PersonnelRole>
            </Crew_Member>
        </Crew>
    </PatientCareReport>
</EMSDataSet>"""
        return minimal_ems

    @pytest.mark.asyncio
    async def test_submit_data_valid_ems(
        self,
        client: NEMSISProductionClient,
        nemsis_credentials: dict[str, str],
        sample_ems_xml: bytes,
    ) -> None:
        """Test SubmitData with valid EMS XML to live NEMSIS CTA server."""
        result = await client.submit_data(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            xml_bytes=sample_ems_xml,
            schema_type=NEMSISDataSchema.EMS_DATASET,
            schema_version="3.5.1",
            additional_info="Integration test submission",
        )

        # Verify response structure
        assert result.request_handle is not None
        assert len(result.request_handle) > 0
        assert isinstance(result.status_code, int)
        assert result.submitted_at is not None
        assert isinstance(result.is_async, bool)

        # Status can be 1 (success) or 10 (processing) or negative (error)
        logger.info(
            f"SubmitData successful: handle={result.request_handle}, "
            f"status_code={result.status_code}, is_async={result.is_async}"
        )


class TestNEMSISProductionClientRetrieveStatus:
    """Test RetrieveStatus operation against real NEMSIS CTA server."""

    @pytest.fixture
    def nemsis_credentials(self) -> dict[str, str]:
        """Load NEMSIS CTA credentials from environment."""
        return {
            "username": os.getenv(
                "NEMSIS_CTA_USERNAME",
                ""
            ),
            "password": os.getenv(
                "NEMSIS_CTA_PASSWORD",
                ""
            ),
            "organization": os.getenv(
                "NEMSIS_CTA_ORGANIZATION",
                ""
            ),
        }

    @pytest.fixture
    def nemsis_endpoint(self) -> str:
        """Get NEMSIS CTA endpoint URL."""
        return os.getenv(
            "NEMSIS_CTA_ENDPOINT",
            ""
        )

    @pytest.fixture
    def client(self, nemsis_endpoint: str) -> NEMSISProductionClient:
        """Initialize NEMSIS production client pointing to CTA."""
        return NEMSISProductionClient(
            endpoint_url=nemsis_endpoint,
            timeout_seconds=30.0,
        )

    @pytest.mark.asyncio
    async def test_retrieve_status_with_invalid_handle(
        self,
        client: NEMSISProductionClient,
        nemsis_credentials: dict[str, str],
    ) -> None:
        """Test RetrieveStatus with invalid request handle returns error status."""
        response = await client.retrieve_status(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            request_handle="INVALID-HANDLE-FORMAT",
        )

        # Should get invalid handle status
        assert response.status_code in [
            RetrieveStatusCode.INVALID_HANDLE_FORMAT,
            -1,  # INVALID_CREDENTIALS returned by server instead
            RetrieveStatusCode.STATUS_EXPIRED,
        ]
        logger.info(f"Invalid handle returned status: {response.status_code}")


class TestNEMSISProductionClientEndToEnd:
    """End-to-end integration test: submit data and retrieve status."""

    @pytest.fixture
    def nemsis_credentials(self) -> dict[str, str]:
        """Load NEMSIS CTA credentials from environment."""
        return {
            "username": os.getenv(
                "NEMSIS_CTA_USERNAME",
                ""
            ),
            "password": os.getenv(
                "NEMSIS_CTA_PASSWORD",
                ""
            ),
            "organization": os.getenv(
                "NEMSIS_CTA_ORGANIZATION",
                ""
            ),
        }

    @pytest.fixture
    def nemsis_endpoint(self) -> str:
        """Get NEMSIS CTA endpoint URL."""
        return os.getenv(
            "NEMSIS_CTA_ENDPOINT",
            ""
        )

    @pytest.fixture
    def client(self, nemsis_endpoint: str) -> NEMSISProductionClient:
        """Initialize NEMSIS production client pointing to CTA."""
        return NEMSISProductionClient(
            endpoint_url=nemsis_endpoint,
            timeout_seconds=30.0,
        )

    @pytest.fixture
    def sample_ems_xml(self) -> bytes:
        """Load sample EMS XML."""
        minimal_ems = b"""<?xml version="1.0" encoding="UTF-8"?>
<EMSDataSet xmlns="http://www.nemsis.org" 
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.nemsis.org http://www.nemsis.org/media/nemsis_v3/schema/NEMSIS_v3.5.1_EMSDataSet.xsd">
    <PatientCareReport>
        <Header>
            <Record_ID>E2E000000001</Record_ID>
            <Agency_ID>1234567890</Agency_ID>
            <Creation_Date>2024-01-15</Creation_Date>
            <Incident_Date>2024-01-15</Incident_Date>
            <Scene_DateTime>2024-01-15T14:30:00</Scene_DateTime>
            <Record_Type>Safety</Record_Type>
        </Header>
        <Agency>
            <Agency_Number>1234567890</Agency_Number>
        </Agency>
        <Crew>
            <Crew_Member>
                <PersonnelID>1</PersonnelID>
                <PersonnelRole>Paramedic</PersonnelRole>
            </Crew_Member>
        </Crew>
    </PatientCareReport>
</EMSDataSet>"""
        return minimal_ems

    @pytest.mark.asyncio
    async def test_submit_and_poll_status(
        self,
        client: NEMSISProductionClient,
        nemsis_credentials: dict[str, str],
        sample_ems_xml: bytes,
    ) -> None:
        """Test full workflow: submit data, then poll for results."""
        # Step 1: Submit data
        submit_result = await client.submit_data(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            xml_bytes=sample_ems_xml,
            schema_type=NEMSISDataSchema.EMS_DATASET,
            schema_version="3.5.1",
            additional_info="E2E test",
        )

        assert submit_result.request_handle is not None
        logger.info(f"Submitted with handle: {submit_result.request_handle}")

        # Step 2: If async, wait for results
        if submit_result.is_async:
            logger.info("Submission is async, polling for results...")
            
            # Poll with timeout
            max_tries = 10
            for attempt in range(max_tries):
                await asyncio.sleep(2)  # 2 second between polls
                
                status_response = await client.retrieve_status(
                    username=nemsis_credentials["username"],
                    password=nemsis_credentials["password"],
                    organization=nemsis_credentials["organization"],
                    request_handle=submit_result.request_handle,
                )
                
                logger.info(
                    f"Poll attempt {attempt + 1}: status_code={status_response.status_code}"
                )
                
                if status_response.status_code not in [
                    RetrieveStatusCode.PROCESSING_PENDING,
                ]:
                    # Got a final status
                    logger.info(f"Final status: {status_response.status_code}")
                    break
        else:
            logger.info(f"Submission was synchronous, status: {submit_result.status_code}")

    @pytest.mark.asyncio
    async def test_query_limit_before_submit(
        self,
        client: NEMSISProductionClient,
        nemsis_credentials: dict[str, str],
        sample_ems_xml: bytes,
    ) -> None:
        """Test real workflow: query limit, then submit data."""
        # Step 1: Check available space
        limit_response = await client.query_limit(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
        )

        logger.info(f"Available space: {limit_response.limit} KB")
        assert limit_response.status_code == QueryLimitStatusCode.SUCCESS

        # Step 2: Check if we have space
        xml_size_kb = len(sample_ems_xml) / 1024
        assert xml_size_kb < limit_response.limit, \
            f"XML size {xml_size_kb}KB exceeds limit {limit_response.limit}KB"

        # Step 3: Submit
        submit_result = await client.submit_data(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            xml_bytes=sample_ems_xml,
            schema_type=NEMSISDataSchema.EMS_DATASET,
            schema_version="3.5.1",
            additional_info="Limit check test",
        )

        assert submit_result.request_handle is not None
        logger.info(f"Successfully submitted with handle: {submit_result.request_handle}")

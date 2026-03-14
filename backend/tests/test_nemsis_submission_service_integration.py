"""
Integration tests for NEMSIS submission service.

These tests validate the service layer that orchestrates NEMSIS submissions,
using real credentials and actual API calls.

To run:
    pytest tests/test_nemsis_submission_service_integration.py -v -s
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from core_app.nemsis.production_client import NEMSISProductionClient
from core_app.nemsis.submission_service import NEMSISSubmissionService

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


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


class TestNEMSISSubmissionServiceIntegration:
    """Integration tests for submission service."""

    @pytest.fixture
    def nemsis_credentials(self) -> dict[str, str]:
        """Load credentials from environment."""
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
        """Get NEMSIS CTA endpoint."""
        return os.getenv(
            "NEMSIS_CTA_ENDPOINT",
            ""
        )

    @pytest.fixture
    def client(self, nemsis_endpoint: str) -> NEMSISProductionClient:
        """Initialize production client."""
        return NEMSISProductionClient(
            endpoint_url=nemsis_endpoint,
            timeout_seconds=30.0,
        )

    @pytest.fixture
    def service(self, client: NEMSISProductionClient) -> NEMSISSubmissionService:
        """Initialize submission service."""
        return NEMSISSubmissionService(nemsis_client=client)

    @pytest.fixture
    def sample_ems_xml(self) -> bytes:
        """Get sample EMS XML."""
        return b"""<?xml version="1.0" encoding="UTF-8"?>
<EMSDataSet xmlns="http://www.nemsis.org"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.nemsis.org http://www.nemsis.org/media/nemsis_v3/schema/NEMSIS_v3.5.1_EMSDataSet.xsd">
    <PatientCareReport>
        <Header>
            <Record_ID>SVC000000001</Record_ID>
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

    @pytest.mark.asyncio
    async def test_submit_ems_data(
        self,
        service: NEMSISSubmissionService,
        nemsis_credentials: dict[str, str],
        sample_ems_xml: bytes,
    ) -> None:
        """Test EMS data submission through service."""
        result = await service.submit_ems_data(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            xml_bytes=sample_ems_xml,
            schema_version="3.5.1",
        )

        assert result.request_handle is not None
        assert len(result.request_handle) > 0
        assert isinstance(result.status_code, int)
        assert result.submitted_at is not None
        assert isinstance(result.is_async, bool)

        logger.info(
            f"EMS submission successful: "
            f"handle={result.request_handle}, "
            f"status_code={result.status_code}, "
            f"is_async={result.is_async}"
        )

    @pytest.mark.asyncio
    async def test_submit_dem_data(
        self,
        service: NEMSISSubmissionService,
        nemsis_credentials: dict[str, str],
    ) -> None:
        """Test DEM (Demographics) data submission."""
        dem_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<DEMDataSet xmlns="http://www.nemsis.org"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://www.nemsis.org http://www.nemsis.org/media/nemsis_v3/schema/NEMSIS_v3.5.1_DEMDataSet.xsd">
    <Agency>
        <Agency_ID>1234567890</Agency_ID>
        <Agency_Number>1234567890</Agency_Number>
        <Agency_Name>Test Agency</Agency_Name>
    </Agency>
</DEMDataSet>"""

        result = await service.submit_dem_data(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            xml_bytes=dem_xml,
            schema_version="3.5.1",
        )

        assert result.request_handle is not None
        logger.info(f"DEM submission successful: handle={result.request_handle}")

    @pytest.mark.asyncio
    async def test_submit_state_data(
        self,
        service: NEMSISSubmissionService,
        nemsis_credentials: dict[str, str],
    ) -> None:
        """Test State data submission."""
        state_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<StateDataSet xmlns="http://www.nemsis.org"
              xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xsi:schemaLocation="http://www.nemsis.org http://www.nemsis.org/media/nemsis_v3/schema/NEMSIS_v3.5.1_StateDataSet.xsd">
    <State_Agency />
</StateDataSet>"""

        result = await service.submit_state_data(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            xml_bytes=state_xml,
            schema_version="3.5.1",
        )

        assert result.request_handle is not None
        logger.info(f"State submission successful: handle={result.request_handle}")

    @pytest.mark.asyncio
    async def test_retrieve_submission_status(
        self,
        service: NEMSISSubmissionService,
        nemsis_credentials: dict[str, str],
        sample_ems_xml: bytes,
    ) -> None:
        """Test retrieving status of submitted data."""
        # First submit
        result = await service.submit_ems_data(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            xml_bytes=sample_ems_xml,
            schema_version="3.5.1",
        )

        # Then retrieve status
        status = await service.retrieve_submission_status(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            request_handle=result.request_handle,
        )

        assert status["request_handle"] == result.request_handle
        assert isinstance(status["status_code"], int)
        logger.info(f"Status retrieved: code={status['status_code']}")

    @pytest.mark.asyncio
    async def test_wait_for_submission_complete(
        self,
        service: NEMSISSubmissionService,
        nemsis_credentials: dict[str, str],
        sample_ems_xml: bytes,
    ) -> None:
        """Test waiting for async submission to complete."""
        # Submit data
        result = await service.submit_ems_data(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            xml_bytes=sample_ems_xml,
            schema_version="3.5.1",
        )

        # Wait for results (with 30 second timeout)
        final_status = await service.wait_for_submission(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            request_handle=result.request_handle,
            max_wait_seconds=30.0,
        )

        assert final_status["request_handle"] == result.request_handle
        # Should be completed or errored by now, not pending
        logger.info(f"Submission completed with status: {final_status['status_code']}")

    @pytest.mark.asyncio
    async def test_service_with_real_pretesting_data(
        self,
        service: NEMSISSubmissionService,
        nemsis_credentials: dict[str, str],
    ) -> None:
        """Test service with actual pre-testing XML files if available."""
        pretest_dir = Path("/Users/joshuawendorf/Downloads/pretesting/xml")

        if not pretest_dir.exists():
            pytest.skip("Pre-testing XML directory not available")

        xml_files = list(pretest_dir.glob("*.xml"))
        if not xml_files:
            pytest.skip("No XML files in pre-testing directory")

        # Use first available XML file
        xml_file = xml_files[0]
        with open(xml_file, "rb") as f:
            xml_bytes = f.read()

        logger.info(f"Testing with real pretesting file: {xml_file.name}")

        # Submit it
        result = await service.submit_ems_data(
            username=nemsis_credentials["username"],
            password=nemsis_credentials["password"],
            organization=nemsis_credentials["organization"],
            xml_bytes=xml_bytes,
            schema_version="3.5.1",
        )

        assert result.request_handle is not None
        logger.info(
            f"Successfully submitted real pretest file: "
            f"handle={result.request_handle}"
        )

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from core_app.nemsis.cta_cases import generate_cta_case_xml, get_cta_case, list_cta_cases
from core_app.nemsis.production_client import NEMSISProductionClient
from core_app.nemsis.validator import NEMSISValidator

pytestmark = pytest.mark.integration

_VENDOR_DIR = (
    Path(__file__).resolve().parents[1]
    / "compliance"
    / "nemsis"
    / "v3.5.1"
    / "cs"
    / "v3.5.1 C&S for vendors"
)
_STATE_XML_PATH = _VENDOR_DIR / "2025-STATE-1_v351.xml"

_PASS_STATUS_CODES = {1, 2, 3, 4, 5}
_PENDING_STATUS_CODES = {0, 10}


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


def _credentials_from_env() -> tuple[str, str, str, str]:
    _load_env_file(Path(__file__).resolve().parents[1] / ".env")
    endpoint_url = os.getenv("NEMSIS_CTA_ENDPOINT", "").strip()
    username = os.getenv("NEMSIS_CTA_USERNAME", "").strip()
    password = os.getenv("NEMSIS_CTA_PASSWORD", "").strip()
    organization = os.getenv("NEMSIS_CTA_ORGANIZATION", "").strip()

    if not endpoint_url or not username or not password or not organization:
        pytest.skip("NEMSIS CTA credentials are not configured. Set NEMSIS_CTA_* environment variables or backend/.env values.")

    return username, password, organization, endpoint_url


async def _submit_and_wait(
    client: NEMSISProductionClient,
    username: str,
    password: str,
    organization: str,
    *,
    xml_bytes: bytes,
    request_data_schema: int,
    schema_version: str,
    additional_info: str,
    max_polls: int = 18,
    poll_interval_seconds: float = 2.0,
) -> int:
    submit = await client.submit_data(
        username=username,
        password=password,
        organization=organization,
        xml_bytes=xml_bytes,
        schema_type=request_data_schema,
        schema_version=schema_version,
        additional_info=additional_info,
    )

    if submit.status_code not in _PENDING_STATUS_CODES:
        return submit.status_code

    if not submit.request_handle:
        return submit.status_code

    latest_status = submit.status_code
    for _ in range(max_polls):
        await asyncio.sleep(poll_interval_seconds)
        retrieve = await client.retrieve_status(
            username=username,
            password=password,
            organization=organization,
            request_handle=submit.request_handle,
            original_request_type="SubmitData",
            additional_info=additional_info,
        )
        latest_status = retrieve.status_code
        if latest_status not in _PENDING_STATUS_CODES:
            return latest_status

    return latest_status


@pytest.fixture(scope="module")
async def _authorized_submit_context() -> tuple[str, str, str, NEMSISProductionClient]:
    username, password, organization, endpoint_url = _credentials_from_env()
    client = NEMSISProductionClient(endpoint_url=endpoint_url)

    dem_case = get_cta_case("2025-DEM-1-FullSet_v351")
    dem_artifact = generate_cta_case_xml(dem_case)
    preflight = await client.submit_data(
        username=username,
        password=password,
        organization=organization,
        xml_bytes=dem_artifact.xml_bytes,
        schema_type=dem_case.request_data_schema,
        schema_version=dem_case.schema_version,
        additional_info=f"auth-preflight-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}",
    )

    if preflight.status_code in {-1, -2, -3}:
        pytest.skip(
            "CTA SubmitData authorization failed for configured credentials "
            f"(status {preflight.status_code}). Update NEMSIS_CTA_USERNAME, "
            "NEMSIS_CTA_PASSWORD, and NEMSIS_CTA_ORGANIZATION with submit-enabled values."
        )

    return username, password, organization, client


@pytest.mark.asyncio
async def test_vendor_pack_dem_and_ems_cases_pass(
    _authorized_submit_context: tuple[str, str, str, NEMSISProductionClient],
) -> None:
    username, password, organization, client = _authorized_submit_context
    validator = NEMSISValidator()

    expected_ids = {
        "2025-DEM-1-FullSet_v351",
        "2025-EMS-1-Allergy_v351",
        "2025-EMS-2-HeatStroke_v351",
        "2025-EMS-3-PediatricAsthma_v351",
        "2025-EMS-4-ArmTrauma_v351",
        "2025-EMS-5-MentalHealthCrisis_v351",
    }
    discovered_ids = {case.case_id for case in list_cta_cases()}
    missing = expected_ids - discovered_ids
    assert not missing, f"Missing CTA cases in repository parser: {sorted(missing)}"

    dem_case = get_cta_case("2025-DEM-1-FullSet_v351")
    dem_artifact = generate_cta_case_xml(dem_case)
    assert not dem_artifact.unresolved_placeholders, dem_artifact.unresolved_placeholders
    dem_validation = validator.validate_xml_bytes(dem_artifact.xml_bytes, state_code="FL")
    dem_errors = [issue for issue in dem_validation.issues if issue.severity == "error"]
    assert not dem_errors, [issue.to_dict() for issue in dem_errors]

    dem_status = await _submit_and_wait(
        client,
        username,
        password,
        organization,
        xml_bytes=dem_artifact.xml_bytes,
        request_data_schema=dem_case.request_data_schema,
        schema_version=dem_case.schema_version,
        additional_info=dem_case.case_id,
    )
    assert dem_status in _PASS_STATUS_CODES, f"DEM case failed with status {dem_status}"

    failures: list[str] = []
    ems_case_ids = [
        "2025-EMS-1-Allergy_v351",
        "2025-EMS-2-HeatStroke_v351",
        "2025-EMS-3-PediatricAsthma_v351",
        "2025-EMS-4-ArmTrauma_v351",
        "2025-EMS-5-MentalHealthCrisis_v351",
    ]
    for case_id in ems_case_ids:
        case = get_cta_case(case_id)
        artifact = generate_cta_case_xml(case, reference_dem_xml=dem_artifact.xml_bytes)
        if artifact.unresolved_placeholders:
            failures.append(f"{case_id}: unresolved placeholders {artifact.unresolved_placeholders}")
            continue

        validation = validator.validate_xml_bytes(artifact.xml_bytes, state_code="FL")
        errors = [issue for issue in validation.issues if issue.severity == "error"]
        if errors:
            failures.append(f"{case_id}: local validation errors present")
            continue

        status = await _submit_and_wait(
            client,
            username,
            password,
            organization,
            xml_bytes=artifact.xml_bytes,
            request_data_schema=case.request_data_schema,
            schema_version=case.schema_version,
            additional_info=case.case_id,
        )
        if status not in _PASS_STATUS_CODES:
            failures.append(f"{case_id}: CTA status {status}")

    assert not failures, "\n".join(failures)


@pytest.mark.asyncio
async def test_vendor_pack_state_case_passes(
    _authorized_submit_context: tuple[str, str, str, NEMSISProductionClient],
) -> None:
    username, password, organization, client = _authorized_submit_context

    assert _STATE_XML_PATH.exists(), f"State case XML not found: {_STATE_XML_PATH}"
    state_xml = _STATE_XML_PATH.read_bytes()

    status = await _submit_and_wait(
        client,
        username,
        password,
        organization,
        xml_bytes=state_xml,
        request_data_schema=65,
        schema_version="3.5.1",
        additional_info="2025-STATE-1-FullSet_v351",
    )

    assert status in _PASS_STATUS_CODES, f"STATE case failed with status {status}"

"""
Tests for NEMSIS production client models.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core_app.nemsis.models import (
    NEMSISDataSchema,
    QueryLimitStatusCode,
    RetrieveStatusCode,
    SubmitDataRequest,
    SubmitDataStatusCode,
    SupportedSchemaVersion,
    XmlValidationErrorInfo,
)


class TestNEMSISDataSchema:
    """Test schema enumeration."""

    def test_ems_dataset_value(self) -> None:
        assert NEMSISDataSchema.EMS_DATASET == 61

    def test_demographics_dataset_value(self) -> None:
        assert NEMSISDataSchema.DEMOGRAPHICS == 62

    def test_state_dataset_value(self) -> None:
        assert NEMSISDataSchema.STATE_DATASET == 65


class TestStatusCodes:
    """Test status code enumerations."""

    def test_query_limit_success(self) -> None:
        assert QueryLimitStatusCode.SUCCESS == 51

    def test_query_limit_server_busy(self) -> None:
        assert QueryLimitStatusCode.SERVER_BUSY == -50

    def test_submit_data_success(self) -> None:
        assert SubmitDataStatusCode.SUCCESSFUL == 1

    def test_submit_data_async_pending(self) -> None:
        assert SubmitDataStatusCode.PROCESSING_PENDING == 10

    def test_submit_data_xml_validation_failed(self) -> None:
        assert SubmitDataStatusCode.XML_VALIDATION_FAILED == -12

    def test_retrieve_status_pending(self) -> None:
        assert RetrieveStatusCode.PROCESSING_PENDING == 0

    def test_retrieve_status_invalid_handle(self) -> None:
        assert RetrieveStatusCode.INVALID_HANDLE_FORMAT == -42


class TestSupportedSchemaVersion:
    """Test schema version constants."""

    def test_version_340_supported(self) -> None:
        assert SupportedSchemaVersion.V_3_4_0 in SupportedSchemaVersion.SUPPORTED

    def test_version_350_supported(self) -> None:
        assert SupportedSchemaVersion.V_3_5_0 in SupportedSchemaVersion.SUPPORTED

    def test_version_351_supported(self) -> None:
        assert SupportedSchemaVersion.V_3_5_1 in SupportedSchemaVersion.SUPPORTED

    def test_unsupported_version(self) -> None:
        version = "2.0.0"
        assert version not in SupportedSchemaVersion.SUPPORTED


class TestSubmitDataRequest:
    """Test SubmitData request model validation."""

    def test_invalid_schema_type(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SubmitDataRequest(
                username="user1",
                password="pass123",
                organization="org1",
                submit_payload=None,
                request_data_schema=99,  # Invalid
                schema_version="3.5.1",
            )
        assert "Invalid schema code" in str(exc_info.value)

    def test_invalid_schema_version(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SubmitDataRequest(
                username="user1",
                password="pass123",
                organization="org1",
                submit_payload=None,
                request_data_schema=61,
                schema_version="2.0.0",  # Unsupported
            )
        assert "Unsupported schema version" in str(exc_info.value)

    def test_username_length_validation(self) -> None:
        with pytest.raises(ValidationError):
            SubmitDataRequest(
                username="",  # Too short
                password="pass123",
                organization="org1",
                submit_payload=None,
                request_data_schema=61,
                schema_version="3.5.1",
            )

    def test_password_max_length_validation(self) -> None:
        # Password max length is 250 per WSDL spec
        long_password = "x" * 251
        with pytest.raises(ValidationError):
            SubmitDataRequest(
                username="user1",
                password=long_password,
                organization="org1",
                submit_payload=None,
                request_data_schema=61,
                schema_version="3.5.1",
            )


class TestXmlValidationErrorInfo:
    """Test XML validation error model."""

    def test_error_with_line_column(self) -> None:
        error = XmlValidationErrorInfo(
            element_name="EMSDataSet",
            line=10,
            column=5,
            description="Invalid element",
        )
        assert error.line == 10
        assert error.column == 5

    def test_error_with_xpath(self) -> None:
        error = XmlValidationErrorInfo(
            element_name="Patient",
            xpath_location="/EMSDataSet/DEM/Patient[1]",
            description="Missing required element",
        )
        assert error.xpath_location == "/EMSDataSet/DEM/Patient[1]"

    def test_error_with_value(self) -> None:
        error = XmlValidationErrorInfo(
            element_name="Age",
            value="not-a-number",
            description="Invalid integer value",
        )
        assert error.value == "not-a-number"

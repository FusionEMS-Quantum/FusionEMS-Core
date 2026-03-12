"""
Production-ready NEMSIS V3 Web Services data models.

Pydantic models for standardized request/response handling with the NEMSIS WSDL.
Supports EMSDataSet, DEMDataSet, and StateDataSet schemas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# Data Schema Enumerations (per NEMSIS WSDL)
class NEMSISDataSchema(IntEnum):
    """NEMSIS standard schema codes."""
    EMS_DATASET = 61
    DEMOGRAPHICS = 62
    CAD = 63
    MEDICAL_DEVICE = 64
    STATE_DATASET = 65


class SupportedSchemaVersion(str):
    """Supported NEMSIS schema versions by national database."""
    V_3_4_0 = "3.4.0"
    V_3_5_0 = "3.5.0"
    V_3_5_1 = "3.5.1"

    SUPPORTED = {V_3_4_0, V_3_5_0, V_3_5_1}


# Status Code Enumerations (per NEMSIS WSDL spec)
class QueryLimitStatusCode(IntEnum):
    """QueryLimit operation response codes."""
    SUCCESS = 51
    SERVER_BUSY = -50
    FAILED = -51


class SubmitDataStatusCode(IntEnum):
    """SubmitData operation response codes."""
    # Success codes
    SUCCESSFUL = 1
    SUCCESS_WITH_ERROR_WARNINGS = 2
    SUCCESS_WITH_WARNING = 3
    SUCCESS_WITH_ETL_WARNING = 4
    SUCCESS_WITH_BI_WARNING = 5
    PARTIALLY_SUCCESSFUL_WITH_ERRORS = 6
    PROCESSING_PENDING = 10
    
    # Error codes
    DUPLICATE_FILE = -11
    XML_VALIDATION_FAILED = -12
    FATAL_SCHEMATRON = -13
    ERROR_SCHEMATRON = -14
    CRITICAL_ETL_VIOLATION = -15
    CRITICAL_BI_VIOLATION = -16
    MESSAGE_SIZE_EXCEEDED = -30
    
    # Common errors (inherited)
    GENERIC_SERVER_ERROR = -20
    DATABASE_ERROR = -21
    FILE_SYSTEM_ERROR = -22
    INVALID_CREDENTIALS = -1
    PERMISSION_DENIED_OP = -2
    PERMISSION_DENIED_ORG = -3
    INVALID_PARAMETER = -4
    INVALID_PARAMETER_COMBO = -5


class RetrieveStatusCode(IntEnum):
    """RetrieveStatus operation response codes."""
    PROCESSING_PENDING = 0
    
    # Error codes
    STATUS_UNAVAILABLE = -40
    STATUS_EXPIRED = -41
    INVALID_HANDLE_FORMAT = -42
    HANDLE_NEVER_USED = -43


# Privilege/Auth Group (part of all requests)
class PrivilegeCredentials(BaseModel):
    """Authentication credentials included in all NEMSIS requests."""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=250)
    organization: str = Field(..., min_length=1, max_length=100)


# Data Payload Models
class PayloadOfXmlElement(BaseModel):
    """XML element wrapper for data payload."""
    
    class Config:
        arbitrary_types_allowed = True

    xml_content: str = Field(
        ...,
        description="Raw XML document bytes as string"
    )


class DataPayload(BaseModel):
    """Data submission payload container."""
    payload_of_xml_element: PayloadOfXmlElement


# Request Models
class QueryLimitRequest(BaseModel):
    """QueryLimit SOAP request."""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=250)
    organization: str = Field(..., min_length=1, max_length=100)
    request_type: str = Field(default="QueryLimit")


class SubmitDataRequest(BaseModel):
    """SubmitData SOAP request for data submission."""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=250)
    organization: str = Field(..., min_length=1, max_length=100)
    request_type: str = Field(default="SubmitData")
    
    submit_payload: DataPayload
    request_data_schema: int = Field(
        ...,
        description="Schema code (61=EMS, 62=Dem, 65=State)"
    )
    schema_version: str = Field(
        ...,
        description="Schema version (3.4.0, 3.5.0, 3.5.1)"
    )
    additional_info: str = Field(
        default="",
        description="Optional metadata/change notes"
    )

    @field_validator("request_data_schema")
    @classmethod
    def validate_schema(cls, v: int) -> int:
        valid_schemas = {61, 62, 65}
        if v not in valid_schemas:
            raise ValueError(f"Invalid schema code. Must be one of {valid_schemas}")
        return v

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if v not in SupportedSchemaVersion.SUPPORTED:
            raise ValueError(
                f"Unsupported schema version {v}. "
                f"Supported: {SupportedSchemaVersion.SUPPORTED}"
            )
        return v


class RetrieveStatusRequest(BaseModel):
    """RetrieveStatus SOAP request for async results."""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=250)
    organization: str = Field(..., min_length=1, max_length=100)
    request_type: str = Field(default="RetrieveStatus")
    
    request_handle: str = Field(..., description="Handle from prior submission")
    original_request_type: str = Field(default="SubmitData")
    additional_info: str = Field(default="")


# Response Models  
class QueryLimitResponse(BaseModel):
    """QueryLimit SOAP response."""
    request_type: str
    limit: int = Field(
        description="Size limit in KB (positive=success, negative=error)"
    )
    status_code: int


class XmlValidationErrorInfo(BaseModel):
    """Single XML validation error detail."""
    element_name: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    xpath_location: Optional[str] = None
    value: Optional[str] = None
    description: str = Field(...)


class XmlValidationErrorReport(BaseModel):
    """XML Schema (XSD) validation report."""
    total_error_count: int
    errors: list[XmlValidationErrorInfo] = Field(default_factory=list)


class SchematronErrorInfo(BaseModel):
    """Single Schematron validation error/warning."""
    rule_id: str
    severity: str = Field(description="[FATAL], [ERROR], [WARNING]")
    message: str
    xpath_location: Optional[str] = None


class SchematronReport(BaseModel):
    """Schematron business rules validation report."""
    errors: list[SchematronErrorInfo] = Field(default_factory=list)


class SubmitDataReport(BaseModel):
    """Complete submission validation and processing report."""
    xml_validation_report: XmlValidationErrorReport
    schematron_report: Optional[SchematronReport] = None
    custom_reports: list[dict[str, Any]] = Field(default_factory=list)


class SubmitDataResponse(BaseModel):
    """SubmitData SOAP response."""
    request_type: str
    request_handle: str = Field(description="Unique transaction ID")
    status_code: int
    reports: Optional[SubmitDataReport] = None


class RetrieveStatusResponse(BaseModel):
    """RetrieveStatus SOAP response."""
    request_type: str
    status_code: int
    request_handle: str
    original_request_type: Optional[str] = None
    retrieve_result: Optional[SubmitDataReport] = None


# Domain Models for Service Layer
@dataclass(frozen=True)
class SubmissionMetadata:
    """Metadata tracking for a data submission."""
    request_handle: str
    schema_type: int  # 61, 62, or 65
    schema_version: str
    organization: str
    status_code: int
    submitted_at: datetime
    submission_type: str = "full"  # full or national_only
    additional_info: str = ""
    
    def is_processing(self) -> bool:
        """True if submission is still pending."""
        return self.status_code in {0, 10}


@dataclass(frozen=True)
class SubmissionResult:
    """Result object from successful data submission."""
    request_handle: str
    status_code: int
    status_message: str
    is_async: bool
    reports: Optional[SubmitDataReport] = None
    submitted_at: Optional[datetime] = None
    
    def is_successful(self) -> bool:
        """True if submission was accepted (sync or async)."""
        return self.status_code >= 0
    
    def is_pending(self) -> bool:
        """True if results not yet available."""
        return self.status_code in {0, 10}

# NEMSIS V3 Web Services Implementation

Production-ready NEMSIS V3 Web Services client for FusionEMS.

## Overview

This implementation provides full support for NEMSIS V3 compliance including:

- **Data Submission**: EMSDataSet (61), DEMDataSet (62), StateDataSet (65)
- **Schema Support**: v3.4.0, v3.5.0, v3.5.1
- **Async Handling**: Request handles for long-running validations
- **Transport**: HTTPS/SOAP with TLS 1.2+
- **Error Handling**: Comprehensive validation and error reporting
- **Observability**: OpenTelemetry correlation tracking, structured logging

## Architecture

### Components

1. **`models.py`** - Pydantic models for NEMSIS WSDL types
   - Request/response models with validation
   - Status code enumerations
   - Domain models for service layer

2. **`production_client.py`** - SOAP client
   - `NEMSISProductionClient`: Low-level SOAP operations
   - Async/await support with httpx
   - Three main operations: SubmitData, RetrieveStatus, QueryLimit
   - Proper error handling with custom exceptions

3. **`submission_service.py`** - Business logic orchestration
   - `NEMSISSubmissionService`: High-level submission API
   - Dataset-specific submit methods (EMS, DEM, State)
   - Async result retrieval
   - Submission tracking and correlation

4. **`nemsis_routes.py`** - REST API endpoints
   - POST `/api/v1/nemsis/submit/ems` - Submit EMS data
   - POST `/api/v1/nemsis/submit/dem` - Submit DEM data
   - POST `/api/v1/nemsis/submit/state` - Submit State data
   - POST `/api/v1/nemsis/status` - Check async submission status
   - POST `/api/v1/nemsis/wait/{request_handle}` - Blocking wait for results

### Data Flow

```
┌─────────────────────┐
│ FusionEMS API Route │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────┐
│ SubmissionService       │
│ - Validation            │
│ - Submission tracking   │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ NEMSISProductionClient  │
│ - SOAP envelope build   │
│ - HTTP POST             │
│ - Response parsing      │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ NEMSIS Server           │
│ (National or Regional)  │
└─────────────────────────┘
```

## Usage

### Basic Submission (Sync)

```python
from core_app.nemsis.submission_service import NEMSISSubmissionService

service = NEMSISSubmissionService()

# Submit EMS data and wait for immediate response
result = await service.submit_ems_data(
    xml_bytes=ems_xml_content,
    organization="my-org-id",
    username="nemsis_user",
    password="nemsis_pass",
    schema_version="3.5.1",
    additional_info="Daily batch submission",
)

print(f"Status: {result.status_code}")
print(f"Handle: {result.request_handle}")
print(f"Async: {result.is_async}")
```

### Async Submission + Polling

```python
# Submit
result = await service.submit_ems_data(...)
if result.is_async:
    print(f"Async submission, handle: {result.request_handle}")
    
    # Poll for status
    status = await service.retrieve_submission_status(
        request_handle=result.request_handle,
        organization="my-org-id",
        username="nemsis_user",
        password="nemsis_pass",
    )
    
    if not status["is_complete"]:
        print(f"Still processing...")
```

### Wait for Results

```python
# Block until submission complete (with timeout)
status = await service.wait_for_submission(
    request_handle="handle-from-submission",
    organization="my-org-id",
    username="nemsis_user",
    password="nemsis_pass",
    poll_interval_seconds=5.0,
    max_wait_seconds=3600.0,  # 1 hour
)
```

### Rest API Endpoints

```bash
# Submit EMS data
curl -X POST http://localhost:8000/api/v1/nemsis/submit/ems \
  -F "file=@ems_data.xml" \
  -F "schema_version=3.5.1" \
  -F "additional_info=Daily batch"

# Check async status
curl -X POST http://localhost:8000/api/v1/nemsis/status \
  -H "Content-Type: application/json" \
  -d '{"request_handle": "<handle-from-submit>"}'

# Wait for completion (blocking)
curl -X POST http://localhost:8000/api/v1/nemsis/wait/<handle> \
  -H "Content-Type: application/json"
```

## Configuration

Add these environment variables to your `.env` or deployment config:

```env
# Production NEMSIS endpoint (national database)
NEMSIS_NATIONAL_ENDPOINT=https://nemsis.org/nemsisWs.wsdl
NEMSIS_NATIONAL_TIMEOUT_SECONDS=60

# Testing endpoint (compliance testing automation)
NEMSIS_CTA_ENDPOINT=https://cta.nemsis.org:443/ComplianceTestingWs/endpoints/
NEMSIS_CTA_TIMEOUT_SECONDS=30
```

Credentials should be stored in organization settings, not hardcoded:
- `org_context.nemsis_username`
- `org_context.nemsis_password`  
- `org_context.organization_id`

## Error Handling

### Status Codes

**Success Codes**:
- `1`: Data imported successfully
- `2`: Imported with Schematron WARNING level
- `3`: Imported with other warnings
- `10`: Validation passed, processing pending (use RetrieveStatus)

**Processing**:
- `0`: Still processing (async)
- `10`: Validation complete, processing pending

**Errors**:
- `-1`: Invalid credentials
- `-12`: XML validation failed
- `-13`: Fatal Schematron rule violation
- `-14`: Error-level Schematron violation
- `-20` to `-22`: Server errors
- `-30`: SOAP message too large

### Exception Hierarchy

```
NEMSISClientError (base)
├── NEMSISAuthenticationError
├── NEMSISValidationError
├── NEMSISTimeoutError
└── NEMSISServerError
```

## Observability

### OpenTelemetry Integration

All operations are traced:

```python
# Spans created for:
- nemsis.submit_data
- nemsis.retrieve_status
- nemsis.wait_for_result
- nemsis.soap_request
- nemsis_service.submit
- nemsis_service.retrieve_status
- nemsis_service.wait_for_submission
```

### Structured Logging

JSON-formatted logs include:
- `correlation_id`: Request tracing
- `schema`: Dataset type (EMS/DEM/State)
- `organization`: Organization submitting
- `status_code`: Response code from NEMSIS
- `request_handle`: Unique submission ID

```python
# Example log
{
  "timestamp": "2026-03-12T10:30:45Z",
  "level": "INFO",
  "message": "nemsis_submit_result",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "handle": "handle-xyz123",
  "status": 1,
  "async": false
}
```

## Compliance

This implementation follows NEMSIS V3 Web Services specification:

- ✅ SOAP 1.1 protocol
- ✅ HTTPS/TLS 1.2+ transport
- ✅ Username/password/organization authentication in SOAP envelope
- ✅ Three required operations: SubmitData, RetrieveStatus, QueryLimit
- ✅ Asynchronous request/response with request handles
- ✅ Status codes per WSDL specification
- ✅ Validation report structure (XSD + Schematron)
- ✅ Support for all schema types (EMS, DEM, State)
- ✅ National elements only submissions
- ✅ Correlation ID tracking for auditing

## Testing

### Pre-Testing with Compliance Testing Automation (CTA)

The existing `NEMSISCTASoapClient` in `cta_soap_client.py` can be used for:
- Compliance testing before production
- Validating submissions against test fixtures
- Verifying Schematron and XSD validation

```python
from core_app.nemsis.cta_soap_client import NEMSISCTASoapClient, CTACredentials

cta_client = NEMSISCTASoapClient()
creds = CTACredentials(
    username="test_user",
    password="test_pass",
    organization="test_org",
)

# Query limit
result = await cta_client.query_limit(creds)
print(f"Size limit: {result.limit_kb} KB")

# Submit test data
submit_result = await cta_client.submit_data(
    creds,
    xml_bytes=test_ems_xml,
    request_data_schema=61,
    schema_version="3.5.1",
    additional_info="",
)
```

### Production Testing

```python
from core_app.nemsis.production_client import NEMSISProductionClient

client = NEMSISProductionClient(
    endpoint_url="https://nemsis.org/nemsisWs.wsdl",
    timeout_seconds=60,
)

# Test QueryLimit
limit_response = await client.query_limit(
    username="prod_user",
    password="prod_pass",
    organization="prod_org",
)
```

## Testing Data

Pre-testing XML files provided:
- `/Downloads/pretesting/xml/full/` - Valid test cases
- `/Downloads/pretesting/xml/fail/` - Invalid test cases (XSD/Schematron failures)
- `/Downloads/pretesting/xml/national/` - National-elements-only variants
- `/Downloads/pretesting/schematron/` - Schematron rule files

## Integration Points

### Database

Consider adding tables for:
- `nemsis_submissions` - Track all submissions
- `nemsis_handles` - Map handles to submissions
- `nemsis_validation_logs` - Schematron/XSD errors

### Event System

Consider emitting events for:
- Submission received
- Validation complete
- Processing complete
- Submission failed

### Audit Trail

All NEMSIS operations should be logged to audit trail:
- Operation type
- Timestamp
- Organization
- Username
- Data size
- Result code

## References

- [NEMSIS V3 Web Services Guide](https://nemsis.org/media/nemsis_v3/master/WSDL/NEMSIS_V3_core.wsdl)
- [NEMSIS Compliance Testing Guide](https://nemsis.org/technical-resources/version-3/v3-compliance/)
- [NEMSIS Validator](https://validator.nemsis.org/)
- [Compliance Testing Automation](https://cta.nemsis.org/ComplianceTestingWebapp)

## Future Enhancements

1. **Batch Submissions**: Queue multiple datasets for batch processing
2. **Schematron Caching**: Cache Schematron rules locally
3. **Custom Error Codes**: Add organization-specific error code mappings
4. **Metrics**: Track submission throughput, latency, success rates
5. **Webhooks**: Notify external systems when submissions complete
6. **Retry Logic**: Exponential backoff for transient failures

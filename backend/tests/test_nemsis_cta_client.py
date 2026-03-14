from __future__ import annotations

import xml.etree.ElementTree as ET

from core_app.nemsis.cta_soap_client import (
    CTACredentials,
    NEMSISCTASoapClient,
    _read_int,
    _read_text,
    normalize_cta_state,
    translate_cta_code,
)


def test_submit_envelope_includes_request_data_schema_and_schema_version() -> None:
    client = NEMSISCTASoapClient(endpoint_url="https://example.test")
    request_xml = client._build_submit_request(
        CTACredentials(username="demo", password="secret", organization="fusion"),
        xml_bytes=b'<?xml version="1.0" encoding="UTF-8"?><DEMDataSet xmlns="http://www.nemsis.org" />',
        request_data_schema=62,
        schema_version="3.5.1",
        additional_info="2025-DEM-1-FullSet_v351",
    )

    root = ET.fromstring(request_xml.encode("utf-8"))
    request_data_schema = next((element.text for element in root.iter() if element.tag.endswith('requestDataSchema')), None)
    schema_version = next((element.text for element in root.iter() if element.tag.endswith('schemaVersion')), None)
    additional_info = next((element.text for element in root.iter() if element.tag.endswith('additionalInfo')), None)

    assert request_data_schema == "62"
    assert schema_version == "3.5.1"
    assert additional_info == "2025-DEM-1-FullSet_v351"


def test_submit_response_parser_extracts_status_code_and_request_handle() -> None:
    response_xml = """
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
      <soapenv:Body>
        <SubmitDataResponse xmlns="http://ws.nemsis.org/">
          <statusCode>10</statusCode>
          <requestHandle>abc-123</requestHandle>
        </SubmitDataResponse>
      </soapenv:Body>
    </soapenv:Envelope>
    """

    assert _read_int(response_xml, "statusCode") == 10
    assert _read_text(response_xml, "requestHandle") == "abc-123"


def test_translate_codes_return_operator_friendly_labels() -> None:
    assert translate_cta_code(-1) == "Failed: Wrong Login"
    assert translate_cta_code(-11) == "Failed: Duplicate Submission"
    assert translate_cta_code(1) == "Passed"
    assert translate_cta_code(10) == "Waiting on NEMSIS"


def test_normalize_cta_state_maps_pending_and_final_states() -> None:
    assert normalize_cta_state(10) == "pending"
    assert normalize_cta_state(1) == "passed"
    assert normalize_cta_state(2) == "passed_with_warnings"
    assert normalize_cta_state(-12) == "failed"

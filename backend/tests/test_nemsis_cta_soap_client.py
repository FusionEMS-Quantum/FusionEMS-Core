from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from core_app.nemsis.cta_soap_client import CTACredentials, NEMSISCTASoapClient


@pytest.mark.asyncio
async def test_query_limit_accepts_limit_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NEMSISCTASoapClient(endpoint_url="https://example.test")

    async def _fake_post_soap(soap_action: str, request_xml: str) -> str:
        del soap_action, request_xml
        return (
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">'
            '<SOAP-ENV:Body>'
            '<ns2:QueryLimitResponse xmlns:ns2="http://ws.nemsis.org/">'
            '<ns2:limit>500</ns2:limit>'
            '<ns2:statusCode>51</ns2:statusCode>'
            '</ns2:QueryLimitResponse>'
            '</SOAP-ENV:Body>'
            '</SOAP-ENV:Envelope>'
        )

    monkeypatch.setattr(client, "_post_soap", _fake_post_soap)

    result = await client.query_limit(CTACredentials(username="u", password="p", organization="o"))

    assert result.limit_kb == 500
    assert result.status_code == 51


def test_submit_request_uses_wsdl_wrapper_and_request_type() -> None:
    client = NEMSISCTASoapClient(endpoint_url="https://example.test")

    xml_text = client._build_submit_request(
        CTACredentials(username="u", password="p", organization="o"),
        xml_bytes=b'<DEMDataSet xmlns="http://www.nemsis.org"/>',
        request_data_schema=62,
        schema_version="3.5.1",
        additional_info="case-1",
    )

    root = ET.fromstring(xml_text)
    body_children = list(root[0])

    assert body_children
    assert body_children[0].tag.endswith("SubmitDataRequest")
    request_type = next(child for child in body_children[0] if child.tag.endswith("requestType"))
    assert request_type.text == "SubmitData"
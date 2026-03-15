from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import defusedxml.ElementTree as _defused_et
import httpx

from core_app.core.config import get_settings

SOAP_ENV_NS = "http://schemas.xmlsoap.org/soap/envelope/"
CTA_NS = "http://ws.nemsis.org/"

logger = logging.getLogger(__name__)

_CTA_CODE_MESSAGES: dict[int, str] = {
    -43: "Failed: Tracking Handle Expired",
    -42: "Failed: Tracking Handle Invalid",
    -41: "Failed: Tracking Handle Invalid",
    -40: "Failed: Tracking Handle Invalid",
    -30: "Failed: File Too Large",
    -22: "Failed: CTA File or Network Error",
    -21: "Failed: CTA Database or Server Error",
    -20: "Failed: CTA Server Error",
    -16: "Failed: Critical BI Issue",
    -15: "Failed: Critical ETL Issue",
    -14: "Failed: Error-Level Rules Failure",
    -13: "Failed: Fatal Rules Failure",
    -12: "Failed: XML Error",
    -11: "Failed: Duplicate Submission",
    -5: "Failed: Invalid Request Combination",
    -4: "Failed: Invalid Request Value",
    -3: "Failed: Organization Permission Issue",
    -2: "Failed: Permission Issue",
    -1: "Failed: Wrong Login",
    0: "Waiting on NEMSIS",
    1: "Passed",
    2: "Passed with Warnings",
    3: "Passed with Warnings",
    10: "Waiting on NEMSIS",
}
_PASSWORD_RE = re.compile(r"(<(?:\w+:)?password>)(.*?)(</(?:\w+:)?password>)", re.DOTALL)
_USERNAME_RE = re.compile(r"(<(?:\w+:)?username>)(.*?)(</(?:\w+:)?username>)", re.DOTALL)


@dataclass(frozen=True)
class CTACredentials:
    username: str
    password: str
    organization: str


@dataclass(frozen=True)
class CTAQueryLimitResult:
    status_code: int
    limit_kb: int | None
    message: str
    raw_response_xml: str
    sanitized_request_xml: str


@dataclass(frozen=True)
class CTASubmitResult:
    status_code: int
    request_handle: str | None
    message: str
    raw_response_xml: str
    sanitized_request_xml: str


@dataclass(frozen=True)
class CTARetrieveStatusResult:
    status_code: int
    request_handle: str | None
    message: str
    reports: dict[str, Any]
    raw_response_xml: str
    sanitized_request_xml: str


class CTAClientError(RuntimeError):
    pass


class NEMSISCTASoapClient:
    def __init__(self, endpoint_url: str | None = None, timeout_seconds: float | None = None) -> None:
        settings = get_settings()
        self._endpoint_url = endpoint_url or settings.nemsis_cta_endpoint
        self._timeout = timeout_seconds or settings.nemsis_cta_timeout_seconds

    async def query_limit(self, credentials: CTACredentials) -> CTAQueryLimitResult:
        request_xml = self._build_query_limit_request(credentials)
        response_xml = await self._post_soap("QueryLimit", request_xml)
        status_code = _read_int(response_xml, "statusCode")
        limit_kb = _read_optional_int(response_xml, "queryLimit", "limit")
        return CTAQueryLimitResult(
            status_code=status_code,
            limit_kb=limit_kb,
            message=translate_cta_code(status_code),
            raw_response_xml=response_xml,
            sanitized_request_xml=_sanitize_request_xml(request_xml),
        )

    async def submit_data(
        self,
        credentials: CTACredentials,
        *,
        xml_bytes: bytes,
        request_data_schema: int,
        schema_version: str,
        additional_info: str,
    ) -> CTASubmitResult:
        request_xml = self._build_submit_request(
            credentials,
            xml_bytes=xml_bytes,
            request_data_schema=request_data_schema,
            schema_version=schema_version,
            additional_info=additional_info,
        )
        response_xml = await self._post_soap("SubmitData", request_xml)
        status_code = _read_int(response_xml, "statusCode")
        request_handle = _read_text(response_xml, "requestHandle")
        return CTASubmitResult(
            status_code=status_code,
            request_handle=request_handle,
            message=translate_cta_code(status_code),
            raw_response_xml=response_xml,
            sanitized_request_xml=_sanitize_request_xml(request_xml),
        )

    async def retrieve_status(
        self,
        credentials: CTACredentials,
        *,
        request_handle: str,
        original_request_type: str = "SubmitData",
        additional_info: str = "",
    ) -> CTARetrieveStatusResult:
        request_xml = self._build_retrieve_status_request(
            credentials,
            request_handle=request_handle,
            original_request_type=original_request_type,
            additional_info=additional_info,
        )
        response_xml = await self._post_soap("RetrieveStatus", request_xml)
        status_code = _read_int(response_xml, "statusCode")
        reports = _extract_reports(response_xml)
        return CTARetrieveStatusResult(
            status_code=status_code,
            request_handle=_read_text(response_xml, "requestHandle") or request_handle,
            message=translate_cta_code(status_code),
            reports=reports,
            raw_response_xml=response_xml,
            sanitized_request_xml=_sanitize_request_xml(request_xml),
        )

    def _build_query_limit_request(self, credentials: CTACredentials) -> str:
        envelope = _soap_envelope("QueryLimitRequest")
        body = _body_element(envelope)
        request_element = ET.SubElement(body, ET.QName(CTA_NS, "QueryLimitRequest"))
        _add_text(request_element, "username", credentials.username)
        _add_text(request_element, "password", credentials.password)
        _add_text(request_element, "organization", credentials.organization)
        _add_text(request_element, "requestType", "QueryLimit")
        return _xml_to_string(envelope)

    def _build_submit_request(
        self,
        credentials: CTACredentials,
        *,
        xml_bytes: bytes,
        request_data_schema: int,
        schema_version: str,
        additional_info: str,
    ) -> str:
        envelope = _soap_envelope("SubmitDataRequest")
        body = _body_element(envelope)
        request_element = ET.SubElement(body, ET.QName(CTA_NS, "SubmitDataRequest"))
        _add_text(request_element, "username", credentials.username)
        _add_text(request_element, "password", credentials.password)
        _add_text(request_element, "organization", credentials.organization)
        _add_text(request_element, "requestType", "SubmitData")
        submit_payload = ET.SubElement(request_element, ET.QName(CTA_NS, "submitPayload"))
        payload_element = ET.SubElement(submit_payload, ET.QName(CTA_NS, "payloadOfXmlElement"))
        parsed_payload = _defused_et.fromstring(xml_bytes)
        payload_element.append(parsed_payload)
        _add_text(request_element, "requestDataSchema", str(request_data_schema))
        _add_text(request_element, "schemaVersion", schema_version)
        _add_text(request_element, "additionalInfo", additional_info)
        return _xml_to_string(envelope)

    def _build_retrieve_status_request(
        self,
        credentials: CTACredentials,
        *,
        request_handle: str,
        original_request_type: str,
        additional_info: str,
    ) -> str:
        envelope = _soap_envelope("RetrieveStatusRequest")
        body = _body_element(envelope)
        request_element = ET.SubElement(body, ET.QName(CTA_NS, "RetrieveStatusRequest"))
        _add_text(request_element, "username", credentials.username)
        _add_text(request_element, "password", credentials.password)
        _add_text(request_element, "organization", credentials.organization)
        _add_text(request_element, "requestType", "RetrieveStatus")
        _add_text(request_element, "requestHandle", request_handle)
        _add_text(request_element, "originalRequestType", original_request_type)
        _add_text(request_element, "additionalInfo", additional_info)
        return _xml_to_string(envelope)

    async def _post_soap(self, soap_action: str, request_xml: str) -> str:
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{CTA_NS}{soap_action}"',
        }
        logger.info(
            "nemsis_cta_request",
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
            raise CTAClientError("Timed out waiting for NEMSIS CTA response") from exc
        except httpx.HTTPError as exc:
            raise CTAClientError(f"NEMSIS CTA request failed: {exc}") from exc
        return response.text


def translate_cta_code(status_code: int) -> str:
    return _CTA_CODE_MESSAGES.get(status_code, f"CTA status code {status_code}")


def normalize_cta_state(status_code: int) -> str:
    if status_code in {1}:
        return "passed"
    if status_code in {2, 3}:
        return "passed_with_warnings"
    if status_code in {0, 10}:
        return "pending"
    return "failed"


def _soap_envelope(_request_type: str) -> ET.Element:
    ET.register_namespace("soapenv", SOAP_ENV_NS)
    ET.register_namespace("ws", CTA_NS)
    return ET.Element(ET.QName(SOAP_ENV_NS, "Envelope"))


def _body_element(envelope: ET.Element) -> ET.Element:
    return ET.SubElement(envelope, ET.QName(SOAP_ENV_NS, "Body"))


def _add_text(parent: ET.Element, tag: str, value: str) -> None:
    element = ET.SubElement(parent, ET.QName(CTA_NS, tag))
    element.text = value


def _xml_to_string(element: ET.Element) -> str:
    ET.indent(element, space="  ")
    return ET.tostring(element, encoding="unicode")


def _read_text(xml_text: str, tag_name: str) -> str | None:
    try:
        root = _defused_et.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        return None
    for element in root.iter():
        if _local_name(element.tag) != tag_name:
            continue
        text = (element.text or "").strip()
        if text:
            return text
    return None


def _read_int(xml_text: str, tag_name: str) -> int:
    text = _read_text(xml_text, tag_name)
    if text is None:
        return -20
    try:
        return int(text)
    except ValueError:
        return -20


def _read_optional_int(xml_text: str, *tag_names: str) -> int | None:
    for tag_name in tag_names:
        text = _read_text(xml_text, tag_name)
        if text is None:
            continue
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _extract_reports(xml_text: str) -> dict[str, Any]:
    try:
        root = _defused_et.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        return {}
    report_tags = [
        "xmlValidationReport",
        "schematronValidationReport",
        "customReport",
        "errorReport",
    ]
    reports: dict[str, Any] = {}
    for tag_name in report_tags:
        values = [element for element in root.iter() if _local_name(element.tag) == tag_name]
        if not values:
            continue
        reports[tag_name] = [ET.tostring(value, encoding="unicode") for value in values]
    return reports


def _sanitize_request_xml(xml_text: str) -> str:
    masked = _PASSWORD_RE.sub(r"\1***REDACTED***\3", xml_text)
    return _USERNAME_RE.sub(r"\1***REDACTED***\3", masked)


def _local_name(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag

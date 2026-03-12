from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import xml.etree.ElementTree as ET

import httpx

from core_app.core.config import get_settings

SOAP_ENV_NS = "http://schemas.xmlsoap.org/soap/envelope/"
PM_NS = "http://ws.nemsis.org/"


@dataclass(frozen=True)
class PMBenchmark:
    id: str
    label: str
    numerator_type: str
    denominator_type: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "label": self.label,
            "numerator_type": self.numerator_type,
            "denominator_type": self.denominator_type,
        }


@dataclass(frozen=True)
class PMParameterValue:
    code: str
    label: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "label": self.label}


@dataclass(frozen=True)
class PMParameter:
    code: str
    name: str
    values: list[PMParameterValue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "values": [value.to_dict() for value in self.values],
        }


@dataclass(frozen=True)
class PMBenchmarkFilter:
    value: str
    parameter: str | None = None


@dataclass(frozen=True)
class PMBenchmarkResult:
    segment_member: str | None
    records: int | None
    numerator: str | None
    denominator: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_member": self.segment_member,
            "records": self.records,
            "numerator": self.numerator,
            "denominator": self.denominator,
        }


@dataclass(frozen=True)
class PMDatabaseInfo:
    database_update_datetime: str | None
    database_records: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_update_datetime": self.database_update_datetime,
            "database_records": self.database_records,
        }


@dataclass(frozen=True)
class PMListBenchmarksResult:
    status_code: int
    benchmarks: list[PMBenchmark]
    error: str | None
    raw_response_xml: str
    sanitized_request_xml: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "benchmarks": [benchmark.to_dict() for benchmark in self.benchmarks],
            "error": self.error,
        }


@dataclass(frozen=True)
class PMListParametersResult:
    status_code: int
    parameters: list[PMParameter]
    error: str | None
    raw_response_xml: str
    sanitized_request_xml: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
            "error": self.error,
        }


@dataclass(frozen=True)
class PMRetrieveBenchmarkResult:
    status_code: int
    database: PMDatabaseInfo | None
    benchmark_id: str | None
    segment: str | None
    data_records: int | None
    numerator_type: str | None
    denominator_type: str | None
    states: int | None
    results: list[PMBenchmarkResult]
    error: str | None
    raw_response_xml: str
    sanitized_request_xml: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "database": self.database.to_dict() if self.database is not None else None,
            "benchmark_id": self.benchmark_id,
            "segment": self.segment,
            "data_records": self.data_records,
            "numerator_type": self.numerator_type,
            "denominator_type": self.denominator_type,
            "states": self.states,
            "results": [result.to_dict() for result in self.results],
            "error": self.error,
        }


class PMClientError(RuntimeError):
    pass


class NEMSISPMSoapClient:
    def __init__(self, endpoint_url: str | None = None, timeout_seconds: float | None = None) -> None:
        settings = get_settings()
        self._endpoint_url = endpoint_url or settings.nemsis_pm_endpoint
        self._timeout = timeout_seconds or settings.nemsis_cta_timeout_seconds

    async def list_benchmarks(self) -> PMListBenchmarksResult:
        request_xml = self._build_simple_request("ListBenchmarksRequest")
        response_xml = await self._post_soap(request_xml)
        response = _response_element(response_xml, "ListBenchmarksResponse")

        benchmarks: list[PMBenchmark] = []
        error = None
        if response is not None:
            error = _read_child_text(response, "error")
            for benchmark in _iter_children(response, "benchmark"):
                benchmarks.append(
                    PMBenchmark(
                        id=benchmark.attrib.get("id", ""),
                        label=(benchmark.text or "").strip(),
                        numerator_type=benchmark.attrib.get("numeratorType", ""),
                        denominator_type=benchmark.attrib.get("denominatorType", ""),
                    )
                )

        return PMListBenchmarksResult(
            status_code=_read_status_attribute(response),
            benchmarks=benchmarks,
            error=error,
            raw_response_xml=response_xml,
            sanitized_request_xml=request_xml,
        )

    async def list_parameters(self) -> PMListParametersResult:
        request_xml = self._build_simple_request("ListParametersRequest")
        response_xml = await self._post_soap(request_xml)
        response = _response_element(response_xml, "ListParametersResponse")

        parameters: list[PMParameter] = []
        error = None
        if response is not None:
            error = _read_child_text(response, "error")
            for parameter in _iter_children(response, "parameter"):
                values = [
                    PMParameterValue(
                        code=value.attrib.get("code", ""),
                        label=(value.text or "").strip(),
                    )
                    for value in _iter_children(parameter, "value")
                ]
                parameters.append(
                    PMParameter(
                        code=parameter.attrib.get("code", ""),
                        name=parameter.attrib.get("name", ""),
                        values=values,
                    )
                )

        return PMListParametersResult(
            status_code=_read_status_attribute(response),
            parameters=parameters,
            error=error,
            raw_response_xml=response_xml,
            sanitized_request_xml=request_xml,
        )

    async def retrieve_benchmark(
        self,
        benchmark_id: str,
        *,
        filters: list[PMBenchmarkFilter] | None = None,
        segment: str | None = None,
    ) -> PMRetrieveBenchmarkResult:
        request_xml = self._build_retrieve_benchmark_request(
            benchmark_id=benchmark_id,
            filters=filters or [],
            segment=segment,
        )
        response_xml = await self._post_soap(request_xml)
        response = _response_element(response_xml, "RetrieveBenchmarkResponse")

        error = None
        database: PMDatabaseInfo | None = None
        response_benchmark_id: str | None = None
        response_segment: str | None = None
        data_records: int | None = None
        numerator_type: str | None = None
        denominator_type: str | None = None
        states: int | None = None
        results: list[PMBenchmarkResult] = []
        if response is not None:
            error = _read_child_text(response, "error")
            database_element = _find_child(response, "database")
            if database_element is not None:
                database = PMDatabaseInfo(
                    database_update_datetime=_read_child_text(database_element, "databaseUpdateDateTime"),
                    database_records=_safe_int(_read_child_text(database_element, "databaseRecords")),
                )
            benchmark_element = _find_child(response, "benchmark")
            if benchmark_element is not None:
                response_benchmark_id = benchmark_element.attrib.get("id")
                response_segment = _read_child_text(benchmark_element, "segment")
            data_element = _find_child(response, "data")
            if data_element is not None:
                data_records = _safe_int(data_element.attrib.get("records"))
                numerator_type = data_element.attrib.get("numeratorType")
                denominator_type = data_element.attrib.get("denominatorType")
                states = _safe_int(data_element.attrib.get("states"))
                for result in _iter_children(data_element, "result"):
                    results.append(
                        PMBenchmarkResult(
                            segment_member=result.attrib.get("segmentMember"),
                            records=_safe_int(result.attrib.get("records")),
                            numerator=_read_child_text(result, "numerator"),
                            denominator=_read_child_text(result, "denominator"),
                        )
                    )

        return PMRetrieveBenchmarkResult(
            status_code=_read_status_attribute(response),
            database=database,
            benchmark_id=response_benchmark_id,
            segment=response_segment,
            data_records=data_records,
            numerator_type=numerator_type,
            denominator_type=denominator_type,
            states=states,
            results=results,
            error=error,
            raw_response_xml=response_xml,
            sanitized_request_xml=request_xml,
        )

    def _build_simple_request(self, request_name: str) -> str:
        envelope = _soap_envelope()
        body = _body_element(envelope)
        ET.SubElement(body, ET.QName(PM_NS, request_name))
        return _xml_to_string(envelope)

    def _build_retrieve_benchmark_request(
        self,
        *,
        benchmark_id: str,
        filters: list[PMBenchmarkFilter],
        segment: str | None,
    ) -> str:
        envelope = _soap_envelope()
        body = _body_element(envelope)
        request = ET.SubElement(body, ET.QName(PM_NS, "RetrieveBenchmarkRequest"))
        benchmark = ET.SubElement(request, ET.QName(PM_NS, "benchmark"))
        benchmark.set("id", benchmark_id)
        for item in filters:
            filter_element = ET.SubElement(benchmark, ET.QName(PM_NS, "filter"))
            if item.parameter:
                filter_element.set("parameter", item.parameter)
            filter_element.text = item.value
        if segment:
            segment_element = ET.SubElement(benchmark, ET.QName(PM_NS, "segment"))
            segment_element.text = segment
        return _xml_to_string(envelope)

    async def _post_soap(self, request_xml: str) -> str:
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '""',
        }
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
            raise PMClientError("Timed out waiting for NEMSIS performance measures response") from exc
        except httpx.HTTPError as exc:
            raise PMClientError(f"NEMSIS performance measures request failed: {exc}") from exc
        return response.text


def _soap_envelope() -> ET.Element:
    ET.register_namespace("soapenv", SOAP_ENV_NS)
    ET.register_namespace("ws", PM_NS)
    return ET.Element(ET.QName(SOAP_ENV_NS, "Envelope"))


def _body_element(envelope: ET.Element) -> ET.Element:
    return ET.SubElement(envelope, ET.QName(SOAP_ENV_NS, "Body"))


def _xml_to_string(element: ET.Element) -> str:
    ET.indent(element, space="  ")
    return ET.tostring(element, encoding="unicode")


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _response_element(xml_text: str, tag_name: str) -> ET.Element | None:
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        return None
    for element in root.iter():
        if _local_name(element.tag) == tag_name:
            return element
    return None


def _find_child(element: ET.Element, tag_name: str) -> ET.Element | None:
    for child in list(element):
        if _local_name(child.tag) == tag_name:
            return child
    return None


def _iter_children(element: ET.Element, tag_name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local_name(child.tag) == tag_name]


def _read_child_text(element: ET.Element, tag_name: str) -> str | None:
    child = _find_child(element, tag_name)
    if child is None:
        return None
    text = (child.text or "").strip()
    return text or None


def _read_status_attribute(element: ET.Element | None) -> int:
    if element is None:
        return -20
    raw = element.attrib.get("status")
    if raw is None:
        return -20
    try:
        return int(raw)
    except ValueError:
        return -20


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
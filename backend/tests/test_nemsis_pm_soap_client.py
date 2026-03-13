from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from core_app.nemsis.pm_soap_client import NEMSISPMSoapClient, PMBenchmarkFilter


@pytest.mark.asyncio
async def test_list_benchmarks_parses_status_and_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NEMSISPMSoapClient(endpoint_url="https://example.test")

    async def _fake_post_soap(request_xml: str) -> str:
        del request_xml
        return (
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">'
            '<SOAP-ENV:Body>'
            '<ns2:ListBenchmarksResponse xmlns:ns2="http://ws.nemsis.org/" status="71">'
            '<ns2:benchmark id="b1" numeratorType="xs:int" denominatorType="xs:int">Cardiac Arrest Survival</ns2:benchmark>'
            '</ns2:ListBenchmarksResponse>'
            '</SOAP-ENV:Body>'
            '</SOAP-ENV:Envelope>'
        )

    monkeypatch.setattr(client, "_post_soap", _fake_post_soap)

    result = await client.list_benchmarks()

    assert result.status_code == 71
    assert len(result.benchmarks) == 1
    assert result.benchmarks[0].id == "b1"
    assert result.benchmarks[0].label == "Cardiac Arrest Survival"


@pytest.mark.asyncio
async def test_list_parameters_parses_values(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NEMSISPMSoapClient(endpoint_url="https://example.test")

    async def _fake_post_soap(request_xml: str) -> str:
        del request_xml
        return (
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">'
            '<SOAP-ENV:Body>'
            '<ns2:ListParametersResponse xmlns:ns2="http://ws.nemsis.org/" status="81">'
            '<ns2:parameter code="state" name="State">'
            '<ns2:value code="FL">Florida</ns2:value>'
            '<ns2:value code="WI">Wisconsin</ns2:value>'
            '</ns2:parameter>'
            '</ns2:ListParametersResponse>'
            '</SOAP-ENV:Body>'
            '</SOAP-ENV:Envelope>'
        )

    monkeypatch.setattr(client, "_post_soap", _fake_post_soap)

    result = await client.list_parameters()

    assert result.status_code == 81
    assert len(result.parameters) == 1
    assert result.parameters[0].code == "state"
    assert [value.code for value in result.parameters[0].values] == ["FL", "WI"]


@pytest.mark.asyncio
async def test_retrieve_benchmark_builds_filters_and_parses_data(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NEMSISPMSoapClient(endpoint_url="https://example.test")

    async def _fake_post_soap(request_xml: str) -> str:
        root = ET.fromstring(request_xml)
        body = list(root)[0]
        request = list(body)[0]
        benchmark = list(request)[0]
        assert benchmark.attrib["id"] == "b1"
        filter_element = next(child for child in list(benchmark) if child.tag.endswith("filter"))
        assert filter_element.attrib["parameter"] == "state"
        assert filter_element.text == "FL"
        segment_element = next(child for child in list(benchmark) if child.tag.endswith("segment"))
        assert segment_element.text == "region"
        return (
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">'
            '<SOAP-ENV:Body>'
            '<ns2:RetrieveBenchmarkResponse xmlns:ns2="http://ws.nemsis.org/" status="91">'
            '<ns2:database><ns2:databaseUpdateDateTime>2026-03-12T12:00:00Z</ns2:databaseUpdateDateTime><ns2:databaseRecords>10</ns2:databaseRecords></ns2:database>'
            '<ns2:benchmark id="b1"><ns2:segment>region</ns2:segment></ns2:benchmark>'
            '<ns2:data records="10" numeratorType="xs:int" denominatorType="xs:int" states="2">'
            '<ns2:result segmentMember="south" records="10"><ns2:numerator>4</ns2:numerator><ns2:denominator>10</ns2:denominator></ns2:result>'
            '</ns2:data>'
            '</ns2:RetrieveBenchmarkResponse>'
            '</SOAP-ENV:Body>'
            '</SOAP-ENV:Envelope>'
        )

    monkeypatch.setattr(client, "_post_soap", _fake_post_soap)

    result = await client.retrieve_benchmark(
        "b1",
        filters=[PMBenchmarkFilter(parameter="state", value="FL")],
        segment="region",
    )

    assert result.status_code == 91
    assert result.database is not None
    assert result.database.database_records == 10
    assert result.results[0].segment_member == "south"
    assert result.results[0].numerator == "4"

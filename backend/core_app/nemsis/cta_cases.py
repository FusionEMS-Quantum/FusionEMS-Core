from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
import xml.etree.ElementTree as ET

NEMSIS_NS = "http://www.nemsis.org"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
CTA_SCHEMA_VERSION = "3.5.1"
CTA_NEMSIS_BUILD_VERSION = "3.5.1.250403CP1"

DatasetType = Literal["DEM", "EMS"]

_VENDOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "compliance"
    / "nemsis"
    / "v3.5.1"
    / "cs"
    / "v3.5.1 C&S for vendors"
)
_STATE_DATASET_XML = _VENDOR_DIR / "2025-STATE-1_v351.xml"
_PRE_BLOCK_RE = re.compile(
    r"ID:\s*(?P<case_id>.+?)\s+Description:\s*(?P<description>.+?)\s+Expected Result:\s*(?P<expected>.+?)\s*</pre>",
    re.DOTALL,
)
_CODE_WITH_LABEL_RE = re.compile(r"^(?P<code>[A-Za-z0-9.]+)\s+-\s+.+$")
_PLACEHOLDER_RE = re.compile(r"\[(Your UUID|Your Timestamp|Value from StateDataSet|Value from DEMDataSet)\]")
_PADDING_RE = re.compile(r"padding-left:\s*([0-9.]+)em")

_NV_LABEL_MAP: dict[str, str] = {
    "Not Applicable": "7701001",
    "Not Recorded": "7701003",
    "Not Reporting": "7701005",
}


@dataclass(frozen=True)
class CTATestCase:
    case_id: str
    short_name: str
    description: str
    dataset_type: DatasetType
    expected_result: str
    schema_version: str
    request_data_schema: int
    html_path: Path
    test_key_element: str


@dataclass(frozen=True)
class CTAXmlArtifact:
    case: CTATestCase
    xml_bytes: bytes
    xml_sha256: str
    unresolved_placeholders: tuple[str, ...]
    warnings: tuple[str, ...]
    resolved_test_key: str | None


@dataclass(frozen=True)
class _VendorRow:
    tag: str
    level: int
    is_group: bool
    value: str | None
    attributes: dict[str, str]


def list_cta_cases() -> list[CTATestCase]:
    cases: list[CTATestCase] = []
    for html_path in sorted(_VENDOR_DIR.glob("2025-*.html")):
        if html_path.name.startswith("2025-STATE-"):
            continue
        text = html_path.read_text(encoding="utf-8")
        metadata = _parse_case_metadata(text)
        dataset_type: DatasetType = "DEM" if "DEM-" in html_path.name else "EMS"
        request_data_schema = 62 if dataset_type == "DEM" else 61
        test_key_element = "dAgency.02" if dataset_type == "DEM" else "eResponse.04"
        short_name = metadata["case_id"].replace("_v351", "")
        cases.append(
            CTATestCase(
                case_id=metadata["case_id"],
                short_name=short_name,
                description=metadata["description"],
                dataset_type=dataset_type,
                expected_result=metadata["expected"],
                schema_version=CTA_SCHEMA_VERSION,
                request_data_schema=request_data_schema,
                html_path=html_path,
                test_key_element=test_key_element,
            )
        )
    return cases


def get_cta_case(case_id: str) -> CTATestCase:
    for case in list_cta_cases():
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)


def generate_cta_case_xml(
    case: CTATestCase,
    *,
    reference_dem_xml: bytes | None = None,
    now: datetime | None = None,
) -> CTAXmlArtifact:
    rows = _parse_vendor_rows(case.html_path)
    state_lookup = _build_lookup_map(_STATE_DATASET_XML.read_bytes())
    dem_lookup = _build_lookup_map(reference_dem_xml) if reference_dem_xml else {}
    current_time = now or datetime.now(UTC)
    unresolved: list[str] = []
    warnings: list[str] = []

    schema_name = "DEMDataSet_v3.xsd" if case.dataset_type == "DEM" else "EMSDataSet_v3.xsd"
    ET.register_namespace("", NEMSIS_NS)
    ET.register_namespace("xsi", XSI_NS)
    root = ET.Element(ET.QName(NEMSIS_NS, f"{case.dataset_type}DataSet"))
    root.set(
        ET.QName(XSI_NS, "schemaLocation"),
        f"{NEMSIS_NS} https://nemsis.org/media/nemsis_v3/{CTA_NEMSIS_BUILD_VERSION}/XSDs/NEMSIS_XSDs/{schema_name}",
    )

    stack: dict[int, ET.Element] = {1: root}
    for row in rows:
        if row.tag == f"{case.dataset_type}DataSet":
            continue

        parent = stack.get(row.level - 1, root)
        element = ET.SubElement(parent, ET.QName(NEMSIS_NS, row.tag))
        for attr_name, attr_value in row.attributes.items():
            resolved_attr = _resolve_value(
                raw_value=attr_value,
                tag=row.tag,
                attr_name=attr_name,
                state_lookup=state_lookup,
                dem_lookup=dem_lookup,
                current_time=current_time,
                unresolved=unresolved,
            )
            if resolved_attr is not None:
                element.set(attr_name, resolved_attr)

        resolved_text = _resolve_value(
            raw_value=row.value,
            tag=row.tag,
            attr_name=None,
            state_lookup=state_lookup,
            dem_lookup=dem_lookup,
            current_time=current_time,
            unresolved=unresolved,
        )
        if resolved_text is not None:
            element.text = resolved_text

        if row.is_group:
            stack = {level: el for level, el in stack.items() if level < row.level}
            stack[row.level] = element

    ET.indent(root, space="  ")
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    resolved_test_key = _find_first_text(xml_bytes, case.test_key_element)
    if not resolved_test_key:
        warnings.append(f"Missing CTA test key element {case.test_key_element}.")

    return CTAXmlArtifact(
        case=case,
        xml_bytes=xml_bytes,
        xml_sha256=hashlib.sha256(xml_bytes).hexdigest(),
        unresolved_placeholders=tuple(unresolved),
        warnings=tuple(warnings),
        resolved_test_key=resolved_test_key,
    )


def extract_xml_lookup(xml_bytes: bytes | None) -> dict[str, list[str]]:
    return _build_lookup_map(xml_bytes)


def _parse_case_metadata(text: str) -> dict[str, str]:
    match = _PRE_BLOCK_RE.search(text)
    if not match:
        raise ValueError("Unable to parse CTA case metadata from vendor file")
    return {
        "case_id": _normalize_ws(match.group("case_id")),
        "description": _normalize_ws(match.group("description")),
        "expected": _normalize_ws(match.group("expected")),
    }


def _parse_vendor_rows(html_path: Path) -> list[_VendorRow]:
    document = ET.fromstring(html_path.read_text(encoding="utf-8"))
    tbody = document.find(".//tbody")
    if tbody is None:
        raise ValueError(f"Unable to find vendor scenario table in {html_path.name}")

    rows: list[_VendorRow] = []
    repeating_row: _VendorRow | None = None
    for tr in tbody.findall("./tr"):
        cells = tr.findall("./td")
        if not cells:
            continue

        first_classes = set((cells[0].get("class") or "").split())
        if "comment" in first_classes:
            continue

        if len(cells) == 1 and repeating_row is not None:
            attrs, value = _split_attrs_and_value(_cell_text(cells[0]))
            rows.append(
                _VendorRow(
                    tag=repeating_row.tag,
                    level=repeating_row.level,
                    is_group=False,
                    value=value,
                    attributes=attrs,
                )
            )
            continue

        if len(cells) < 2:
            continue

        descriptor = cells[0]
        tag = _extract_tag_name(descriptor)
        if not tag:
            continue
        level = _extract_level(descriptor)
        is_group = _is_group_row(descriptor)
        attrs, value = _split_attrs_and_value(_cell_text(cells[1]))
        row = _VendorRow(
            tag=tag,
            level=level,
            is_group=is_group,
            value=value,
            attributes=attrs,
        )
        rows.append(row)
        repeating_row = None if is_group else row

    return rows


def _extract_tag_name(cell: ET.Element) -> str:
    span = cell.find(".//span")
    if span is None:
        return ""
    raw_text = _normalize_ws("".join(span.itertext()))
    if "-" in raw_text:
        raw_text = raw_text.split("-", 1)[0]
    return raw_text.strip()


def _extract_level(cell: ET.Element) -> int:
    style = cell.get("style") or ""
    match = _PADDING_RE.search(style)
    if not match:
        return 1
    return int(round(float(match.group(1))))


def _is_group_row(cell: ET.Element) -> bool:
    span = cell.find(".//span")
    if span is None:
        return False
    classes = set((span.get("class") or "").split())
    return "group" in classes


def _cell_text(cell: ET.Element) -> str:
    pieces = [part for part in cell.itertext()]
    return _normalize_ws(" ".join(pieces))


def _split_attrs_and_value(raw_text: str) -> tuple[dict[str, str], str | None]:
    attrs: dict[str, str] = {}
    remainder = raw_text.strip()
    while remainder.startswith("["):
        segment, remainder = _consume_bracket_segment(remainder)
        inner = segment[1:-1]
        if "=" not in inner:
            break
        key, value = inner.split("=", 1)
        attrs[_normalize_ws(key)] = _normalize_ws(value).strip('"')
        remainder = remainder.lstrip()

    normalized_remainder = _normalize_ws(remainder)
    return attrs, normalized_remainder or None


def _consume_bracket_segment(text: str) -> tuple[str, str]:
    depth = 0
    for index, char in enumerate(text):
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[: index + 1], text[index + 1 :]
    return text, ""


def _resolve_value(
    *,
    raw_value: str | None,
    tag: str,
    attr_name: str | None,
    state_lookup: dict[str, list[str]],
    dem_lookup: dict[str, list[str]],
    current_time: datetime,
    unresolved: list[str],
) -> str | None:
    if raw_value is None:
        return None

    value = raw_value.strip()
    if not value:
        return None

    value = value.replace("[Your UUID]", str(uuid.uuid4()))
    value = value.replace("[Your Timestamp]", current_time.isoformat())
    if "[Value from StateDataSet]" in value:
        replacement = _lookup_placeholder_value(state_lookup, tag, attr_name)
        if replacement:
            value = value.replace("[Value from StateDataSet]", replacement)
        else:
            unresolved.append(f"{tag}:state_dataset")
    if "[Value from DEMDataSet]" in value:
        replacement = _lookup_placeholder_value(dem_lookup, tag, attr_name)
        if replacement:
            value = value.replace("[Value from DEMDataSet]", replacement)
        else:
            unresolved.append(f"{tag}:dem_dataset")

    value = _normalize_ws(value)
    if _PLACEHOLDER_RE.search(value):
        unresolved.append(f"{tag}:{attr_name or 'text'}")
        return value

    if attr_name == "NV":
        return _NV_LABEL_MAP.get(value, value)

    code_match = _CODE_WITH_LABEL_RE.match(value)
    if code_match and any(char.isdigit() for char in code_match.group("code")):
        return code_match.group("code")

    return value or None


def _build_lookup_map(xml_bytes: bytes | None) -> dict[str, list[str]]:
    if not xml_bytes:
        return {}
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return {}

    lookup: dict[str, list[str]] = {}
    for element in root.iter():
        local_name = _local_name(element.tag)
        text = _normalize_ws(element.text or "")
        if not text:
            text = ""
        if text:
            lookup.setdefault(local_name, []).append(text)
        for attr_name, attr_value in element.attrib.items():
            attr_local_name = _local_name(attr_name)
            normalized_attr_value = _normalize_ws(attr_value)
            if not normalized_attr_value:
                continue
            lookup.setdefault(attr_local_name, []).append(normalized_attr_value)
            lookup.setdefault(f"{local_name}@{attr_local_name}", []).append(normalized_attr_value)
    return lookup


def _lookup_first(lookup: dict[str, list[str]], tag: str) -> str | None:
    values = lookup.get(tag)
    if values:
        return values[0]
    return None


def _lookup_placeholder_value(
    lookup: dict[str, list[str]],
    tag: str,
    attr_name: str | None,
) -> str | None:
    candidate_keys: list[str] = []
    if attr_name:
        candidate_keys.append(f"{tag}@{attr_name}")
    candidate_keys.append(tag)
    if tag and tag[0] in {"d", "e"}:
        state_variant = f"s{tag[1:]}"
        if attr_name:
            candidate_keys.append(f"{state_variant}@{attr_name}")
        candidate_keys.append(state_variant)
    if attr_name:
        candidate_keys.append(attr_name)

    for candidate in candidate_keys:
        values = lookup.get(candidate)
        if values:
            return values[0]
    return None


def _find_first_text(xml_bytes: bytes, tag: str) -> str | None:
    lookup = _build_lookup_map(xml_bytes)
    values = lookup.get(tag)
    return values[0] if values else None


def _normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _local_name(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag
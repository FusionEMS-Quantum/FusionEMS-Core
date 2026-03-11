from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core_app.epcr.completeness_engine import ELEMENT_FIELD_MAP
from core_app.epcr.nemsis_exporter import NEMSIS_VERSION

logger = logging.getLogger(__name__)

_CLINICAL_TABLES_BASE = "https://clinicaltables.nlm.nih.gov/api"
_SNOWSTORM_BASE = "https://snowstorm.ihtsdotools.org/snowstorm"
_NPPI_REGISTRY_BASE = "https://npiregistry.cms.hhs.gov/api/"
_DEFAULT_TIMEOUT_SECONDS = 8


class OpenDataUnavailable(RuntimeError):
    """Raised when an upstream open-data provider is unavailable."""


def _http_json(url: str, *, timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "FusionEMS-Core/clinical-open-data",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 429:
            raise OpenDataUnavailable("upstream_rate_limited") from exc
        raise OpenDataUnavailable(f"upstream_http_error_{exc.code}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise OpenDataUnavailable("upstream_unavailable") from exc


def _normalize_query(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_clinicaltables_response(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, list) or len(payload) < 4:
        return []

    raw_codes = payload[1] if isinstance(payload[1], list) else []
    raw_rows = payload[3] if isinstance(payload[3], list) else []

    rows: list[dict[str, str]] = []
    for idx, raw_row in enumerate(raw_rows):
        code = ""
        display = ""

        if isinstance(raw_row, list):
            if len(raw_row) >= 1 and isinstance(raw_row[0], str):
                code = raw_row[0].strip()
            if len(raw_row) >= 2 and isinstance(raw_row[1], str):
                display = raw_row[1].strip()
            elif len(raw_row) >= 1 and isinstance(raw_row[0], str):
                display = raw_row[0].strip()

        if not code and idx < len(raw_codes) and isinstance(raw_codes[idx], str):
            code = raw_codes[idx].strip()

        if not display and idx < len(raw_codes) and isinstance(raw_codes[idx], str):
            display = raw_codes[idx].strip()

        if code or display:
            rows.append({"code": code, "display": display})

    return rows


def search_icd10_open(*, query: str, limit: int = 25) -> list[dict[str, str]]:
    normalized = _normalize_query(query)
    if not normalized:
        return []

    params = urlencode({"terms": normalized, "maxList": str(max(1, min(limit, 100))), "sf": "code,name"})
    payload = _http_json(f"{_CLINICAL_TABLES_BASE}/icd10cm/v3/search?{params}")
    rows = _parse_clinicaltables_response(payload)
    return [{"code": row["code"], "display": row["display"], "source": "clinicaltables.icd10cm"} for row in rows]


def search_rxnorm_open(*, query: str, limit: int = 25) -> list[dict[str, str]]:
    normalized = _normalize_query(query)
    if not normalized:
        return []

    params = urlencode({"terms": normalized, "maxList": str(max(1, min(limit, 100)))})
    payload = _http_json(f"{_CLINICAL_TABLES_BASE}/rxterms/v3/search?{params}")
    rows = _parse_clinicaltables_response(payload)
    return [{"code": row["code"], "display": row["display"], "source": "clinicaltables.rxterms"} for row in rows]


def _search_snomed_snowstorm(*, query: str, limit: int) -> list[dict[str, str]]:
    params = urlencode(
        {
            "term": query,
            "activeFilter": "true",
            "offset": "0",
            "limit": str(max(1, min(limit, 100))),
        }
    )
    payload = _http_json(
        f"{_SNOWSTORM_BASE}/snomed-ct/browser/MAIN/concepts?{params}",
        timeout_seconds=10,
    )

    items = payload.get("items", []) if isinstance(payload, dict) else []
    rows: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        concept_id = str(item.get("conceptId") or "").strip()
        preferred_term = ""
        pt = item.get("pt")
        if isinstance(pt, dict):
            preferred_term = str(pt.get("term") or "").strip()
        if not preferred_term:
            fsn = item.get("fsn")
            if isinstance(fsn, dict):
                preferred_term = str(fsn.get("term") or "").strip()

        if concept_id or preferred_term:
            rows.append(
                {
                    "code": concept_id,
                    "display": preferred_term,
                    "source": "snowstorm.snomed",
                }
            )

    return rows


def _search_snomed_fallback(*, query: str, limit: int) -> list[dict[str, str]]:
    params = urlencode({"terms": query, "maxList": str(max(1, min(limit, 100)))})
    payload = _http_json(f"{_CLINICAL_TABLES_BASE}/conditions/v3/search?{params}")
    rows = _parse_clinicaltables_response(payload)
    return [{"code": row["code"], "display": row["display"], "source": "clinicaltables.conditions"} for row in rows]


def search_snomed_open(*, query: str, limit: int = 25) -> list[dict[str, str]]:
    normalized = _normalize_query(query)
    if not normalized:
        return []

    try:
        return _search_snomed_snowstorm(query=normalized, limit=limit)
    except OpenDataUnavailable as exc:
        logger.warning("snomed_snowstorm_unavailable reason=%s", exc)
        return _search_snomed_fallback(query=normalized, limit=limit)


def search_npi_open(*, query: str, limit: int = 10) -> list[dict[str, str]]:
    normalized = _normalize_query(query)
    if not normalized:
        return []

    safe_limit = max(1, min(limit, 50))
    results: list[dict[str, str]] = []

    for dataset in ("npi_idv", "npi_org"):
        params = urlencode({"terms": normalized, "maxList": str(safe_limit)})
        payload = _http_json(f"{_CLINICAL_TABLES_BASE}/{dataset}/v3/search?{params}")
        rows = _parse_clinicaltables_response(payload)
        for row in rows:
            results.append(
                {
                    "npi": row["code"],
                    "display": row["display"],
                    "source": f"clinicaltables.{dataset}",
                }
            )

    unique: dict[str, dict[str, str]] = {}
    for row in results:
        key = row.get("npi") or row.get("display")
        if key and key not in unique:
            unique[key] = row

    return list(unique.values())[:safe_limit]


def verify_npi_open(*, npi_number: str) -> dict[str, Any]:
    npi = "".join(ch for ch in npi_number if ch.isdigit())
    if len(npi) != 10:
        return {
            "npi_number": npi,
            "valid": False,
            "status": "invalid_format",
            "reason": "npi_must_be_10_digits",
            "source": "nppes.cms",
        }

    query = urlencode({"number": npi, "version": "2.1", "limit": 1})
    payload = _http_json(f"{_NPPI_REGISTRY_BASE}?{query}", timeout_seconds=10)
    rows = payload.get("results", []) if isinstance(payload, dict) else []
    if not rows:
        return {
            "npi_number": npi,
            "valid": False,
            "status": "not_found",
            "source": "nppes.cms",
        }

    item = rows[0]
    basic = item.get("basic", {}) if isinstance(item, dict) else {}
    addresses = item.get("addresses", []) if isinstance(item, dict) else []
    taxonomies = item.get("taxonomies", []) if isinstance(item, dict) else []

    location = next(
        (
            address
            for address in addresses
            if isinstance(address, dict) and address.get("address_purpose") == "LOCATION"
        ),
        addresses[0] if addresses and isinstance(addresses[0], dict) else {},
    )
    primary_taxonomy = next(
        (
            taxonomy
            for taxonomy in taxonomies
            if isinstance(taxonomy, dict) and taxonomy.get("primary") is True
        ),
        taxonomies[0] if taxonomies and isinstance(taxonomies[0], dict) else {},
    )

    organization_name = ""
    if isinstance(basic, dict):
        organization_name = str(
            basic.get("organization_name") or basic.get("name") or ""
        ).strip()

    return {
        "npi_number": npi,
        "valid": True,
        "status": "verified",
        "source": "nppes.cms",
        "organization_name": organization_name,
        "state": str(location.get("state") or "").strip() if isinstance(location, dict) else "",
        "city": str(location.get("city") or "").strip() if isinstance(location, dict) else "",
        "taxonomy_code": str(primary_taxonomy.get("code") or "").strip()
        if isinstance(primary_taxonomy, dict)
        else "",
        "taxonomy_desc": str(primary_taxonomy.get("desc") or "").strip()
        if isinstance(primary_taxonomy, dict)
        else "",
    }


def _table_exists(db: Session, table_name: str) -> bool:
    row = db.execute(
        text("SELECT to_regclass(:table_name)"),
        {"table_name": f"public.{table_name}"},
    ).fetchone()
    return bool(row and row[0])


def _safe_scalar_int(db: Session, sql: str, params: dict[str, Any] | None = None) -> int:
    try:
        value = db.execute(text(sql), params or {}).scalar()
        return int(value or 0)
    except (SQLAlchemyError, TypeError, ValueError):
        return 0


def build_dataset_status(db: Session, *, probe_external: bool = False) -> dict[str, Any]:
    icd_term_count = 0
    icd_latest_year = "unknown"
    if _table_exists(db, "icd10_codes"):
        icd_term_count = _safe_scalar_int(db, "SELECT count(*) FROM icd10_codes")
        latest_year = db.execute(text("SELECT max(version_year) FROM icd10_codes")).scalar()
        if latest_year:
            icd_latest_year = str(latest_year)

    facilities_count = 0
    if _table_exists(db, "facilities"):
        facilities_count = _safe_scalar_int(db, "SELECT count(*) FROM facilities WHERE deleted_at IS NULL")

    rxnorm_status = "not_probed"
    snomed_status = "not_probed"
    npi_status = "not_probed"

    if probe_external:
        try:
            rxnorm_status = "active" if search_rxnorm_open(query="metformin", limit=1) else "degraded"
        except OpenDataUnavailable:
            rxnorm_status = "degraded"

        try:
            snomed_status = "active" if search_snomed_open(query="asthma", limit=1) else "degraded"
        except OpenDataUnavailable:
            snomed_status = "degraded"

        try:
            npi_probe = search_npi_open(query="mayo", limit=1)
            npi_status = "active" if len(npi_probe) > 0 else "degraded"
        except OpenDataUnavailable:
            npi_status = "degraded"

    return {
        "nemsis": {
            "version": NEMSIS_VERSION,
            "last_update": datetime.now(UTC).date().isoformat(),
            "schematron_active": True,
            "element_count": len(ELEMENT_FIELD_MAP),
            "source": "internal.nemsis.dataset",
        },
        "neris": {
            "version": "1.0",
            "last_update": datetime.now(UTC).date().isoformat(),
            "schematron_active": True,
            "source": "internal.neris.dataset",
        },
        "rxnorm": {
            "version": "live",
            "last_update": datetime.now(UTC).date().isoformat(),
            "term_count": 0,
            "source": "clinicaltables.rxterms",
            "status": rxnorm_status,
        },
        "snomed": {
            "version": "live",
            "last_update": datetime.now(UTC).date().isoformat(),
            "term_count": 0,
            "source": "snowstorm.snomed",
            "status": snomed_status,
        },
        "icd10": {
            "version": icd_latest_year,
            "last_update": datetime.now(UTC).date().isoformat(),
            "term_count": icd_term_count,
            "source": "clinicaltables.icd10cm+local_db",
        },
        "npi": {
            "source": "nppes.cms+clinicaltables",
            "status": npi_status,
            "verification_supported": True,
        },
        "facilities": {
            "active_count": facilities_count,
            "last_state_sync": datetime.now(UTC).date().isoformat(),
        },
    }


def founder_clinical_snapshot(db: Session) -> dict[str, Any]:
    status = build_dataset_status(db, probe_external=False)
    return {
        "icd10": {
            "version": status["icd10"]["version"],
            "term_count": status["icd10"]["term_count"],
        },
        "rxnorm": {
            "status": status["rxnorm"]["status"],
            "source": status["rxnorm"]["source"],
        },
        "snomed": {
            "status": status["snomed"]["status"],
            "source": status["snomed"]["source"],
        },
        "nemsis": {
            "version": status["nemsis"]["version"],
            "element_count": status["nemsis"]["element_count"],
        },
        "npi": {
            "verification_supported": True,
            "source": status["npi"]["source"],
        },
    }

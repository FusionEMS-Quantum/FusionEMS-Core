from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://clinicaltables.nlm.nih.gov/api"


class NihClinicalTablesError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class NihClinicalTablesResult:
    code: str
    display: str
    extra: dict[str, Any]


class NihClinicalTablesClient:
    """NIH/NLM Clinical Tables API client (no-cost public lookup).

    This is used for low-cost external lookups (autocomplete, fallback search)
    when a tenant has not ingested a local dataset copy.
    """

    def __init__(self, *, timeout_s: float = 6.0) -> None:
        self._timeout_s = timeout_s

    async def search(
        self,
        *,
        table: str,
        terms: str,
        limit: int = 25,
    ) -> list[NihClinicalTablesResult]:
        t = (terms or "").strip()
        if not t:
            return []

        url = f"{_BASE}/{table}/v3/search"
        params = {
            "terms": t,
            "maxList": str(int(limit)),
        }

        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            resp = await client.get(url, params=params)

        if resp.status_code >= 400:
            raise NihClinicalTablesError(
                f"ClinicalTables API error {resp.status_code}: {resp.text[:200]}"
            )

        # Expected response shape: [totalCount, [codes], [displays], ...]
        try:
            payload = resp.json()
        except Exception as exc:
            raise NihClinicalTablesError("ClinicalTables response was not JSON") from exc

        if not isinstance(payload, list) or len(payload) < 3:
            raise NihClinicalTablesError("ClinicalTables response shape unexpected")

        codes = payload[1] if isinstance(payload[1], list) else []
        displays = payload[2] if isinstance(payload[2], list) else []

        results: list[NihClinicalTablesResult] = []
        for idx in range(min(len(codes), len(displays))):
            code = str(codes[idx])
            display = str(displays[idx])
            results.append(NihClinicalTablesResult(code=code, display=display, extra={"table": table}))

        logger.info(
            "nih_clinical_tables_search table=%s terms_len=%d results=%d",
            table,
            len(t),
            len(results),
        )
        return results

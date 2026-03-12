from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://npiregistry.cms.hhs.gov/api"


class NpiRegistryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class NpiRegistryResult:
    npi: str
    name: str
    enumeration_type: str | None
    extra: dict[str, Any]


class NpiRegistryClient:
    """NPI Registry public API client (CMS)."""

    def __init__(self, *, timeout_s: float = 6.0) -> None:
        self._timeout_s = timeout_s

    async def search(
        self,
        *,
        number: str | None = None,
        organization_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        city: str | None = None,
        state: str | None = None,
        limit: int = 25,
    ) -> list[NpiRegistryResult]:
        params: dict[str, str] = {"version": "2.1"}
        if number:
            params["number"] = number.strip()
        if organization_name:
            params["organization_name"] = organization_name.strip()
        if first_name:
            params["first_name"] = first_name.strip()
        if last_name:
            params["last_name"] = last_name.strip()
        if city:
            params["city"] = city.strip()
        if state:
            params["state"] = state.strip().upper()
        if not any(k in params for k in ("number", "organization_name", "first_name", "last_name")):
            return []

        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            resp = await client.get(_BASE, params=params)

        if resp.status_code >= 400:
            raise NpiRegistryError(
                f"NPI registry error {resp.status_code}: {resp.text[:200]}"
            )

        try:
            payload = resp.json()
        except Exception as exc:
            raise NpiRegistryError("NPI registry response was not JSON") from exc

        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            return []

        out: list[NpiRegistryResult] = []
        for r in results[: int(limit)]:
            if not isinstance(r, dict):
                continue
            npi = str(r.get("number") or "").strip()
            if not npi:
                continue
            basic = r.get("basic") if isinstance(r.get("basic"), dict) else {}
            enumeration_type = r.get("enumeration_type")

            name = ""
            if isinstance(basic, dict):
                org = basic.get("organization_name")
                if org:
                    name = str(org)
                else:
                    first = str(basic.get("first_name") or "").strip()
                    last = str(basic.get("last_name") or "").strip()
                    if first or last:
                        name = (first + " " + last).strip()

            out.append(
                NpiRegistryResult(
                    npi=npi,
                    name=name or npi,
                    enumeration_type=str(enumeration_type) if enumeration_type else None,
                    extra={
                        "raw": r,
                    },
                )
            )

        logger.info("npi_registry_search results=%d", len(out))
        return out

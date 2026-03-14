from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://rxnav.nlm.nih.gov/REST"


class RxNavError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RxNavApproximateMatch:
    rxcui: str
    score: int
    name: str | None
    extra: dict[str, Any]


class RxNavClient:
    """RxNav public API client for RxNorm normalization and lookups."""

    def __init__(self, *, timeout_s: float = 6.0) -> None:
        self._timeout_s = timeout_s

    async def approximate_term(
        self,
        *,
        term: str,
        limit: int = 25,
        max_entries: int = 1,
    ) -> list[RxNavApproximateMatch]:
        t = (term or "").strip()
        if not t:
            return []

        url = f"{_BASE}/approximateTerm.json"
        params = {
            "term": t,
            "maxEntries": str(int(max_entries)),
            "option": "1",
        }

        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            resp = await client.get(url, params=params)

        if resp.status_code >= 400:
            raise RxNavError(f"RxNav error {resp.status_code}: {resp.text[:200]}")

        try:
            payload = resp.json()
        except Exception as exc:
            raise RxNavError("RxNav response was not JSON") from exc

        matches = (
            payload.get("approximateGroup", {})
            .get("candidate", [])
            if isinstance(payload, dict)
            else []
        )

        out: list[RxNavApproximateMatch] = []
        if not isinstance(matches, list):
            return []

        for m in matches[: int(limit)]:
            if not isinstance(m, dict):
                continue
            rxcui = str(m.get("rxcui") or "").strip()
            if not rxcui:
                continue
            score_raw = m.get("score")
            try:
                score = int(score_raw)
            except Exception:
                score = 0
            out.append(
                RxNavApproximateMatch(
                    rxcui=rxcui,
                    score=score,
                    name=None,
                    extra={"term": t},
                )
            )

        logger.info("rxnav_approximate_term term_len=%d results=%d", len(t), len(out))
        return out

    async def rxcui_to_name(self, *, rxcui: str) -> str | None:
        r = (rxcui or "").strip()
        if not r:
            return None

        url = f"{_BASE}/rxcui/{r}/properties.json"
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            resp = await client.get(url)

        if resp.status_code >= 400:
            raise RxNavError(f"RxNav error {resp.status_code}: {resp.text[:200]}")

        try:
            payload = resp.json()
        except Exception as exc:
            raise RxNavError("RxNav response was not JSON") from exc

        props = payload.get("properties") if isinstance(payload, dict) else None
        if not isinstance(props, dict):
            return None
        name = props.get("name")
        return str(name) if name is not None else None

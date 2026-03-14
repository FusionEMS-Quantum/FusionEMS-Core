from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_UMLS_SEARCH_URL = "https://uts-ws.nlm.nih.gov/rest/search/current"


@dataclass(frozen=True, slots=True)
class UmlsUtsResult:
    """A single concept result from the UMLS UTS search API."""

    ui: str
    name: str
    root_source: str
    uri: str


class UmlsUtsClient:
    """Async client for the NLM UMLS Unified Terminology Services REST API.

    Reference: https://documentation.uts.nlm.nih.gov/rest/search/
    """

    def __init__(self, *, api_key: str, timeout_s: float = 6.0) -> None:
        if not api_key:
            raise ValueError("UmlsUtsClient requires a non-empty api_key")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_s)

    async def search_current(
        self,
        *,
        q: str,
        limit: int = 25,
    ) -> list[UmlsUtsResult]:
        """Search the UMLS Metathesaurus current release.

        Args:
            q: Search string (concept name, code, etc.).
            limit: Maximum number of results to return (1–100).

        Returns:
            List of UmlsUtsResult objects. Empty list when no matches found.

        Raises:
            httpx.HTTPStatusError: on non-2xx responses from NLM.
            httpx.TimeoutException: when the request exceeds timeout_s.
        """
        params: dict[str, str | int] = {
            "string": q,
            "apiKey": self._api_key,
            "returnIdType": "concept",
            "pageNumber": 1,
            "pageSize": limit,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(_UMLS_SEARCH_URL, params=params)
            resp.raise_for_status()

        payload: dict = resp.json()
        raw_results: list[dict] = (
            payload.get("result", {}).get("results", [])
        )
        return [
            UmlsUtsResult(
                ui=r.get("ui", ""),
                name=r.get("name", ""),
                root_source=r.get("rootSource", ""),
                uri=r.get("uri", ""),
            )
            for r in raw_results
            # NLM returns a sentinel "NONE" ui when no match exists
            if r.get("ui") and r["ui"] != "NONE"
        ]

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from scripts.run_nemsis_cta_case import (
    _load_env_file,
    _tenant_default,
    _trim_result_for_output,
    _user_default,
    _wait_for_terminal_status,
)


class _FakeService:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = responses
        self.calls = 0

    async def check_status(self, **kwargs: Any) -> dict[str, Any]:
        del kwargs
        response = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        return response


async def _no_sleep(_: float) -> None:
    return None


def test_trim_result_for_output_keeps_validation_and_strips_large_blobs() -> None:
    result = {
        "status": "submitted",
        "details": {
            "validation": {"valid": True},
            "warnings": [],
            "xml_b64": "YWJj",
            "submit_request_xml": "<submit />",
            "retrieve_response_xml": "<retrieve />",
        },
    }

    trimmed = _trim_result_for_output(result, include_details=False)

    assert trimmed["details"]["validation"] == {"valid": True}
    assert "xml_b64" not in trimmed["details"]
    assert "submit_request_xml" not in trimmed["details"]
    assert "retrieve_response_xml" not in trimmed["details"]


@pytest.mark.asyncio
async def test_wait_for_terminal_status_stops_on_first_terminal_result() -> None:
    service = _FakeService(
        [
            {"status": "pending", "id": "run-1"},
            {"status": "submitted", "id": "run-1"},
            {"status": "passed", "id": "run-1", "plain_summary": "Passed"},
        ]
    )

    result = await _wait_for_terminal_status(
        service=service,  # type: ignore[arg-type]
        run_id="run-1",
        payload={},
        current=SimpleNamespace(),
        correlation_id=None,
        poll_interval_seconds=0.0,
        max_polls=5,
        initial_result={"status": "submitted", "id": "run-1"},
        sleep_func=_no_sleep,
    )

    assert result["status"] == "passed"
    assert service.calls == 3


def test_load_env_file_populates_actor_defaults(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "FUSIONEMS_TENANT_ID=00000000-0000-0000-0000-000000000000\n"
        "FUSIONEMS_USER_ID=00000000-0000-0000-0000-000000000000\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("FUSIONEMS_TENANT_ID", raising=False)
    monkeypatch.delenv("FUSIONEMS_USER_ID", raising=False)

    _load_env_file(env_path)

    assert _tenant_default() == "00000000-0000-0000-0000-000000000000"
    assert _user_default() == "00000000-0000-0000-0000-000000000000"
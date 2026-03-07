"""Tests for platform health probes and scoring logic."""
from __future__ import annotations

from core_app.api.platform_health_router import (
    _compute_score,
    _overall_status,
    _probe_api,
)


class TestComputeScore:
    def test_all_green_returns_100(self) -> None:
        services = [
            {"name": "A", "status": "GREEN"},
            {"name": "B", "status": "GREEN"},
            {"name": "C", "status": "GREEN"},
        ]
        assert _compute_score(services) == 100

    def test_one_red_reduces_score(self) -> None:
        services = [
            {"name": "A", "status": "GREEN"},
            {"name": "B", "status": "RED"},
            {"name": "C", "status": "GREEN"},
        ]
        score = _compute_score(services)
        assert score == 66  # 2/3 ≈ 66%

    def test_all_red_returns_zero(self) -> None:
        services = [
            {"name": "A", "status": "RED"},
            {"name": "B", "status": "RED"},
        ]
        assert _compute_score(services) == 0

    def test_empty_services_returns_zero(self) -> None:
        assert _compute_score([]) == 0

    def test_gray_not_counted_as_green(self) -> None:
        services = [
            {"name": "A", "status": "GREEN"},
            {"name": "B", "status": "GRAY"},
        ]
        assert _compute_score(services) == 50


class TestOverallStatus:
    def test_score_90_is_green(self) -> None:
        assert _overall_status(90) == "GREEN"
        assert _overall_status(100) == "GREEN"

    def test_score_60_is_yellow(self) -> None:
        assert _overall_status(60) == "YELLOW"
        assert _overall_status(89) == "YELLOW"

    def test_score_below_60_is_red(self) -> None:
        assert _overall_status(59) == "RED"
        assert _overall_status(0) == "RED"


class TestProbeApi:
    def test_self_probe_always_green(self) -> None:
        result = _probe_api()
        assert result["name"] == "FastAPI Core"
        assert result["status"] == "GREEN"
        assert result["latency_ms"] == 0

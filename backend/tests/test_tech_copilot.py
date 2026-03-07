"""Tests for the Tech Copilot heuristic analysis fallback."""
from core_app.api.tech_copilot_router import _heuristic_analysis


def test_heuristic_empty_data() -> None:
    result = _heuristic_analysis(None)
    assert result["severity"] == "MEDIUM"
    assert result["human_review"] == "RECOMMENDED"


def test_heuristic_all_green() -> None:
    data = {
        "score": 100,
        "services": [
            {"name": "FastAPI", "status": "GREEN", "latency_ms": 10},
            {"name": "PostgreSQL", "status": "GREEN", "latency_ms": 5},
        ],
    }
    result = _heuristic_analysis(data)
    assert result["severity"] == "GREEN"
    assert result["issue"] == "All Systems Nominal"


def test_heuristic_red_service() -> None:
    data = {
        "score": 50,
        "services": [
            {"name": "PostgreSQL", "status": "RED", "latency_ms": 999},
            {"name": "FastAPI", "status": "GREEN", "latency_ms": 10},
        ],
    }
    result = _heuristic_analysis(data)
    assert result["severity"] == "CRITICAL"
    assert "PostgreSQL" in result["issue"]
    assert result["human_review"] == "REQUIRED"


def test_heuristic_high_latency() -> None:
    data = {
        "score": 80,
        "services": [
            {"name": "Redis", "status": "GREEN", "latency_ms": 750},
        ],
    }
    result = _heuristic_analysis(data)
    assert result["severity"] == "HIGH"
    assert "Latency" in result["issue"]


def test_heuristic_low_score() -> None:
    data = {
        "score": 50,
        "services": [
            {"name": "API", "status": "GRAY", "latency_ms": 10},
        ],
    }
    result = _heuristic_analysis(data)
    assert result["severity"] == "MEDIUM"
    assert "Degraded" in result["issue"]

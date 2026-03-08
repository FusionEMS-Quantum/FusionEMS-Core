"""Tests for the Compliance Command Center router.

Tests the pure domain-scoring helper functions and response model construction
without requiring a database connection.
"""
from __future__ import annotations

from datetime import UTC, datetime

from core_app.api.compliance_command_router import (
    ComplianceCommandSummary,
    DomainKey,
    DomainScore,
    _build_action_queue,
    _build_priority_alerts,
    _clamp,
    _parse_iso,
    _risk_tier,
)


DOMAINS: tuple[DomainKey, ...] = (
    "nemsis",
    "hipaa",
    "pcr",
    "billing",
    "accreditation",
    "dea",
    "cms",
)


# ─── Utility tests ────────────────────────────────────────────────────────

def test_clamp_bounds() -> None:
    assert _clamp(-10) == 0
    assert _clamp(0) == 0
    assert _clamp(50) == 50
    assert _clamp(100) == 100
    assert _clamp(150) == 100


def test_risk_tier_thresholds() -> None:
    assert _risk_tier(90) == "low"
    assert _risk_tier(80) == "low"
    assert _risk_tier(79) == "medium"
    assert _risk_tier(60) == "medium"
    assert _risk_tier(59) == "high"
    assert _risk_tier(0) == "high"


def test_parse_iso_valid() -> None:
    ts = _parse_iso("2026-03-08T12:00:00+00:00")
    assert ts is not None
    assert ts.year == 2026


def test_parse_iso_with_z_suffix() -> None:
    ts = _parse_iso("2026-03-08T12:00:00Z")
    assert ts is not None


def test_parse_iso_invalid() -> None:
    assert _parse_iso("not-a-date") is None
    assert _parse_iso("") is None
    assert _parse_iso(None) is None
    assert _parse_iso(12345) is None


# ─── Priority Alert Builder ──────────────────────────────────────────────

def test_priority_alerts_critical_domain() -> None:
    domains = [
        DomainScore(
            domain="dea",
            score=40,
            passing=1,
            warning=0,
            critical=3,
            trend="down",
            suggested_actions=["Resolve 3 hard blocks."],
        ),
    ]
    alerts = _build_priority_alerts(domains)
    assert len(alerts) == 1
    assert alerts[0].severity == "critical"
    assert alerts[0].domain == "dea"
    assert "Critical Deficiency" in alerts[0].title


def test_priority_alerts_warning_domain() -> None:
    domains = [
        DomainScore(
            domain="billing",
            score=65,
            passing=10,
            warning=1,
            critical=0,
            trend="stable",
            suggested_actions=["Review pending claims."],
        ),
    ]
    alerts = _build_priority_alerts(domains)
    assert len(alerts) == 1
    assert alerts[0].severity == "warning"
    assert alerts[0].domain == "billing"


def test_priority_alerts_healthy_domain_no_alert() -> None:
    domains = [
        DomainScore(
            domain="hipaa",
            score=92,
            passing=20,
            warning=0,
            critical=0,
            trend="stable",
        ),
    ]
    alerts = _build_priority_alerts(domains)
    assert len(alerts) == 0


def test_priority_alerts_sorted_critical_first() -> None:
    domains = [
        DomainScore(
            domain="billing",
            score=65,
            passing=5,
            warning=3,
            critical=0,
            suggested_actions=["Review claims."],
        ),
        DomainScore(
            domain="dea",
            score=30,
            passing=0,
            warning=0,
            critical=5,
            suggested_actions=["Resolve blocks."],
        ),
    ]
    alerts = _build_priority_alerts(domains)
    assert len(alerts) == 2
    assert alerts[0].severity == "critical"
    assert alerts[0].domain == "dea"
    assert alerts[1].severity == "warning"


def test_priority_alerts_capped_at_8() -> None:
    domains = [
        DomainScore(
            domain=d,
            score=30,
            critical=5,
            suggested_actions=["Fix."],
        )
        for d in DOMAINS
    ]
    domains.extend([
        DomainScore(domain="nemsis", score=30, critical=5, suggested_actions=["Fix again."]),
        DomainScore(domain="hipaa", score=30, critical=5, suggested_actions=["Fix again."]),
    ])
    alerts = _build_priority_alerts(domains)
    assert len(alerts) <= 8


# ─── Action Queue Builder ────────────────────────────────────────────────

def test_action_queue_from_domains() -> None:
    domains = [
        DomainScore(
            domain="cms",
            score=55,
            passing=3,
            warning=2,
            critical=4,
            suggested_actions=["Fix PCS.", "Review BS flags."],
        ),
        DomainScore(
            domain="nemsis",
            score=85,
            passing=10,
            warning=1,
            critical=0,
            suggested_actions=["Address warnings."],
        ),
    ]
    queue = _build_action_queue(domains)
    assert len(queue) >= 2
    # Lowest score domain should come first
    assert queue[0].domain == "cms"
    assert "Fix PCS" in queue[0].title


def test_action_queue_urgency_based_on_score() -> None:
    domains = [
        DomainScore(
            domain="dea",
            score=40,
            critical=3,
            suggested_actions=["Resolve blocks."],
        ),
    ]
    queue = _build_action_queue(domains)
    assert len(queue) >= 1
    assert queue[0].action_state == "blocking"
    assert queue[0].impact == "High"


def test_action_queue_capped_at_12() -> None:
    domains = [
        DomainScore(
            domain=d,
            score=30,
            critical=5,
            suggested_actions=["Fix A.", "Fix B.", "Fix C."],
        )
        for d in DOMAINS
    ]
    queue = _build_action_queue(domains)
    assert len(queue) <= 12


# ─── Response Model Construction ─────────────────────────────────────────

def test_summary_model_construction() -> None:
    domains = [
        DomainScore(
            domain="nemsis",
            score=85,
            passing=10,
            warning=1,
            critical=0,
        ),
        DomainScore(
            domain="dea",
            score=70,
            passing=5,
            warning=0,
            critical=2,
        ),
    ]
    summary = ComplianceCommandSummary(
        overall_score=77,
        total_items=18,
        passing_items=15,
        warning_items=1,
        critical_items=2,
        domains=domains,
        priority_alerts=[],
        action_queue=[],
        generated_at=datetime.now(UTC).isoformat(),
    )
    assert summary.overall_score == 77
    assert len(summary.domains) == 2
    assert summary.domains[0].domain == "nemsis"


def test_domain_score_seven_domains() -> None:
    """All 7 domain keys are accepted as valid."""
    for domain in DOMAINS:
        ds = DomainScore(domain=domain, score=75)
        assert ds.domain == domain
        assert ds.score == 75


def test_summary_overall_clamps_to_0_100() -> None:
    summary = ComplianceCommandSummary(
        overall_score=100,
        generated_at=datetime.now(UTC).isoformat(),
    )
    assert summary.overall_score == 100

    summary2 = ComplianceCommandSummary(
        overall_score=0,
        generated_at=datetime.now(UTC).isoformat(),
    )
    assert summary2.overall_score == 0

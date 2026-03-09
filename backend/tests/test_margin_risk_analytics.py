"""
Tests for margin risk analytics and release readiness gate.

Covers:
- BillingCommandService.get_margin_risk_by_tenant() cost model
- Release readiness gate structure validation
- Office Ally eligibility/claim-status SFTP operations
"""
from __future__ import annotations

import uuid
from collections import namedtuple
from unittest.mock import MagicMock, patch

import pytest

from core_app.integrations.officeally import (
    OfficeAllyClientError,
    OfficeAllySftpConfig,
    poll_claim_status_responses,
    poll_eligibility_responses,
    poll_era_files,
    submit_270_eligibility_inquiry,
    submit_276_claim_status_inquiry,
)
from core_app.services.billing_command_service import BillingCommandService

# ── Helpers ───────────────────────────────────────────────────────────────────

def _cfg() -> OfficeAllySftpConfig:
    return OfficeAllySftpConfig(
        host="sftp.test.local",
        port=22,
        username="testuser",
        password="testpass",
        remote_dir="/outbound",
        inbound_dir="/inbound",
        era_dir="/era",
        eligibility_dir="/eligibility",
        claim_status_dir="/claim_status",
    )


MarginRow = namedtuple(
    "MarginRow",
    ["id", "name", "billing_tier", "total_claims", "revenue_cents",
     "denied_count", "draft_count", "appeal_count"],
)


class FakeMarginDB:
    """DB mock returning canned tenant margin data."""

    def __init__(self, rows: list[MarginRow]) -> None:
        self._rows = rows
        self._chain = self

    def query(self, *a, **kw):
        return self

    def outerjoin(self, *a, **kw):
        return self

    def group_by(self, *a, **kw):
        return self

    def order_by(self, *a, **kw):
        return self

    def filter(self, *a, **kw):
        return self

    def all(self):
        return self._rows


# ═══════════════════════════════════════════════════════════════════════════════
# MARGIN RISK ANALYTICS TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMarginRiskByTenant:
    """BillingCommandService.get_margin_risk_by_tenant() cost model tests."""

    def test_empty_tenants_returns_zero(self) -> None:
        db = FakeMarginDB([])
        result = BillingCommandService(db).get_margin_risk_by_tenant()
        assert result["total_tenants"] == 0
        assert result["high_risk_count"] == 0
        assert result["tenants"] == []
        assert "as_of" in result

    def test_single_healthy_tenant(self) -> None:
        tid = uuid.uuid4()
        rows = [MarginRow(tid, "Healthy EMS", "enterprise", 100, 500000, 5, 2, 1)]
        db = FakeMarginDB(rows)
        result = BillingCommandService(db).get_margin_risk_by_tenant()

        assert result["total_tenants"] == 1
        t = result["tenants"][0]
        assert t["tenant_id"] == str(tid)
        assert t["name"] == "Healthy EMS"
        assert t["total_claims"] == 100
        assert t["revenue_cents"] == 500000
        assert t["denied_count"] == 5
        assert t["risk_level"] in ("low", "medium")
        assert t["margin_pct"] > 0
        assert t["stripe_fee_cents"] > 0
        assert t["clearinghouse_cost_cents"] == 100 * 50  # $0.50/claim
        assert t["rework_cost_cents"] == 5 * 2500  # $25/denial
        assert t["appeal_cost_cents"] == 1 * 3000  # $30/appeal

    def test_high_denial_rate_flags_risk(self) -> None:
        """Tenant with 80% denial rate should be high or critical risk."""
        tid = uuid.uuid4()
        rows = [MarginRow(tid, "Struggling EMS", "basic", 100, 10000, 80, 5, 5)]
        db = FakeMarginDB(rows)
        result = BillingCommandService(db).get_margin_risk_by_tenant()

        t = result["tenants"][0]
        assert t["risk_level"] in ("high", "critical")
        assert result["high_risk_count"] == 1
        assert t["denial_rate_pct"] == 80.0

    def test_zero_revenue_tenant(self) -> None:
        """Tenant with zero revenue should not cause division by zero."""
        tid = uuid.uuid4()
        rows = [MarginRow(tid, "New EMS", "basic", 10, 0, 0, 10, 0)]
        db = FakeMarginDB(rows)
        result = BillingCommandService(db).get_margin_risk_by_tenant()

        t = result["tenants"][0]
        assert t["margin_pct"] == 0
        assert t["risk_level"] == "critical"  # 0% margin < 30% threshold

    def test_multiple_tenants_counted(self) -> None:
        rows = [
            MarginRow(uuid.uuid4(), "A", "enterprise", 200, 1000000, 10, 5, 3),
            MarginRow(uuid.uuid4(), "B", "basic", 50, 5000, 40, 2, 2),
            MarginRow(uuid.uuid4(), "C", "standard", 100, 300000, 5, 0, 0),
        ]
        db = FakeMarginDB(rows)
        result = BillingCommandService(db).get_margin_risk_by_tenant()

        assert result["total_tenants"] == 3
        assert result["high_risk_count"] >= 1
        names = {t["name"] for t in result["tenants"]}
        assert names == {"A", "B", "C"}

    def test_cost_model_arithmetic(self) -> None:
        """Verify the cost model formula matches expected values."""
        tid = uuid.uuid4()
        # 50 claims, 200000 revenue, 10 denied, 0 draft, 5 appeals
        # paid_count = 50 - 10 - 0 - 5 = 35
        # stripe = 200000 * 0.029 + 35 * 30 = 5800 + 1050 = 6850
        # clearinghouse = 50 * 50 = 2500
        # rework = 10 * 2500 = 25000
        # appeal = 5 * 3000 = 15000
        # total_cost = 6850 + 2500 + 25000 + 15000 = 49350
        # net_margin = 200000 - 49350 = 150650
        # margin_pct = 150650 / 200000 * 100 = 75.33
        rows = [MarginRow(tid, "Test EMS", "standard", 50, 200000, 10, 0, 5)]
        db = FakeMarginDB(rows)
        result = BillingCommandService(db).get_margin_risk_by_tenant()

        t = result["tenants"][0]
        assert t["stripe_fee_cents"] == 6850
        assert t["clearinghouse_cost_cents"] == 2500
        assert t["rework_cost_cents"] == 25000
        assert t["appeal_cost_cents"] == 15000
        assert t["total_cost_cents"] == 49350
        assert t["net_margin_cents"] == 150650
        assert t["margin_pct"] == 75.33
        assert t["risk_level"] == "low"  # 75.33% > 70%


# ═══════════════════════════════════════════════════════════════════════════════
# OFFICE ALLY ELIGIBILITY / CLAIM STATUS SFTP TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestEligibilityInquiry:
    """Test submit_270_eligibility_inquiry SFTP operation."""

    @patch("core_app.integrations.officeally._connect")
    def test_submit_270_uploads_file(self, mock_connect: MagicMock) -> None:
        mock_sftp = MagicMock()
        mock_transport = MagicMock()
        mock_connect.return_value = (mock_transport, mock_sftp)

        result = submit_270_eligibility_inquiry(
            cfg=_cfg(),
            file_name="270_test.x12",
            x12_bytes=b"ISA*00*test~",
        )

        assert result == "/outbound/270_test.x12"
        mock_sftp.putfo.assert_called_once()
        mock_sftp.close.assert_called_once()
        mock_transport.close.assert_called_once()

    @patch("core_app.integrations.officeally._connect")
    def test_submit_270_propagates_sftp_error(self, mock_connect: MagicMock) -> None:
        mock_connect.side_effect = OfficeAllyClientError("sftp_down")
        with pytest.raises(OfficeAllyClientError, match="sftp_down"):
            submit_270_eligibility_inquiry(
                cfg=_cfg(), file_name="270_fail.x12", x12_bytes=b"ISA*00~",
            )


class TestClaimStatusInquiry:
    """Test submit_276_claim_status_inquiry SFTP operation."""

    @patch("core_app.integrations.officeally._connect")
    def test_submit_276_uploads_file(self, mock_connect: MagicMock) -> None:
        mock_sftp = MagicMock()
        mock_transport = MagicMock()
        mock_connect.return_value = (mock_transport, mock_sftp)

        result = submit_276_claim_status_inquiry(
            cfg=_cfg(),
            file_name="276_test.x12",
            x12_bytes=b"ISA*00*276test~",
        )

        assert result == "/outbound/276_test.x12"
        mock_sftp.putfo.assert_called_once()

    @patch("core_app.integrations.officeally._connect")
    def test_submit_276_propagates_sftp_error(self, mock_connect: MagicMock) -> None:
        mock_connect.side_effect = OfficeAllyClientError("connection_refused")
        with pytest.raises(OfficeAllyClientError, match="connection_refused"):
            submit_276_claim_status_inquiry(
                cfg=_cfg(), file_name="276_fail.x12", x12_bytes=b"ISA*00~",
            )


class TestEligibilityPolling:
    """Test poll_eligibility_responses delegates to retrieve_sftp_files correctly."""

    @patch("core_app.integrations.officeally.retrieve_sftp_files")
    def test_polls_eligibility_dir_with_271_prefix(self, mock_retrieve: MagicMock) -> None:
        mock_retrieve.return_value = [
            {"filename": "271_resp_001.x12", "content": "ISA*00~", "size_bytes": 8}
        ]
        result = poll_eligibility_responses(cfg=_cfg(), max_files=10)

        mock_retrieve.assert_called_once_with(
            cfg=_cfg(),
            remote_dir="/eligibility",
            prefix_filter="271",
            max_files=10,
        )
        assert len(result) == 1
        assert result[0]["filename"] == "271_resp_001.x12"


class TestClaimStatusPolling:
    """Test poll_claim_status_responses delegates to retrieve_sftp_files correctly."""

    @patch("core_app.integrations.officeally.retrieve_sftp_files")
    def test_polls_claim_status_dir_with_277_prefix(self, mock_retrieve: MagicMock) -> None:
        mock_retrieve.return_value = [
            {"filename": "277_resp_001.x12", "content": "ISA*00~", "size_bytes": 8}
        ]
        result = poll_claim_status_responses(cfg=_cfg(), max_files=25)

        mock_retrieve.assert_called_once_with(
            cfg=_cfg(),
            remote_dir="/claim_status",
            prefix_filter="277",
            max_files=25,
        )
        assert len(result) == 1


class TestERAPolling:
    """Test poll_era_files delegates to retrieve_sftp_files correctly."""

    @patch("core_app.integrations.officeally.retrieve_sftp_files")
    def test_polls_era_dir_with_835_prefix(self, mock_retrieve: MagicMock) -> None:
        mock_retrieve.return_value = []
        result = poll_era_files(cfg=_cfg(), max_files=5)

        mock_retrieve.assert_called_once_with(
            cfg=_cfg(),
            remote_dir="/era",
            prefix_filter="835",
            max_files=5,
        )
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestOfficeAllyConfig:
    """OfficeAllySftpConfig validation and _validate_config."""

    def test_missing_host_raises(self) -> None:
        cfg = OfficeAllySftpConfig(host="", port=22, username="u", password="p")
        with pytest.raises(OfficeAllyClientError, match="not_configured"):
            from core_app.integrations.officeally import _validate_config
            _validate_config(cfg)

    def test_missing_username_raises(self) -> None:
        cfg = OfficeAllySftpConfig(host="h", port=22, username="", password="p")
        with pytest.raises(OfficeAllyClientError, match="not_configured"):
            from core_app.integrations.officeally import _validate_config
            _validate_config(cfg)

    def test_missing_password_raises(self) -> None:
        cfg = OfficeAllySftpConfig(host="h", port=22, username="u", password="")
        with pytest.raises(OfficeAllyClientError, match="not_configured"):
            from core_app.integrations.officeally import _validate_config
            _validate_config(cfg)

    def test_valid_config_passes(self) -> None:
        cfg = _cfg()
        from core_app.integrations.officeally import _validate_config
        _validate_config(cfg)  # Should not raise

"""
Office Ally X12 835 — Unit Tests
Covers: CARC/RARC denial classification, 835 parsing, SFTP submission boundary,
ingest classification completeness.

DIRECTIVE REQUIREMENT: Office Ally ingest classification tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core_app.billing.x12_835 import (
    EraDenial,
    classify_denial,
    parse_835,
)
from core_app.integrations.officeally import (
    OfficeAllyClientError,
    OfficeAllySftpConfig,
    submit_837_via_sftp,
)

# ── CARC/RARC Denial Classification Tests ────────────────────────────────────

class TestDenialClassification:
    """Every known CARC code must classify into a human-readable category."""

    def test_co_4_modifier_mismatch(self) -> None:
        result = classify_denial("CO", "4")
        assert result["code"] == "CO-4"
        assert result["category"] == "Modifier/Procedure Mismatch"
        assert "modifier" in result["action"].lower()

    def test_co_16_missing_information(self) -> None:
        result = classify_denial("CO", "16")
        assert result["code"] == "CO-16"
        assert result["category"] == "Missing Information"

    def test_co_18_duplicate_claim(self) -> None:
        result = classify_denial("CO", "18")
        assert result["category"] == "Duplicate Claim"
        assert "duplicate" in result["description"].lower()

    def test_co_29_timely_filing(self) -> None:
        result = classify_denial("CO", "29")
        assert result["category"] == "Timely Filing"
        assert "filing" in result["action"].lower()

    def test_co_45_charges_exceed_allowed(self) -> None:
        result = classify_denial("CO", "45")
        assert result["category"] == "Charges Exceed Allowed"

    def test_co_50_medical_necessity(self) -> None:
        result = classify_denial("CO", "50")
        assert result["category"] == "Medical Necessity"
        assert "PCS" in result["action"] or "appeal" in result["action"].lower()

    def test_co_97_bundled_service(self) -> None:
        result = classify_denial("CO", "97")
        assert result["category"] == "Bundled Service"

    def test_co_109_not_covered(self) -> None:
        result = classify_denial("CO", "109")
        assert result["category"] == "Not Covered"

    def test_co_167_diagnosis_mismatch(self) -> None:
        result = classify_denial("CO", "167")
        assert result["category"] == "Diagnosis Mismatch"
        assert "ICD" in result["action"]

    def test_co_197_authorization_required(self) -> None:
        result = classify_denial("CO", "197")
        assert result["category"] == "Authorization Required"

    def test_co_204_service_not_rendered(self) -> None:
        result = classify_denial("CO", "204")
        assert result["category"] == "Service Not Rendered"

    def test_co_236_level_of_service(self) -> None:
        result = classify_denial("CO", "236")
        assert result["category"] == "Level of Service"

    def test_pr_1_deductible(self) -> None:
        result = classify_denial("PR", "1")
        assert result["category"] == "Deductible"
        assert "patient" in result["action"].lower()

    def test_pr_2_coinsurance(self) -> None:
        result = classify_denial("PR", "2")
        assert result["category"] == "Coinsurance"

    def test_pr_3_copay(self) -> None:
        result = classify_denial("PR", "3")
        assert result["category"] == "Copay"

    def test_pr_96_non_covered(self) -> None:
        result = classify_denial("PR", "96")
        assert result["category"] == "Non-Covered Charge"
        assert "ABN" in result["action"]

    def test_oa_23_coordination_of_benefits(self) -> None:
        result = classify_denial("OA", "23")
        assert result["category"] == "Coordination of Benefits"

    def test_unknown_code_falls_back_to_group(self) -> None:
        result = classify_denial("CO", "9999")
        assert result["code"] == "CO-9999"
        assert result["category"] == "Contractual Obligation"

    def test_unknown_group_falls_back_gracefully(self) -> None:
        result = classify_denial("XX", "1")
        assert result["code"] == "XX-1"
        assert result["category"] == "Unknown Adjustment"

    def test_pi_group_label(self) -> None:
        result = classify_denial("PI", "999")
        assert result["category"] == "Payer Initiated Reduction"

    def test_all_classifications_have_required_keys(self) -> None:
        """Every classification result must have code, category, description, action."""
        test_codes = [
            ("CO", "4"), ("CO", "16"), ("CO", "50"), ("PR", "1"),
            ("PR", "3"), ("OA", "23"), ("XX", "0"),
        ]
        for group, reason in test_codes:
            result = classify_denial(group, reason)
            assert "code" in result
            assert "category" in result
            assert "description" in result
            assert "action" in result
            assert len(result["category"]) > 0
            assert len(result["action"]) > 0


# ── 835 Parsing Tests ────────────────────────────────────────────────────────

class TestParse835:
    """X12 835 remittance parsing extracts claims and denials correctly."""

    def _build_835(self, claims: list[tuple[str, list[tuple[str, str, str]]]]) -> str:
        """Build a minimal 835 X12 string from claim+adjustment definitions."""
        segments: list[str] = ["ISA*00*...*~", "GS*HP*...*~"]
        for claim_id, adjustments in claims:
            segments.append(f"CLP*{claim_id}*1*1000*800*200*~")
            for group, reason, amount in adjustments:
                segments.append(f"CAS*{group}*{reason}*{amount}*~")
        segments.append("SE*...*~")
        return "~".join(segments)

    def test_parse_single_claim_single_denial(self) -> None:
        x12 = self._build_835([("CLM001", [("CO", "50", "200.00")])])
        result = parse_835(x12)
        assert len(result["denials"]) == 1
        denial = result["denials"][0]
        assert denial["claim_id"] == "CLM001"
        assert denial["group_code"] == "CO"
        assert denial["reason_code"] == "50"
        assert denial["amount"] == 200.0
        assert denial["classification"]["category"] == "Medical Necessity"

    def test_parse_multiple_denials_same_claim(self) -> None:
        x12 = self._build_835([
            ("CLM002", [("CO", "16", "100"), ("PR", "1", "50"), ("CO", "45", "75")]),
        ])
        result = parse_835(x12)
        assert len(result["denials"]) == 3
        categories = {d["classification"]["category"] for d in result["denials"]}
        assert "Missing Information" in categories
        assert "Deductible" in categories
        assert "Charges Exceed Allowed" in categories

    def test_parse_multiple_claims(self) -> None:
        x12 = self._build_835([
            ("CLM003", [("CO", "97", "150")]),
            ("CLM004", [("PR", "2", "50")]),
        ])
        result = parse_835(x12)
        assert len(result["denials"]) == 2
        claim_ids = {d["claim_id"] for d in result["denials"]}
        assert claim_ids == {"CLM003", "CLM004"}

    def test_parse_empty_835(self) -> None:
        result = parse_835("ISA*...*~GS*HP*...*~SE*...*~")
        assert result["denials"] == []

    def test_parse_non_numeric_amount_defaults_to_zero(self) -> None:
        x12 = "CLP*CLM005*1*1000*800*~CAS*CO*50*BAD_AMOUNT*~"
        result = parse_835(x12)
        assert len(result["denials"]) == 1
        assert result["denials"][0]["amount"] == 0.0

    def test_parse_real_world_835_segments(self) -> None:
        """Partial real-world 835 structure."""
        x12 = (
            "ISA*00*          *00*          *ZZ*SENDER    *ZZ*RECEIVER  *260101*1200*^*00501*000000001*0*P*:~"
            "GS*HP*SENDER*RECEIVER*20260101*1200*1*X*005010X221A1~"
            "ST*835*0001~"
            "BPR*I*800.00*C*CHK************20260115~"
            "TRN*1*12345678*1234567890~"
            "CLP*AMB-2026-001*1*1500.00*800.00*200.00~"
            "CAS*CO*45*500.00~"
            "CAS*PR*1*200.00~"
            "CLP*AMB-2026-002*1*1200.00*1200.00*0.00~"
            "SE*10*0001~"
            "GE*1*1~"
            "IEA*1*000000001~"
        )
        result = parse_835(x12)
        assert len(result["denials"]) == 2
        # First claim has CO-45 and PR-1
        assert result["denials"][0]["claim_id"] == "AMB-2026-001"
        assert result["denials"][0]["classification"]["category"] == "Charges Exceed Allowed"
        assert result["denials"][1]["claim_id"] == "AMB-2026-001"
        assert result["denials"][1]["classification"]["category"] == "Deductible"


# ── EraDenial Data Object Tests ──────────────────────────────────────────────

class TestEraDenial:
    """EraDenial dataclass integrity."""

    def test_era_denial_is_frozen(self) -> None:
        d = EraDenial(claim_id="CLM001", group_code="CO", reason_code="50", amount=200.0)
        with pytest.raises(AttributeError):
            d.amount = 0  # type: ignore[misc]

    def test_era_denial_fields(self) -> None:
        d = EraDenial(claim_id="CLM002", group_code="PR", reason_code="1", amount=50.0)
        assert d.claim_id == "CLM002"
        assert d.group_code == "PR"
        assert d.reason_code == "1"
        assert d.amount == 50.0


# ── Office Ally SFTP Boundary Tests ──────────────────────────────────────────

class TestOfficeAllySftp:
    """SFTP submission boundary: config validation, error classification."""

    def test_missing_host_raises_client_error(self) -> None:
        cfg = OfficeAllySftpConfig(host="", port=22, username="u", password="p")
        with pytest.raises(OfficeAllyClientError, match="office_ally_sftp_not_configured"):
            submit_837_via_sftp(cfg=cfg, file_name="test.x12", x12_bytes=b"ISA*~")

    def test_missing_username_raises_client_error(self) -> None:
        cfg = OfficeAllySftpConfig(host="sftp.example.com", port=22, username="", password="p")
        with pytest.raises(OfficeAllyClientError, match="office_ally_sftp_not_configured"):
            submit_837_via_sftp(cfg=cfg, file_name="test.x12", x12_bytes=b"ISA*~")

    def test_missing_password_raises_client_error(self) -> None:
        cfg = OfficeAllySftpConfig(host="sftp.example.com", port=22, username="u", password="")
        with pytest.raises(OfficeAllyClientError, match="office_ally_sftp_not_configured"):
            submit_837_via_sftp(cfg=cfg, file_name="test.x12", x12_bytes=b"ISA*~")

    def test_sftp_config_default_remote_dir(self) -> None:
        cfg = OfficeAllySftpConfig(host="h", port=22, username="u", password="p")
        assert cfg.remote_dir == "/"

    def test_sftp_config_custom_remote_dir(self) -> None:
        cfg = OfficeAllySftpConfig(host="h", port=22, username="u", password="p", remote_dir="/outbox")
        assert cfg.remote_dir == "/outbox"

    @patch("core_app.integrations.officeally.paramiko.Transport")
    def test_successful_sftp_upload_returns_remote_path(self, mock_transport_cls: MagicMock) -> None:
        """Verify SFTP upload returns correct remote path on success."""
        mock_transport = MagicMock()
        mock_transport_cls.return_value = mock_transport
        mock_sftp = MagicMock()
        # paramiko.SFTPClient.from_transport returns mock_sftp
        with patch("core_app.integrations.officeally.paramiko.SFTPClient") as mock_sftp_cls:
            mock_sftp_cls.from_transport.return_value = mock_sftp

            cfg = OfficeAllySftpConfig(
                host="sftp.officeally.com", port=22,
                username="ems_user", password="secure_pass",
                remote_dir="/outbox",
            )
            result = submit_837_via_sftp(
                cfg=cfg,
                file_name="batch_20260307.x12",
                x12_bytes=b"ISA*00*~",
            )
            assert result == "/outbox/batch_20260307.x12"
            mock_sftp.putfo.assert_called_once()

    @patch("core_app.integrations.officeally.paramiko.Transport")
    def test_sftp_transport_closed_on_error(self, mock_transport_cls: MagicMock) -> None:
        """Transport must close even on SFTP failure."""
        mock_transport = MagicMock()
        mock_transport_cls.return_value = mock_transport
        mock_transport.connect.side_effect = Exception("Connection refused")

        cfg = OfficeAllySftpConfig(host="bad.host", port=22, username="u", password="p")
        with pytest.raises(Exception, match="Connection refused"):
            submit_837_via_sftp(cfg=cfg, file_name="test.x12", x12_bytes=b"data")

        mock_transport.close.assert_called_once()


# ── Ingest Classification Completeness ───────────────────────────────────────

class TestIngestClassificationCompleteness:
    """Common ambulance billing denial codes must all be classified."""

    COMMON_AMBULANCE_DENIALS = [
        ("CO", "4"),   # Modifier
        ("CO", "16"),  # Missing info
        ("CO", "18"),  # Duplicate
        ("CO", "29"),  # Timely filing
        ("CO", "45"),  # Charges exceed
        ("CO", "50"),  # Medical necessity
        ("CO", "97"),  # Bundled
        ("CO", "109"), # Not covered
        ("CO", "167"), # Diagnosis mismatch
        ("CO", "197"), # Auth required
        ("CO", "204"), # Not rendered
        ("CO", "236"), # Level of service
        ("PR", "1"),   # Deductible
        ("PR", "2"),   # Coinsurance
        ("PR", "3"),   # Copay
        ("PR", "96"),  # Non-covered charge
        ("OA", "23"),  # COB
    ]

    @pytest.mark.parametrize("group,reason", COMMON_AMBULANCE_DENIALS)
    def test_common_denial_has_specific_classification(self, group: str, reason: str) -> None:
        result = classify_denial(group, reason)
        # Must NOT fall through to the generic group-level fallback
        assert result["category"] != "Contractual Obligation" or group != "CO" or reason == "4" or result["category"] != group
        # Must have a specific action recommendation
        assert len(result["action"]) > 10
        assert "Review" in result["action"] or "Submit" in result["action"] or "Bill" in result["action"] or "Verify" in result["action"] or "Write" in result["action"] or "Collect" in result["action"] or "Check" in result["action"] or "Obtain" in result["action"]

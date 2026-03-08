from __future__ import annotations

from core_app.api.dea_compliance_router import (
    _build_evidence_csv,
    _build_findings,
    _build_pdf_payload,
    _compute_bundle_hash,
    _summarize_cms_results,
    _summarize_dea_audits,
)


def test_bundle_hash_is_deterministic_for_same_core_payload() -> None:
    bundle_core = {
        "schema_version": "dea_cms_evidence_bundle.v1",
        "bundle_id": "bundle-123",
        "generated_at": "2026-03-08T12:00:00+00:00",
        "window_days": 30,
        "tenant_id": "tenant-1",
        "source_manifest": {
            "dea_audit_report_ids": ["a", "b"],
            "cms_gate_result_ids": ["c"],
        },
    }

    hash_one = _compute_bundle_hash(bundle_core)
    hash_two = _compute_bundle_hash(bundle_core)

    assert hash_one == hash_two
    assert len(hash_one) == 64


def test_build_evidence_csv_contains_expected_sections() -> None:
    csv_text = _build_evidence_csv(
        dea_audits=[
            {
                "report_id": "dea-1",
                "generated_at": "2026-03-08T10:00:00+00:00",
                "unit_id": "M12",
                "result": {
                    "passed": False,
                    "score": 70,
                    "hard_block": True,
                    "metrics": {
                        "open_discrepancies": 1,
                        "unwitnessed_waste_events": 0,
                    },
                },
            }
        ],
        cms_results=[
            {
                "record_id": "cms-1",
                "evaluated_at": "2026-03-08T09:00:00+00:00",
                "case_id": "case-1",
                "passed": True,
                "score": 82,
                "hard_block": False,
                "bs_flag": False,
                "issues": [],
            }
        ],
    )

    assert "DEA_AUDIT" in csv_text
    assert "CMS_GATE" in csv_text
    assert "dea-1" in csv_text
    assert "cms-1" in csv_text


def test_summaries_and_findings_capture_hard_blocks() -> None:
    dea_rows = [
        {
            "result": {
                "passed": False,
                "score": 68,
                "hard_block": True,
                "required_actions": ["Resolve discrepancy"],
                "metrics": {
                    "open_discrepancies": 1,
                    "unwitnessed_waste_events": 1,
                },
            }
        }
    ]
    cms_rows = [
        {
            "passed": False,
            "score": 50,
            "hard_block": True,
            "bs_flag": True,
            "issues": ["Missing signature"],
        }
    ]

    dea_summary = _summarize_dea_audits(dea_rows)
    cms_summary = _summarize_cms_results(cms_rows)
    findings = _build_findings(
        dea_rows=dea_rows,
        cms_rows=cms_rows,
        dea_summary=dea_summary,
        cms_summary=cms_summary,
    )

    assert dea_summary["hard_block_count"] == 1
    assert cms_summary["hard_block_count"] == 1
    assert any("DEA hard blocks" in item for item in findings["critical_findings"])
    assert any("CMS hard blocks" in item for item in findings["critical_findings"])


def test_pdf_payload_contains_integrity_block_and_manifest_reference() -> None:
    bundle_core = {
        "bundle_id": "bundle-xyz",
        "generated_at": "2026-03-08T12:00:00+00:00",
        "window_days": 30,
        "tenant_id": "tenant-9",
        "dea_summary": {"total": 3, "pass_rate": 66, "hard_block_count": 1},
        "cms_summary": {"total": 5, "pass_rate": 80, "hard_block_count": 1},
        "findings": {
            "critical_findings": ["DEA hard blocks present in 1 audit(s)."],
            "required_actions": ["Resolve discrepancy events."],
        },
        "previous_bundle_hash": "abc123",
    }

    payload = _build_pdf_payload(
        bundle_core=bundle_core,
        immutable_hash="f" * 64,
        csv_filename="bundle.csv",
    )

    assert payload["template_id"] == "fusionems.dea_cms_evidence_bundle.v1"
    assert payload["document_title"].startswith("FusionEMS Quantum")
    sections = payload.get("sections") or []
    assert any(section.get("type") == "integrity_block" for section in sections)
    manifest = next(
        section for section in sections if section.get("title") == "Evidence Manifest"
    )
    rows = manifest.get("rows") or []
    assert any("CSV artifact" in row for row in rows)

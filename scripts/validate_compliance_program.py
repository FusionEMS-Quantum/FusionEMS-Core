#!/usr/bin/env python3
"""Validate required compliance artifacts exist and emit evidence manifest."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "compliance" / "policies"
OUT_DIR = ROOT / "artifacts"
OUT_FILE = OUT_DIR / "compliance-evidence-manifest.json"

REQUIRED_FILES = [
    "information-security-policy.md",
    "acceptable-use-policy.md",
    "access-control-policy.md",
    "encryption-policy.md",
    "data-classification-policy.md",
    "data-retention-disposal-policy.md",
    "vulnerability-management-policy.md",
    "incident-response-plan.md",
    "breach-notification-procedure.md",
    "business-continuity-dr-plan.md",
    "vendor-management-policy.md",
    "risk-assessment-methodology.md",
    "risk-register.md",
    "security-awareness-training.md",
    "workforce-security-offboarding.md",
    "endpoint-workstation-policy.md",
    "media-disposal-procedure.md",
    "privacy-notice.md",
    "dsar-procedure.md",
    "baa-management.md",
    "change-management-policy.md",
    "system-description.md",
    "control-ownership-evidence-matrix.md",
    "subprocessor-register.md",
    "audit-preparation-checklist.md",
    "evidence-inventory.md",
]


def main() -> int:
    missing = []
    present = []

    for rel in REQUIRED_FILES:
        p = POLICY_DIR / rel
        if p.exists() and p.is_file():
            present.append(rel)
        else:
            missing.append(rel)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy_directory": str(POLICY_DIR),
        "required_count": len(REQUIRED_FILES),
        "present_count": len(present),
        "missing_count": len(missing),
        "present": present,
        "missing": missing,
        "status": "pass" if not missing else "fail",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if missing:
        print("Compliance validation failed. Missing required artifacts:")
        for item in missing:
            print(f" - {item}")
        print(f"Manifest written to: {OUT_FILE}")
        return 1

    print("Compliance validation passed.")
    print(f"Manifest written to: {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

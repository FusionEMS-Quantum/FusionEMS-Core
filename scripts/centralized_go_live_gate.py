#!/usr/bin/env python3
"""Centralized go-live gate for FusionEMS Quantum.

This gate enforces canonical architecture and trust-path requirements:
- No Microsoft tenant placeholder leakage in active production paths.
- Canonical live-status and release-readiness contracts are present.
- Canonical frontend live-status route and API wrapper are present.
- Duplicate active route/API artifacts are flagged as release blockers.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

BLOCKERS: list[str] = []
WARNINGS: list[str] = []


def _check(condition: bool, message: str) -> None:
    if condition:
        return
    BLOCKERS.append(message)


def _warn(condition: bool, message: str) -> None:
    if condition:
        return
    WARNINGS.append(message)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def check_placeholder_leaks() -> None:
    import os
    needle = "placeholder_rotate_graph_tenant_id"
    scan_roots = [
        REPO_ROOT / "backend",
        REPO_ROOT / "frontend",
        REPO_ROOT / "infra",
    ]
    findings: list[str] = []
    ignore_dirs = {".venv", "node_modules", ".next", "__pycache__", ".git", ".terraform"}
    for root in scan_roots:
        if not root.exists(): continue
        for dirpath, dirnames, filenames in os.walk(str(root)):
            dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
            for f in filenames:
                path = Path(dirpath) / f
                if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".json", ".env", ".yml", ".yaml", ".md"}:
                    continue
                try:
                    text = _read(path)
                    if needle in text:
                        findings.append(str(path.relative_to(REPO_ROOT)))
                except:
                    pass
    _check(len(findings) == 0, f"Microsoft tenant placeholder found in active paths: {findings}")

def check_backend_contracts() -> None:
    router_path = REPO_ROOT / "backend" / "core_app" / "api" / "platform_core_router.py"
    _check(router_path.exists(), "Missing backend platform core router")
    if not router_path.exists():
        return

    text = _read(router_path)
    _check('@router.get("/live-status")' in text, "Missing canonical /api/v1/platform/live-status endpoint")
    _check('@router.get("/release-readiness")' in text, "Missing canonical /api/v1/platform/release-readiness endpoint")

    config_path = REPO_ROOT / "backend" / "core_app" / "core" / "config.py"
    _check(config_path.exists(), "Missing backend settings config")
    if config_path.exists():
        config_text = _read(config_path)
        _check(
            "def is_valid_entra_tenant_identifier" in config_text,
            "Missing Entra tenant identifier validator in core config",
        )
        _check(
            "_validate_production_secrets" in config_text,
            "Missing production secret validation gate in core config",
        )


def check_frontend_contracts() -> None:
    api_path = REPO_ROOT / "frontend" / "services" / "api.ts"
    _check(api_path.exists(), "Missing canonical frontend API layer file")
    if api_path.exists():
        api_text = _read(api_path)
        _check(
            "export async function getPlatformLiveStatus" in api_text,
            "Missing getPlatformLiveStatus API wrapper in frontend/services/api.ts",
        )
        _check(
            "export async function getReleaseReadiness" in api_text,
            "Missing getReleaseReadiness API wrapper in frontend/services/api.ts",
        )

    live_status_page = REPO_ROOT / "frontend" / "app" / "live-status" / "page.tsx"
    _check(live_status_page.exists(), "Missing canonical live-status route at frontend/app/live-status/page.tsx")

    system_health_page = REPO_ROOT / "frontend" / "app" / "system-health" / "page.tsx"
    _check(system_health_page.exists(), "Missing operational live-status implementation page")


def check_duplicate_active_paths() -> None:
    nested_app_route = REPO_ROOT / "frontend" / "app" / "app"
    _check(
        not nested_app_route.exists(),
        "Duplicate route family detected at frontend/app/app; collapse to one canonical route architecture",
    )

    api_backup = REPO_ROOT / "frontend" / "services" / "api.ts.bak"
    _check(
        not api_backup.exists(),
        "Duplicate API helper artifact exists at frontend/services/api.ts.bak; remove from active production path",
    )


def run() -> int:
    check_placeholder_leaks()
    check_backend_contracts()
    check_frontend_contracts()
    check_duplicate_active_paths()

    if BLOCKERS:
        print("FAIL centralized go-live gate")
        for msg in BLOCKERS:
            print(f"  BLOCKER: {msg}")
    else:
        print("OK centralized go-live gate")

    for msg in WARNINGS:
        print(f"  WARN: {msg}")

    return 1 if BLOCKERS else 0


if __name__ == "__main__":
    raise SystemExit(run())

#!/usr/bin/env python3
"""Canonical release gate runner for FusionEMS Quantum.

Runs deterministic, repository-local validation gates and fails fast on blockers.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Gate:
    name: str
    command: list[str]


def run_gate(repo_root: Path, gate: Gate) -> int:
    print(f"\n=== GATE: {gate.name} ===")
    proc = subprocess.Popen(
        gate.command,
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
    return proc.wait()


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    python = sys.executable

    gates = [
        Gate("Auth Surface Validation", [python, "scripts/validate_auth_surface.py"]),
        Gate("Placeholder Secret Scan", [python, "scripts/scan_placeholders.py"]),
        Gate("Route Matrix CI Gate", [python, "scripts/ci_gate_route_matrix.py"]),
        Gate("Centralized Go-Live Gate", [python, "scripts/centralized_go_live_gate.py"]),
    ]

    failures: list[str] = []
    for gate in gates:
        code = run_gate(repo_root, gate)
        if code != 0:
            failures.append(f"{gate.name} (exit={code})")

    if failures:
        print("\nRELEASE GATE FAILED")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("\nRELEASE GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

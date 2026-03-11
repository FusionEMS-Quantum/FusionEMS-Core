#!/usr/bin/env python3
"""CI Gate: prohibit crash-on-fallback injections in frontend.

This repository previously had automated edits that replaced safe nullish-coalescing
fallbacks with expressions that throw at runtime (e.g.,
`?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()`).

In a mission-critical, multi-tenant SaaS, UI render-path exceptions are not an
acceptable enforcement mechanism. Missing or partial data must degrade
gracefully and emit telemetry via supported channels.

Exit codes:
  0 = no forbidden patterns detected
  1 = forbidden patterns detected
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "frontend" / "app"


@dataclass(frozen=True)
class Finding:
    file_path: str
    line: int
    snippet: str
    pattern: str


FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "marker:unsafe-silent-fallback",
        re.compile(r"Unsafe silent fallback\\. Dependency missing\\.", re.IGNORECASE),
    ),
    (
        "marker:fallback-detected",
        re.compile(r"Fallback detected", re.IGNORECASE),
    ),
    (
        "throw-in-nullish-coalescing",
        re.compile(
            r"\?\?\s*\(\(\)\s*=>\s*\{\s*throw\s+new\s+Error",
            re.IGNORECASE,
        ),
    ),
)

EXCLUDE_DIRS = {"node_modules", ".next", ".git"}


def _iter_tsx_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*.tsx"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        files.append(p)
    return files


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for fp in _iter_tsx_files(APP_DIR):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        rel = str(fp.relative_to(ROOT))
        for idx, line in enumerate(text.splitlines(), 1):
            for label, pat in FORBIDDEN_PATTERNS:
                if pat.search(line):
                    findings.append(
                        Finding(
                            file_path=rel,
                            line=idx,
                            snippet=line.strip()[:240],
                            pattern=label,
                        )
                    )
    return findings


def main() -> int:
    if not APP_DIR.exists():
        # Non-frontend repos shouldn't fail this gate.
        print(json.dumps({"status": "skipped", "reason": "frontend/app not found"}))
        return 0

    findings = scan()

    output = {
        "status": "fail" if findings else "pass",
        "root": str(APP_DIR),
        "count": len(findings),
        "findings": [
            {
                "file": f.file_path,
                "line": f.line,
                "pattern": f.pattern,
                "snippet": f.snippet,
            }
            for f in findings[:300]
        ],
        "truncated": max(len(findings) - 300, 0),
    }

    print(json.dumps(output, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    os.chdir(str(ROOT))
    sys.exit(main())

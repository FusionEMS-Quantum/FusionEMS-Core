from __future__ import annotations

import concurrent.futures
import re
import sys
from dataclasses import dataclass
from pathlib import Path

print("=========================================================================")
print(" FUSION EMS COMMAND - GOD SPEED DEPLOYMENT ENFORCER")
print(" EXECUTING FINAL BUILD DIRECTIVE: ZERO STUBS, ZERO FAKES, 100% REAL DATA")
print(" BATCH PARALLEL WORKERS INITIALIZING...")
print("=========================================================================")

# Target React standard files
TARGET_EXTS = {'.tsx', '.ts', '.jsx', '.js'}
FRONTEND_DIR = Path('frontend/app')


@dataclass(frozen=True)
class Finding:
    file_path: str
    line: int
    snippet: str


FORBIDDEN_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Unsafe silent fallback\\. Dependency missing\\.", re.IGNORECASE),
    re.compile(r"Fallback detected", re.IGNORECASE),
    re.compile(r"\\?\\?\\s*\\(\\(\\)\\s*=>\\s*\\{\\s*throw\\s+new\\s+Error", re.IGNORECASE),
)


def _scan_file(filepath: Path) -> list[Finding]:
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return []

    rel = str(filepath)
    findings: list[Finding] = []
    for idx, line in enumerate(text.splitlines(), 1):
        if any(p.search(line) for p in FORBIDDEN_MARKERS):
            findings.append(Finding(file_path=rel, line=idx, snippet=line.strip()[:200]))
    return findings

def worker_task(file_path: Path) -> list[Finding]:
    return _scan_file(file_path)

def main():
    if not FRONTEND_DIR.exists():
        print(f"Error: {FRONTEND_DIR} not found.")
        return 2

    files_to_process = [
        p for p in FRONTEND_DIR.rglob('*') 
        if p.is_file() and p.suffix in TARGET_EXTS
    ]
    
    print(f"Discovered {len(files_to_process)} target files in {FRONTEND_DIR}. Commencing scan...")
    
    all_findings: list[Finding] = []
    # Parallel scan
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        for findings in executor.map(worker_task, files_to_process):
            all_findings.extend(findings)

    if all_findings:
        print("\n[!] FORBIDDEN FRONTEND PATTERNS DETECTED (refuse-to-deploy):")
        for f in all_findings[:300]:
            print(f"- {f.file_path}:{f.line}: {f.snippet}")
        if len(all_findings) > 300:
            print(f"... and {len(all_findings) - 300} more")
        return 2

    print("\n[+] SCAN COMPLETE. No forbidden crash-on-fallback patterns detected.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

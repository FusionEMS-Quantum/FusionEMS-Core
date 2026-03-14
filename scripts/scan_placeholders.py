"""Scan source files for placeholder secrets that must not reach production."""
from __future__ import annotations
import re
import sys
from pathlib import Path

PLACEHOLDER_PATTERNS = [
    re.compile(r"REPLACE_WITH_", re.IGNORECASE),
    re.compile(r"YOUR_SECRET_HERE", re.IGNORECASE),
    re.compile(r"<YOUR_", re.IGNORECASE),
    re.compile(r"CHANGE_ME", re.IGNORECASE),
    re.compile(r"TODO_SECRET", re.IGNORECASE),
    re.compile(r"INSERT_API_KEY", re.IGNORECASE),
    re.compile(r"placeholder_rotate_graph_tenant_id", re.IGNORECASE),
    re.compile(r"placeholder_rotate_", re.IGNORECASE),  # Secret rotation incomplete values
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".next",
    ".mypy_cache",
    "dist",
    "build",
    "venv",
    ".venv",
    ".github",
    "artifacts",
    "reports",
}
EXCLUDE_FILES = {"scan_placeholders.py", "release-gate.yml"}
SCAN_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".json", ".yml", ".yaml", ".md"}
SCAN_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
}
SCAN_ROOTS = ("backend", "frontend", "infra", "scripts")
IGNORE_LINE_PATTERNS = [
    re.compile(r"re\.compile\(", re.IGNORECASE),
    re.compile(r"_PLACEHOLDER_CONFIG_PATTERN", re.IGNORECASE),
    re.compile(r"placeholder_patterns", re.IGNORECASE),
    re.compile(r"needle\s*=\s*[\"']placeholder_rotate_graph_tenant_id", re.IGNORECASE),
    re.compile(r"rotation patterns like", re.IGNORECASE),
    re.compile(r"^\s*r\"\(\?:placeholder", re.IGNORECASE),
    re.compile(
        r'^\s*"(placeholder|placeholder_rotate|change_me|changeme|your_|your-|replace_with|<your|todo|todo_|xxx|xxxx|insert_|put_your|sample_|test_|your_tenant|your_client|sample)",?\s*$',
        re.IGNORECASE,
    ),
]

repo_root = Path(__file__).parent.parent


def scan() -> list[str]:
    findings: list[str] = []
    for root_name in SCAN_ROOTS:
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if any(ex in path.parts for ex in EXCLUDE_DIRS):
                continue
            if path.name in EXCLUDE_FILES:
                continue
            if not path.is_file():
                continue
            if path.suffix not in SCAN_EXTENSIONS and path.name not in SCAN_FILENAMES:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if any(pat.search(line) for pat in IGNORE_LINE_PATTERNS):
                    continue
                for pat in PLACEHOLDER_PATTERNS:
                    if pat.search(line):
                        findings.append(f"{path.relative_to(repo_root)}:{lineno}: {line.strip()[:120]}")
                        break
    return findings


if __name__ == "__main__":
    hits = scan()
    if hits:
        print(f"FAIL — {len(hits)} placeholder(s) found:")
        for h in hits:
            print(f"  {h}")
        sys.exit(1)
    print("OK — no placeholders found")

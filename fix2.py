import sys
content = """def check_placeholder_leaks() -> None:
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
    _check(len(findings) == 0, f"Microsoft tenant placeholder found in active paths: {findings}")"""

import re
with open("scripts/centralized_go_live_gate.py", "r") as f:
    text = f.read()

# Replace the old function
text = re.sub(r'def check_placeholder_leaks\(\) -> None:.*?(?=def check_backend_contracts\(\) -> None:)', content + "\n\n", text, flags=re.DOTALL)

with open("scripts/centralized_go_live_gate.py", "w") as f:
    f.write(text)

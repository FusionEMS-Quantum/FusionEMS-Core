import sys
with open("scripts/centralized_go_live_gate.py", "r") as f:
    lines = f.readlines()
with open("scripts/centralized_go_live_gate.py", "w") as f:
    for line in lines:
        if 'for path in root.rglob("*"):' in line:
            f.write('        for path in root.rglob("*"):\n')
            f.write('            if any(part in {"node_modules", ".next", "__pycache__", ".git", ".venv", ".terraform"} for part in path.parts):\n')
            f.write('                continue\n')
        else:
            f.write(line)

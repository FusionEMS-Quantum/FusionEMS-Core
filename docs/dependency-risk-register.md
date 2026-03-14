# Dependency Risk Register (Go-Live)

## Frontend direct dependencies review

Command run: `npm outdated --json`

### Upgraded tonight (compatible)
- Installed to latest compatible ranges and regenerated `frontend/package-lock.json` via `npm install`.

### Deferred with justification (breaking-major risk tonight)
- `date-fns` 3.6.0 -> 4.1.0 — **defer-with-justification** (major upgrade likely API breaking across date formatting callsites).
- `framer-motion` 11.x -> 12.x — **defer-with-justification** (major behavior changes across animation props).
- `recharts` 2.x -> 3.x — **defer-with-justification** (major chart API changes).
- `tailwind-merge` 2.x -> 3.x — **pinned-for-compatibility** with current Tailwind config.
- `zustand` 4.x -> 5.x — **defer-with-justification** (major middleware/store typing changes).

## Backend direct dependencies review

Command run: `python3 -m pip list --outdated --format=json`

### Result
- No direct backend runtime requirements from `backend/requirements.txt` were changed tonight.
- Outdated list observed in environment primarily contains toolchain/global packages (black, ruff, pip, setuptools, etc.).

### Classification
- `black` / `ruff` / `pip` / `setuptools` / `platformdirs` and other environment tooling — **non-blocking** for runtime go-live, **defer-with-justification** for separate dev-image/toolchain refresh window.

## Release posture
- Any dependency not upgraded tonight is explicitly classified as above and tracked in this register.

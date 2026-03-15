# ENOPRO Workspace Recovery

`ENOPRO: No file system provider found for resource 'file:///workspaces/FusionEMS-Core'`

This error is not a normal application runtime failure. It means the VS Code or Codespaces workspace provider lost access to the mounted repository path, so terminal- and task-backed operations cannot start even when the code itself is valid.

## What this breaks

- terminal execution from the workspace
- task execution
- local git operations that require the workspace provider
- test and smoke execution launched through the editor integration

## What it does **not** mean

- it does **not** automatically mean the backend code is broken
- it does **not** mean the frontend has compile errors
- it does **not** mean Docker, Python, or the repo layout are necessarily invalid

## First recovery steps

Run these in order, stopping as soon as the workspace provider recovers:

1. Reload the VS Code window.
2. Reopen the repository folder if the Explorer looks stale.
3. Rebuild or restart the dev container / Codespace.
4. Re-run the workspace health scripts:
   - `bash scripts/enopro-workspace-doctor.sh`
   - `bash scripts/codespace-up.sh`
   - `bash scripts/codespace-health.sh`

## Expected healthy signals

The workspace is ready again when all of the following are true:

- terminal commands can run from `/workspaces/FusionEMS-Core`
- `.venv/bin/python` is present
- `rg`, `bwrap`, and `socat` are available
- backend imports resolve from repo root and `backend/`
- `docker compose ps` responds without provider failures

## If the error persists

If reload/rebuild does not restore access, the likely issue is outside the application source tree:

- VS Code remote file-system provider desynchronized
- Codespaces mount failure
- dev-container session corruption
- editor extension host failure

At that point, collect:

- screenshot or copy of the exact `ENOPRO` error
- whether Explorer still shows the repository contents
- whether a fresh Codespace/container has the same issue
- whether non-workspace folders open normally

## Why this repo includes extra checks

The repo now includes sandbox prerequisite checks in:

- `scripts/dev-doctor.sh`
- `scripts/codespace-health.sh`

Those checks validate tools frequently needed by the editor sandbox (`rg`, `bwrap`, `socat`) and verify backend importability from both repo root and backend working directory.
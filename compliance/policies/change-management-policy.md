# Change Management Policy

| Field | Value |
|---|---|
| Policy ID | CMP-001 |
| Version | 1.0 |
| Effective Date | March 9, 2026 |
| Owner | CTO |

## Scope

All infrastructure, application, database, and configuration changes affecting FusionEMS environments.

## Change Types

- **Standard**: low-risk, repeatable, pre-approved patterns
- **Normal**: requires peer review and formal approvals
- **Emergency**: expedited change for security/availability restoration

## Approval Model

- Standard: automated controls + required CI success
- Normal: PR review + CODEOWNERS + green checks
- Emergency: Incident Commander/CTO approval, post-change review required

## Required Gates

- Ruff/pytest for backend
- Typecheck/lint/tests/build for frontend
- Checkov/TFLint/Terraform validate for infra
- Migration safety checks

## Rollback

- ECS revision rollback
- Terraform controlled rollback/remediation
- DB recovery procedures via backups/snapshots

## Evidence

- PR history and approvals
- CI run artifacts
- Change calendar / release notes
- Emergency change retrospective records

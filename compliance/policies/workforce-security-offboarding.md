# Workforce Security and Offboarding Procedure

| Field | Value |
|---|---|
| Policy ID | WSO-001 |
| Version | 1.0 |
| Effective Date | March 9, 2026 |
| Owner | Security Officer |

## Hiring and Onboarding Controls

- Background check (where legally permitted)
- NDA and confidentiality agreement
- Role-appropriate least-privilege access only
- HIPAA/security training completion before PHI access

## Role Change Controls

- Access review within 24 hours of role change
- Remove obsolete permissions before granting new elevated access
- Update ownership/delegation for operational artifacts

## Offboarding Checklist

### Same Day (mandatory)

- Disable Cognito account and revoke active sessions
- Revoke GitHub org/repo access
- Disable email and SSO accounts
- Revoke VPN/remote tooling access
- Collect company assets/tokens where applicable

### Within 24 Hours

- Remove from Slack/monitoring/on-call/vendor consoles
- Validate IAM/OIDC role access removed
- Review recent audit logs for anomalous activity

### Within 7 Days

- Complete final access certification
- Archive offboarding evidence package

## Emergency Termination

Immediate lockout first, investigation second. Preserve forensic evidence and notify Security Officer + legal/HR as required.

## Evidence

- Signed offboarding checklist
- Access revocation logs
- Account disable timestamps
- Final certification record

# Risk Register (Starter Set)

| Field | Value |
|---|---|
| Policy ID | RR-001 |
| Version | 1.0 |
| Effective Date | March 9, 2026 |
| Owner | Security Officer |

## Active Risks

| ID | Category | Risk | L | I | Score | Current Controls | Residual | Treatment | Owner | Next Review |
|---|---|---|---:|---:|---:|---|---|---|---|---|
| R-001 | Access | Unauthorized PHI access | 3 | 5 | 15 | Cognito MFA, OPA RBAC, tenant isolation | High | Mitigate | Security Officer | 2026-04-01 |
| R-002 | Malware | Ransomware in workloads | 2 | 5 | 10 | Immutable images, ECR scan, backups | Med | Mitigate | CTO | 2026-04-01 |
| R-003 | Availability | AWS region outage | 2 | 5 | 10 | Multi-AZ, DR env, backup copies | Med | Mitigate | CTO | 2026-04-01 |
| R-004 | Isolation | Cross-tenant data leakage | 2 | 5 | 10 | OPA + tenant scoped queries | Med | Mitigate | Eng Lead | 2026-04-01 |
| R-005 | Insider | Privileged misuse | 2 | 4 | 8 | Audit logs, access reviews | Med | Mitigate | Security Officer | 2026-04-01 |
| R-006 | Network | DDoS/API abuse | 3 | 4 | 12 | WAF, rate limits, autoscaling | Med | Mitigate | DevOps | 2026-04-01 |
| R-007 | Vendor | Stripe/Telnyx compromise | 2 | 4 | 8 | Vendor due diligence, key rotation | Med | Transfer/Mitigate | CTO | 2026-04-01 |
| R-008 | Storage | S3 misconfiguration | 2 | 5 | 10 | Block public access, Config rules | Med | Mitigate | DevOps | 2026-04-01 |
| R-009 | PKI | Expired cert outage | 2 | 4 | 8 | ACM auto-renew + alarms | Low | Mitigate | DevOps | 2026-04-01 |
| R-010 | Vuln | Unpatched container CVEs | 3 | 4 | 12 | ECR/Inspector, SLA policy | Med | Mitigate | Eng Lead | 2026-04-01 |
| R-011 | AppSec | SQL injection | 2 | 5 | 10 | ORM, validation, tests | Med | Mitigate | Backend Lead | 2026-04-01 |
| R-012 | Identity | Credential stuffing | 3 | 4 | 12 | MFA, lockout, WAF rules | Med | Mitigate | Security Officer | 2026-04-01 |
| R-013 | Secrets | API key exposure | 2 | 5 | 10 | Secrets Manager, scans, no static keys | Med | Mitigate | CTO | 2026-04-01 |
| R-014 | Data Loss | Accidental destructive action | 2 | 4 | 8 | Backups, change control, review | Low | Mitigate | DevOps | 2026-04-01 |
| R-015 | Compliance | HIPAA control failure | 2 | 5 | 10 | Policy set, evidence cadence | Med | Mitigate | Security Officer | 2026-04-01 |
| R-016 | DR | Natural disaster in primary region | 2 | 4 | 8 | DR env and backup replication | Low | Mitigate | CTO | 2026-04-01 |
| R-017 | AI | Hallucinated AI output persisted | 3 | 3 | 9 | Human review, deterministic fallbacks | Med | Mitigate | Product/Eng | 2026-04-01 |
| R-018 | Fraud | Billing fraud/charge manipulation | 2 | 4 | 8 | Audit trails, role separation | Low | Mitigate | Billing Lead | 2026-04-01 |
| R-019 | DNS | Domain/DNS hijack | 2 | 5 | 10 | Route53 controls, IAM hardening | Med | Mitigate | DevOps | 2026-04-01 |
| R-020 | People | Key personnel departure | 3 | 3 | 9 | Runbooks, cross-training | Med | Mitigate | CTO | 2026-04-01 |
| R-021 | Logging | Log tampering attempt | 2 | 4 | 8 | CloudTrail + immutable audit stores | Low | Mitigate | Security Officer | 2026-04-01 |
| R-022 | Backup | Backup/restore failure | 2 | 5 | 10 | Backup policy + restore drills | Med | Mitigate | DevOps | 2026-04-01 |
| R-023 | Supply chain | Dependency compromise | 3 | 4 | 12 | Dependabot, pinning, scans | Med | Mitigate | Eng Lead | 2026-04-01 |
| R-024 | Social engineering | Employee phishing success | 3 | 4 | 12 | Training + simulations | Med | Mitigate | Security Officer | 2026-04-01 |
| R-025 | Governance | Untracked console drift | 3 | 3 | 9 | Config + IaC-only policy | Med | Mitigate | DevOps | 2026-04-01 |

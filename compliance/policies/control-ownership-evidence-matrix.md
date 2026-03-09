# Control Ownership & Evidence Matrix

| Control ID | Control | Owner | Evidence Source | Review Frequency | Approval Authority |
|---|---|---|---|---|---|
| C-001 | Identity and MFA enforcement | Security Officer | Cognito config export, access logs | Quarterly | Security Officer |
| C-002 | RBAC + OPA authorization | Engineering Lead | OPA policies, authz test evidence | Quarterly | CTO |
| C-003 | Tenant isolation | Engineering Lead | Integration tests, query scope checks | Quarterly | CTO |
| C-004 | Encryption at rest | DevOps Lead | Terraform state, KMS key config | Quarterly | Security Officer |
| C-005 | Encryption in transit | DevOps Lead | ALB/ACM config evidence | Quarterly | Security Officer |
| C-006 | CloudTrail audit coverage | DevOps Lead | Trail ARN, log bucket policy, alarm status | Monthly | Security Officer |
| C-007 | Threat detection (GuardDuty) | Security Officer | Detector status, triage records | Monthly | Security Officer |
| C-008 | Config compliance monitoring | DevOps Lead | AWS Config recorder/rule compliance reports | Monthly | Security Officer |
| C-009 | Findings aggregation (Security Hub) | Security Officer | Standards subscription status, findings exports | Monthly | Security Officer |
| C-010 | Backup + restore readiness | DevOps Lead | Backup plans, restore drill logs | Monthly | CTO |
| C-011 | Vulnerability scanning lifecycle | Security Officer | Inspector/ECR/Checkov reports | Weekly | CTO |
| C-012 | Incident response readiness | Security Officer | IR tabletop evidence, incident logs | Quarterly | CEO |
| C-013 | Breach notification readiness | Privacy Officer | Breach procedure records | Quarterly | CEO |
| C-014 | Vendor and BAA governance | Security Officer | Vendor register, BAA register | Quarterly | CEO |
| C-015 | Workforce onboarding/offboarding | Security Officer | Access change logs, offboarding checklists | Monthly | Security Officer |
| C-016 | Security awareness training | Security Officer | Completion reports, phishing drills | Quarterly | Security Officer |
| C-017 | Change management controls | CTO | PR approvals, CI gates, release evidence | Monthly | CTO |
| C-018 | Logging and observability | DevOps Lead | CloudWatch/Grafana dashboards, alert history | Monthly | CTO |
| C-019 | Data retention and disposal | Security Officer | Disposal logs, lifecycle policy evidence | Quarterly | Security Officer |
| C-020 | Privacy/DSAR operations | Privacy Officer | DSAR register, response evidence | Quarterly | Privacy Officer |

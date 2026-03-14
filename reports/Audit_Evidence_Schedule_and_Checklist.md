# FusionEMS Audit Evidence Schedule and Formal Readiness Checklist

This document operationalizes the compliance architecture. It dictates exactly *what* must be collected, *when* it must be collected, and *how* to prove the implementation of the Policy Framework against SOC 2, ISO 27001/27701, and HIPAA protocols.

## Part 1: Automated Continuous Evidence (AWS Audit Manager)
These items DO NOT require human collection. They are continuously vacuumed into the `fusionems-prod-audit-evidence-[id]` S3 bucket via the Audit Manager module and AWS Config rules.

| Control Area | Automated Source | Evidence Provided |
| :--- | :--- | :--- |
| **Data Encryption at Rest** | AWS Config (`encrypted-volumes`, `rds-storage-encrypted`) | Snapshots of KMS keys tied to all production data stores. |
| **Data Encryption in Transit** | AWS Security Hub (CIS / PCI standards) | Proof that ALB/API Gateways reject HTTP and only allow TLS 1.2+. |
| **Log Immutability** | AWS Config | Confirmation CloudTrail Multi-Region is ON and Vault Lock isn't modified. |
| **Change Management CI/CD** | GitHub Actions Logs via API integration | Proof that Checkov/Terraform PRs require explicit approvals before merging to `main`. |
| **Vulnerability Scanning** | Amazon Inspector / ECR | Live registries of patched vs unpatched CVEs across the container fleet. |

---

## Part 2: Human/Manual Evidence Artifact Schedule (The Calendar)
These tasks require scheduled, formal human execution and screenshot capturing.

### 📅 Weekly Tasks
- [ ] **Infrastructure Vulnerability Review:** DevSecOps review of non-critical Amazon Inspector findings and Trivy alerts.
- [ ] **Code Dependency Review:** Review output of `safety` and `dependabot` checks. 

### 📅 Monthly Tasks
- [ ] **Access Deprovisioning Check:** Validate that 100% of employees terminated in the past 30 days had their AWS SSO / Okta access revoked within 24 hours (screenshot of ticketing system vs Okta logs).
- [ ] **AWS Billing Anomaly Review:** FinOps / CISO reviews billing for unexpected spikes indicating compromised compute access.
- [ ] **WAF & Security Hub Tuning:** Review GuardDuty and WAF logs; tweak rules to eliminate false positives.

### 📅 Quarterly Tasks
- [ ] **IAM Full Access Review:** Export all AWS IAM Users, Identity Center Groups, and DB Roles. System owners MUST sign off on every granted permission. Documented in Jira/Linear. *(Required for SOC 2 CC6.2)*
- [ ] **Disaster Recovery Test:** Execute a manual restore of the Production RDS database to the Staging VPC using AWS Backup. Document time taken (RTO). *(Required for HIPAA 164.308(a)(7))*
- [ ] **Phishing Simulation / Training Audit:** Ensure 100% of new hires completed HIPAA and Security awareness training within their first 30 days. Execute one company-wide phishing test.

### 📅 Annual Tasks
- [ ] **Formal Penetration Test:** Engage a 3rd-party independent security firm to run external/internal networking and application layer testing. Obtain the remediation report. 
- [ ] **Information Security Risk Assessment:** Conduct the formal Risk Assessment matrix updates (Policy A.08). *(Required for ISO 27001)*
- [ ] **Policy Review:** CISO and Management review and sign-off on Policies A.01 through A.09.
- [ ] **Tabletop Incident Response Exercise:** Walk through a simulated data breach/ransomware scenario with key executives. Document the results and lessons learned.

---

## Part 3: Go-Live Readiness (Day 1 SOC 2 Type I Checklist)
Before spinning up the formal Audit Observation Window for SOC 2 Type I or ISO 27001 Stage 1, the following must be physically complete:
- [ ] Terraform applied with God-Mode architecture in Production.
- [ ] 100% of Policies explicitly approved and distributed to workforce.
- [ ] MDM rolled out to all developer laptops (FileVault + EDR active).
- [ ] Initial Penetration Test concluded with all Critical/High findings completely patched.
- [ ] BAA specifically signed with Amazon Web Services via AWS Artifact.

*Maintained by the FusionEMS DevSecOps & Governance Division.*

# A.02 Access Control & Identity Policy

## 1. Purpose
This policy enforces Zero Trust architecture principles by restricting physical and logical access to FusionEMS networks, infrastructure, applications, and PHI/PII data. It enforces the Principle of Least Privilege and Need-to-Know.

## 2. Workforce Access Controls
1. **SSO and MFA Authentication:** All access to corporate applications, source code (GitHub), and infrastructure (AWS) MUST be gated by Single Sign-On (SSO) acting as an Identity Provider (IdP) with mandatory Hardware/App-based Multi-Factor Authentication (MFA). SMS MFA is expressly prohibited.
2. **Role-Based Access Control (RBAC):** Privileges are assigned to roles, not individual accounts. Access must be approved by a system owner.
3. **Just-In-Time (JIT) Access:** Persistent admin access is prohibited. Elevated privileges must be strictly time-bound and explicitly acquired through a documented approval process.
4. **Access Reviews:** Formal, documented recertification of all system and DB access rolls MUST occur completely at least every 90 days.

## 3. System and Application Access
1. **No Shared Accounts:** All service and human accounts must be distinctly attributable.
2. **OIDC over Long-Lived Credentials:** All workload-to-workload communication and CI/CD pipelines (e.g. GitHub Actions to AWS) MUST use short-lived OIDC tokens. Long-lived static AWS access keys are globally disallowed.
3. **Database Access:** Direct connectivity to Production databases from developer workstations is blocked via networking. Access happens exclusively via Bastion hosts logged entirely by AWS Systems Manager Session Manager, utilizing short-lived AWS IAM DB Tokens rather than static passwords.

## 4. Termination of Employment
All digital access must be revoked systematically on the day of off-boarding via the centralized IdP. 

## 5. Framework Mappings
- **ISO 27001:** Clause A.9 (Access Control)
- **SOC 2:** CC6.1 - CC6.3 (Logical and Physical Access)
- **HIPAA:** 164.312(a)(1) (Access Control), 164.312(d) (Person or Entity Authentication)

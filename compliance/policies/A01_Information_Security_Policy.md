# A.01 Information Security Policy

## 1. Purpose and Scope
This policy establishes the Information Security Management System (ISMS) for FusionEMS, ensuring the secure operation of all systems in compliance with SOC 2 Type II, ISO 27001, and HIPAA Security Rules.

## 2. Roles and Responsibilities
- **Chief Information Security Officer (CISO):** Ultimate accountability for the ISMS.
- **Engineering / DevSecOps:** Implementing security controls in code (Terraform, Config).
- **All Employees:** Adherence to security guidelines, acceptable use, and breach reporting.

## 3. Policy Statements
1. **Zero Trust Architecture:** All services must verify identity via OIDC/SSO (AWS Identity Center). None shall assume trust implicitly.
2. **Infrastructure as Code:** All infrastructure changes MUST be defined in Terraform, peer-reviewed, and deployed via CI/CD.
3. **Data Protection:** All PHI/PII must be encrypted at rest utilizing hardware-backed KMS (FIPS-140-2) and in transit utilizing TLS 1.3.
4. **Continuous Compliance:** AWS Audit Manager, Config, and Security Hub shall be utilized to gather real-time continuous evidence.
5. **Auditing and Logging:** Multi-region CloudTrail will be enabled and logs made immutable.

## 4. Framework Mappings
- **ISO 27001:** Clause 5.1 (Management Commitment), A.5 (Information Security Policies)
- **SOC 2:** CC1.1, CC1.2
- **HIPAA:** 164.308(a)(1) (Security Management Process)

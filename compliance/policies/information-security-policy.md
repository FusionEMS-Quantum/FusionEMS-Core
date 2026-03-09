# Information Security Policy

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Policy ID**      | ISP-001                                    |
| **Version**        | 1.0                                        |
| **Effective Date** | March 9, 2026                              |
| **Review Cadence** | Annual                                     |
| **Next Review**    | March 9, 2027                              |
| **Owner**          | Security Officer                           |
| **Approved By**    | Security Officer, CEO — FusionEMS Quantum  |
| **Classification** | INTERNAL                                   |

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Scope](#2-scope)
3. [Definitions](#3-definitions)
4. [Roles and Responsibilities](#4-roles-and-responsibilities)
5. [Security Principles](#5-security-principles)
6. [Risk Management](#6-risk-management)
7. [Compliance Frameworks](#7-compliance-frameworks)
8. [Security Controls](#8-security-controls)
9. [Policy Governance](#9-policy-governance)
10. [Enforcement and Sanctions](#10-enforcement-and-sanctions)
11. [Related Policies](#11-related-policies)
12. [Revision History](#12-revision-history)

---

## 1. Purpose

This Information Security Policy establishes the security governance framework for FusionEMS Quantum ("the Organization") and its FusionEMS platform. FusionEMS is a mission-critical, multi-tenant public safety SaaS platform supporting Emergency Medical Services (EMS), Helicopter Emergency Medical Services (HEMS), Fire, electronic Patient Care Reporting (ePCR), Computer-Aided Dispatch (CAD), Fleet Management, Revenue Cycle Management / Billing, Mobile Data Terminals (MDT), and AI-powered Analytics.

The purpose of this policy is to:

- Protect the confidentiality, integrity, and availability of all information assets, including Protected Health Information (PHI) and Personally Identifiable Information (PII).
- Establish a security-first culture across all business functions.
- Define roles, responsibilities, and accountability for information security.
- Ensure compliance with applicable laws, regulations, and contractual obligations.
- Provide a foundation for the Organization's complete policy library.

## 2. Scope

### 2.1 Systems

This policy applies to all information systems owned, operated, or managed by FusionEMS Quantum, including but not limited to:

- **FusionEMS Backend**: Python/FastAPI services running on AWS ECS Fargate, including all API endpoints, background workers, and scheduled tasks.
- **FusionEMS Frontend**: Next.js/TypeScript web application served via AWS CloudFront and Application Load Balancer.
- **Data Stores**: Amazon RDS (PostgreSQL), Amazon ElastiCache (Redis), Amazon S3 buckets (document storage, audit logs, exports, NEMSIS submissions).
- **Identity and Access Management**: AWS Cognito user pools, OPA (Open Policy Agent) policy engine, JWT-based session management.
- **Infrastructure**: All AWS resources provisioned via Terraform across development, staging, and production environments, including VPC, ECS, ALB, WAF, Route53, CloudWatch, KMS, Secrets Manager, GuardDuty, Security Hub, Inspector, and Macie.
- **AI/ML Systems**: AI analytics modules, including any models processing patient or operational data.
- **Monitoring and Observability**: OpenTelemetry (OTel) collector, Prometheus, Grafana dashboards, CloudWatch Logs and Alarms.
- **CI/CD Pipeline**: GitHub Actions, container image builds, ECR repositories, automated deployment pipelines.
- **Communication Systems**: Corporate email, Slack, and any third-party integrations (Telnyx for telephony, Stripe for billing).

### 2.2 Personnel

This policy applies to:

- All full-time and part-time employees of FusionEMS Quantum.
- All contractors, consultants, and temporary workers with access to FusionEMS systems or data.
- All third-party vendors and business associates with access to PHI or system resources.
- All users of the FusionEMS platform in administrative or development roles.

### 2.3 Data

This policy applies to all data created, received, maintained, or transmitted by FusionEMS systems, regardless of format or storage medium. This explicitly includes PHI, PII, financial data, operational data, audit logs, source code, infrastructure configurations, and encryption keys.

## 3. Definitions

| Term | Definition |
|------|-----------|
| **PHI** | Protected Health Information as defined by HIPAA — individually identifiable health information, including ePCR records, patient demographics, vitals, treatment data, and billing claims. |
| **PII** | Personally Identifiable Information — any data that can identify an individual, including names, addresses, dates of birth, Social Security Numbers, and contact information. |
| **Tenant** | An EMS agency, fire department, or healthcare organization subscribing to the FusionEMS platform. Each tenant operates in logical isolation within the multi-tenant architecture. |
| **Break-Glass Access** | Emergency administrative access granted via the SupportAccessGrant model when normal access controls must be temporarily bypassed for incident response. |
| **Founder Role** | The highest-privilege role in FusionEMS, reserved for platform owners with full administrative authority across all tenants. |
| **Security Incident** | Any event that compromises or threatens the confidentiality, integrity, or availability of information assets. |

## 4. Roles and Responsibilities

### 4.1 Security Officer

The Security Officer holds ultimate accountability for the information security program. Responsibilities include:

- Maintaining and updating the complete policy library.
- Overseeing risk assessments and treatment plans.
- Coordinating incident response and breach notification.
- Ensuring compliance with HIPAA, SOC 2, and other regulatory obligations.
- Reporting security posture to the CEO and Board quarterly.
- Approving access exceptions and managing the exception register.
- Coordinating annual penetration testing and vulnerability management.

### 4.2 Chief Technology Officer (CTO)

The CTO is responsible for:

- Technical implementation of security controls across all FusionEMS systems.
- Architecture decisions that impact security posture, including AWS service selection and configuration.
- Ensuring infrastructure-as-code (Terraform) reflects security policies.
- Overseeing the CI/CD pipeline security, including container image scanning (ECR Enhanced Scanning) and IaC scanning (Checkov).
- Approving technical exceptions to security standards.
- Ensuring security requirements are integrated into the software development lifecycle.

### 4.3 Engineering Team

All engineers are responsible for:

- Writing secure code following OWASP Top 10 mitigations.
- Applying strict typing (Python type hints, TypeScript strict mode) to reduce defect classes.
- Validating all external input using Pydantic models at service boundaries.
- Never committing secrets, credentials, or PHI to source control.
- Responding to Dependabot alerts and vulnerability findings within defined SLAs.
- Participating in security training and incident response exercises.

### 4.4 Operations / DevOps

Operations personnel are responsible for:

- Maintaining Terraform modules for all infrastructure with security best practices.
- Configuring and monitoring GuardDuty, Security Hub, Inspector, Macie, and CloudWatch alarms.
- Managing KMS key rotation, certificate lifecycle (ACM), and secrets rotation (Secrets Manager).
- Executing disaster recovery procedures and validating backup integrity.
- Enforcing network segmentation via VPC design (private subnets for data tier, public subnets for ALB only).

### 4.5 All Personnel

Every individual within scope of this policy must:

- Complete security awareness training within 30 days of onboarding and annually thereafter.
- Report suspected security incidents immediately to the Security Officer.
- Protect credentials and never share authentication tokens.
- Lock workstations when unattended.
- Comply with the Acceptable Use Policy (AUP-001) and all subordinate policies.

## 5. Security Principles

### 5.1 Confidentiality

Information shall be accessible only to authorized individuals with a legitimate need-to-know. FusionEMS enforces confidentiality through:

- Role-based access control (RBAC) via OPA policies evaluated on every API request.
- Tenant isolation enforced at the database query layer (agency_id scoping on all data models).
- Encryption of all data at rest using AWS KMS with automatic key rotation.
- Encryption of all data in transit using TLS 1.2 minimum (TLS 1.3 preferred on ALB).
- JWT tokens with 60-minute expiration and refresh token rotation.

### 5.2 Integrity

Information shall be accurate, complete, and protected from unauthorized modification. FusionEMS enforces integrity through:

- Immutable audit logs written to dedicated S3 buckets with Object Lock.
- Database transaction isolation and referential integrity constraints in PostgreSQL.
- Alembic-managed schema migrations with forward-only evolution.
- Code review requirements on all pull requests before merge.
- Container image signing and digest verification in ECR.

### 5.3 Availability

Information systems shall be available to authorized users when needed. Given FusionEMS supports 24/7 life-safety operations, availability is critical. Availability is ensured through:

- Multi-AZ deployment for all stateful services (RDS, ElastiCache, ECS).
- Auto-scaling ECS Fargate tasks based on CPU/memory metrics and request volume.
- Route53 health checks with automated failover.
- Defined Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO) per the Business Continuity / Disaster Recovery Plan (BCP-001).
- Redundant data paths and graceful degradation when non-critical services are impaired.

### 5.4 Defense in Depth

Security controls are layered across network, application, data, and identity tiers:

- **Network**: VPC with private subnets, Security Groups, NACLs, WAF on ALB.
- **Application**: Input validation (Pydantic), output encoding, CSRF protection, rate limiting.
- **Data**: KMS encryption, field-level encryption for sensitive attributes, S3 bucket policies.
- **Identity**: Cognito MFA, OPA policy evaluation, session management, privilege escalation controls.

### 5.5 Least Privilege

All access is granted on a deny-by-default basis. Users and services receive the minimum permissions necessary to perform their function. Privileged access (founder, agency_admin) requires additional authentication controls and is subject to quarterly review.

### 5.6 Zero Trust

FusionEMS operates on a zero-trust model. Every request is authenticated and authorized regardless of network origin. OIDC-based authentication via Cognito is the sole identity mechanism — no static API keys or shared secrets for human users.

## 6. Risk Management

### 6.1 Risk Assessment

FusionEMS Quantum conducts a formal risk assessment annually and upon significant system changes. The assessment:

- Identifies information assets, threats, and vulnerabilities.
- Evaluates likelihood and impact using a 5×5 risk matrix.
- Produces a risk register with assigned owners and treatment plans.
- Prioritizes risks to PHI and life-safety systems.

### 6.2 Risk Treatment

Identified risks are treated via one of four strategies:

- **Mitigate**: Implement controls to reduce likelihood or impact.
- **Accept**: Formally accept residual risk with Security Officer and CEO approval, documented in the risk register.
- **Transfer**: Shift risk via insurance, contractual terms, or BAAs.
- **Avoid**: Eliminate the activity or system that generates the risk.

### 6.3 Continuous Monitoring

Risk posture is continuously monitored through:

- AWS Security Hub aggregate findings.
- GuardDuty threat detection across all accounts.
- Macie PHI discovery scans on S3 buckets.
- Inspector runtime vulnerability scanning on ECS containers.
- Dependabot alerts on all code repositories.
- CloudWatch anomaly detection on key metrics.

## 7. Compliance Frameworks

FusionEMS Quantum maintains compliance with the following frameworks:

### 7.1 HIPAA (Health Insurance Portability and Accountability Act)

As a Business Associate handling PHI on behalf of Covered Entity customers, FusionEMS must comply with:

- **Privacy Rule**: Minimum necessary use and disclosure of PHI.
- **Security Rule**: Administrative, physical, and technical safeguards for ePHI.
- **Breach Notification Rule**: Timely notification of unsecured PHI breaches.
- **Business Associate Agreements (BAAs)**: In place with all customers and subprocessors (AWS, Telnyx, Stripe).

### 7.2 SOC 2 Type II

FusionEMS targets SOC 2 Type II attestation across all five Trust Services Criteria:

- **Security (CC)**: Common Criteria — foundational controls.
- **Availability (A)**: System uptime and recovery commitments.
- **Processing Integrity (PI)**: Accurate and complete data processing.
- **Confidentiality (C)**: Protection of confidential information.
- **Privacy (P)**: Personal information lifecycle management.

### 7.3 ISO 27001 Alignment

While formal ISO 27001 certification is a future objective, FusionEMS aligns its ISMS structure with ISO 27001:2022 Annex A controls, including risk management methodology, control selection, and continuous improvement.

### 7.4 NIST Cybersecurity Framework

FusionEMS maps controls to the NIST CSF functions: Identify, Protect, Detect, Respond, Recover. This mapping supports customer due-diligence questionnaires and regulatory inquiries.

## 8. Security Controls

Security controls are documented across the subordinate policy library. Key control domains include:

| Domain | Governing Policy |
|--------|-----------------|
| Access Control | Access Control Policy (ACP-001) |
| Encryption | Encryption Policy (ENC-001) |
| Data Classification | Data Classification Policy (DCP-001) |
| Data Retention | Data Retention and Disposal Policy (DRD-001) |
| Vulnerability Management | Vulnerability Management Policy (VMP-001) |
| Incident Response | Incident Response Plan (IRP-001) |
| Breach Notification | Breach Notification Procedure (BNP-001) |
| Business Continuity | Business Continuity / DR Plan (BCP-001) |
| Acceptable Use | Acceptable Use Policy (AUP-001) |

## 9. Policy Governance

### 9.1 Policy Lifecycle

All policies in the FusionEMS security program follow this lifecycle:

1. **Drafting**: Policy owner creates or updates the policy with input from relevant stakeholders.
2. **Review**: Security Officer and CTO review for accuracy, completeness, and feasibility.
3. **Approval**: Security Officer and CEO approve the policy.
4. **Distribution**: Approved policy is published to the compliance repository and communicated to affected personnel.
5. **Acknowledgment**: Personnel acknowledge receipt and understanding.
6. **Review**: Policies are reviewed annually or upon significant changes to systems, regulations, or threat landscape.
7. **Retirement**: Obsolete policies are formally retired with documentation.

### 9.2 Annual Review

All policies are reviewed no later than 12 months from the last approval date. The review considers:

- Changes to the FusionEMS platform architecture.
- New regulatory requirements or updated guidance.
- Findings from audits, assessments, and incidents.
- Feedback from personnel and customers.

### 9.3 Exception Process

Exceptions to any security policy require:

1. Written request from the requestor documenting the business justification.
2. Risk assessment of the exception, including compensating controls.
3. Approval by the Security Officer (and CTO for technical exceptions).
4. Time-bound duration (maximum 12 months; must be re-evaluated).
5. Documentation in the exception register with periodic review.

Exceptions that impact PHI security require CEO approval in addition to the Security Officer.

### 9.4 Policy Repository

All approved policies are maintained in the `/compliance/policies/` directory of the FusionEMS-Core repository. Version control is managed via Git, providing a complete audit trail of all policy changes, approvals, and history.

## 10. Enforcement and Sanctions

### 10.1 Compliance Monitoring

Compliance with this policy and all subordinate policies is monitored through:

- Automated technical controls (OPA policy enforcement, IAM policy restrictions, WAF rules).
- Quarterly access reviews.
- Annual security awareness assessments.
- Internal audits and external SOC 2 examinations.

### 10.2 Violations

Violations of this policy or any subordinate policy may result in disciplinary action, up to and including:

- Verbal or written warning.
- Mandatory additional security training.
- Temporary or permanent revocation of system access.
- Termination of employment or contract.
- Civil or criminal legal action where applicable.

The severity of sanctions is proportional to the nature and impact of the violation, the individual's role, and whether the violation was intentional or negligent.

### 10.3 Reporting Violations

Personnel must report suspected policy violations to the Security Officer. The Organization prohibits retaliation against individuals who report security concerns in good faith.

## 11. Related Policies

- Acceptable Use Policy (AUP-001)
- Access Control Policy (ACP-001)
- Encryption Policy (ENC-001)
- Data Classification Policy (DCP-001)
- Data Retention and Disposal Policy (DRD-001)
- Vulnerability Management Policy (VMP-001)
- Incident Response Plan (IRP-001)
- Breach Notification Procedure (BNP-001)
- Business Continuity / Disaster Recovery Plan (BCP-001)

## 12. Revision History

| Version | Date           | Author           | Description          |
|---------|----------------|------------------|----------------------|
| 1.0     | March 9, 2026  | Security Officer | Initial release      |

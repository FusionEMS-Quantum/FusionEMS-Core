# Data Classification Policy

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Policy ID**      | DCP-001                                    |
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
3. [Classification Levels](#3-classification-levels)
4. [Classification Level Details](#4-classification-level-details)
5. [Data Ownership and Custodianship](#5-data-ownership-and-custodianship)
6. [Classification Procedure](#6-classification-procedure)
7. [Handling Requirements Matrix](#7-handling-requirements-matrix)
8. [FusionEMS Data Inventory](#8-fusionems-data-inventory)
9. [Third-Party Data Sharing](#9-third-party-data-sharing)
10. [Reclassification](#10-reclassification)
11. [Enforcement](#11-enforcement)
12. [Related Policies](#12-related-policies)
13. [Revision History](#13-revision-history)

---

## 1. Purpose

This Data Classification Policy establishes a framework for categorizing information assets based on their sensitivity, regulatory requirements, and business value. Proper classification ensures that data receives the appropriate level of protection throughout its lifecycle — from creation through disposal. As a healthcare SaaS platform processing Protected Health Information (PHI), FusionEMS must clearly distinguish data types and enforce handling requirements proportional to risk.

## 2. Scope

This policy applies to all data created, received, maintained, processed, or transmitted by FusionEMS Quantum systems, including:

- Data stored in AWS services (RDS, S3, ElastiCache, CloudWatch Logs).
- Data processed by FusionEMS backend services (FastAPI, Celery workers).
- Data displayed in the FusionEMS frontend (Next.js web application).
- Data transmitted to or from external systems (Telnyx, Stripe, NEMSIS state systems).
- Code, infrastructure configurations, and internal documentation.
- Physical documents, if any.

All personnel, contractors, and third parties with access to FusionEMS data must apply this classification scheme.

## 3. Classification Levels

FusionEMS Quantum defines four classification levels, ordered from least to most sensitive:

| Level | Label | Color Code | Description |
|-------|-------|-----------|-------------|
| 1 | **PUBLIC** | 🟢 Green | Information intended for public disclosure |
| 2 | **INTERNAL** | 🔵 Blue | Information for internal use that is not sensitive |
| 3 | **CONFIDENTIAL** | 🟡 Yellow | Sensitive business information requiring protection |
| 4 | **RESTRICTED / PHI** | 🔴 Red | Highly sensitive data subject to regulatory requirements |

When in doubt, classify at the higher level and consult the Security Officer.

## 4. Classification Level Details

### 4.1 PUBLIC (Level 1)

**Definition**: Information that is intended for unrestricted distribution and poses no risk to FusionEMS Quantum, its customers, or patients if disclosed.

**Examples**:

- Marketing materials, press releases, and blog posts.
- Public-facing website content (fusionems.com).
- Public API documentation and developer guides.
- Published pricing information.
- Job postings and recruiting materials.
- Open-source software components with appropriate licensing.
- Published compliance certifications (SOC 2 Type II report summary, not the full report).

**Handling Requirements**:

| Control | Requirement |
|---------|------------|
| Encryption at rest | Recommended (S3 default encryption) |
| Encryption in transit | Required (TLS 1.2+) |
| Access control | No restrictions beyond standard web access |
| Storage | Public S3 buckets (CloudFront) or public website hosting |
| Sharing | No restrictions |
| Labeling | Not required |
| Retention | Per content management schedule |
| Disposal | Standard deletion; no special procedures |

### 4.2 INTERNAL (Level 2)

**Definition**: Information intended for use within FusionEMS Quantum that is not publicly available but does not contain sensitive personal, financial, or health data. Unauthorized disclosure would cause minimal harm.

**Examples**:

- Internal procedures, runbooks, and operational documentation (e.g., RUNBOOK_BILLING.txt, RUNBOOK_TELNYX.txt).
- Architecture diagrams and technical design documents.
- Source code (FusionEMS-Core repository).
- Internal meeting notes that do not contain PHI or confidential business data.
- Non-sensitive project plans and roadmaps.
- Employee directory (name, title, team).
- Compliance policy documents (this document library).
- Terraform module structure and non-secret configuration.
- OPA policy definitions.
- Grafana dashboard configurations and Prometheus scrape configs.
- OpenTelemetry (OTel) configuration files.

**Handling Requirements**:

| Control | Requirement |
|---------|------------|
| Encryption at rest | Required (KMS) |
| Encryption in transit | Required (TLS 1.2+) |
| Access control | Authenticated FusionEMS personnel only |
| Storage | Private GitHub repository, private S3 buckets, internal documentation systems |
| Sharing | Within FusionEMS Quantum personnel; NDA required for external sharing |
| Labeling | Not required but encouraged on documents |
| Retention | Per information type; source code retained indefinitely in Git |
| Disposal | Standard deletion with confirmation |

### 4.3 CONFIDENTIAL (Level 3)

**Definition**: Sensitive business information that, if disclosed without authorization, could cause material harm to FusionEMS Quantum, its competitive position, financial interests, or business relationships. This includes most business operations data.

**Examples**:

- Business financials, revenue projections, and investor materials.
- Customer contracts, pricing agreements, and SLAs.
- Vendor contracts and third-party agreements.
- Tenant (agency) configuration data: agency names, subscription tiers, feature flags, integration endpoints.
- Employee compensation, performance reviews, and HR records.
- Security assessment results, penetration test reports, and vulnerability scan findings.
- The full SOC 2 Type II audit report.
- Stripe configuration, subscription metadata, and payment processing rules.
- AWS account IDs, resource ARNs, and infrastructure details beyond public facing.
- Incident response documentation and post-incident reviews.
- Internal financial records: billing claims metadata (not PHI-containing claim details), agency billing summaries.
- Secrets Manager configuration (not the secret values themselves).
- Board meeting minutes.

**Handling Requirements**:

| Control | Requirement |
|---------|------------|
| Encryption at rest | Required (dedicated KMS CMK) |
| Encryption in transit | Required (TLS 1.2+) |
| Access control | Need-to-know basis; role-based restrictions via OPA |
| Storage | Encrypted S3 buckets with restricted bucket policies; encrypted database tables; private repositories with branch protection |
| Sharing | Authorized personnel only; NDA and Security Officer approval for external sharing |
| Labeling | Required on formal documents (header or footer marking) |
| Retention | Per data type; financial records 7 years; contracts through term + 3 years |
| Disposal | Secure deletion with documented evidence |

### 4.4 RESTRICTED / PHI (Level 4)

**Definition**: The most sensitive information class. Includes all Protected Health Information (PHI) as defined by HIPAA, Personally Identifiable Information (PII) that could cause significant harm if disclosed, and data subject to the most stringent regulatory requirements. Unauthorized disclosure could result in regulatory penalties, legal liability, or harm to individuals.

**Examples**:

- **Patient demographics**: name, date of birth, address, phone, email, Social Security Number, insurance identifiers.
- **ePCR records**: patient care reports, medical histories, assessments, treatments, medications administered, vital signs (heart rate, blood pressure, SpO2, EtCO2, temperature), clinical impressions, narrative notes.
- **Billing claims**: CMS-1500 claim data, ICD-10 codes, CPT codes, insurance information, remittance data, EOBs, patient financial responsibility.
- **NEMSIS submissions**: National EMS Information System data packages containing full patient encounter data submitted to state health departments.
- **Patient vitals streams**: Real-time vitals data from cardiac monitors, pulse oximeters, and other medical devices transmitted via MDT.
- **Dispatch/CAD data**: Incident details including patient location, nature of emergency, caller information.
- **ePCR signatures**: Patient and provider digital signatures on PCR documents.
- **Medication records**: Controlled substance administration logs, DEA-related data.
- **AI analytics input/output**: Any model input or output containing or derived from patient data.
- **Authentication credentials**: Cognito user pool secrets, KMS key material, Secrets Manager values, database passwords.
- **Audit logs containing PHI**: API request logs that capture patient identifiers in URL parameters or request bodies.

**Handling Requirements**:

| Control | Requirement |
|---------|------------|
| Encryption at rest | Required (dedicated KMS CMK with annual rotation; field-level encryption for SSN and other high-sensitivity fields) |
| Encryption in transit | Required (TLS 1.2+ minimum, TLS 1.3 preferred) |
| Access control | Strict RBAC via OPA; minimum necessary principle; tenant isolation mandatory; MFA required for all accessors |
| Storage | RDS with encryption; S3 with KMS and restricted bucket policies; never in logs, error messages, or URLs |
| Sharing | Only via authorized platform functions; BAA required for third-party sharing; no email, Slack, or unencrypted channels |
| Labeling | Required; database fields and S3 objects classified in data inventory |
| Retention | Minimum 7 years per state requirements (see DRD-001); patient may request copies per HIPAA right of access |
| Disposal | Crypto-shred via KMS key rotation/deletion; documented in disposal log; certificate of destruction for physical media |

## 5. Data Ownership and Custodianship

### 5.1 Data Owners

| Data Domain | Owner | Classification Authority |
|------------|-------|------------------------|
| Patient/Clinical Data | Agency Medical Director (per tenant) | Security Officer determines classification level |
| Billing/Financial Data | Billing Operations Lead | Security Officer determines classification level |
| Employee HR Data | HR Manager | Security Officer determines classification level |
| Source Code | CTO | CTO determines classification level |
| Infrastructure Configuration | CTO | CTO + Security Officer joint authority |
| Security/Compliance Data | Security Officer | Security Officer determines classification level |
| Marketing/Public Content | Marketing Lead | Marketing Lead with Security Officer review |

### 5.2 Data Custodians

Data custodians are responsible for implementing the technical controls required by the data's classification level. At FusionEMS, custodianship is aligned with the service layer:

- **Engineering Team**: Custodians of application-tier data (ePCR records, billing claims, user accounts) — responsible for access control logic, input validation, audit logging.
- **DevOps/Infrastructure**: Custodians of infrastructure-tier data (database backups, log archives, encryption keys) — responsible for storage encryption, backup integrity, key management.
- **Security Officer**: Custodian of compliance evidence, audit reports, and security assessment results.

## 6. Classification Procedure

### 6.1 New Data Elements

When a new data element is introduced to FusionEMS (new database field, new API endpoint, new integration):

1. The data element owner identifies the data type and sensitivity.
2. The owner proposes a classification level based on this policy's definitions.
3. The Security Officer reviews and confirms the classification.
4. The classification is recorded in the data inventory (Section 8).
5. Technical controls corresponding to the classification level are implemented before the data element enters production.

### 6.2 Bulk Data

When datasets contain elements of different classification levels, the entire dataset is classified at the highest level present. For example:

- An ePCR export file containing patient names and vital signs is RESTRICTED/PHI, even if it also contains non-sensitive metadata.
- A tenant configuration export containing agency names (CONFIDENTIAL) alongside agency_id (INTERNAL) is classified as CONFIDENTIAL.

### 6.3 Derived Data

Data derived from higher-classification data inherits the higher classification unless:

- The derivation process produces truly de-identified output per HIPAA Safe Harbor de-identification standards (18 identifier categories removed).
- The Security Officer has reviewed and approved the de-identification methodology.
- The de-identification is documented and the output is reclassified with a formal reclassification record.

## 7. Handling Requirements Matrix

| Handling Aspect | PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED/PHI |
|----------------|--------|----------|--------------|---------------|
| **Storage encryption** | Recommended | KMS required | Dedicated CMK | Dedicated CMK + field-level for sensitive subfields |
| **Transit encryption** | TLS 1.2+ | TLS 1.2+ | TLS 1.2+ | TLS 1.2+ (1.3 preferred) |
| **Access model** | Public | Authenticated personnel | Need-to-know RBAC | Minimum necessary RBAC + MFA |
| **Logging** | Standard | Standard | Enhanced (who accessed what, when) | Full audit trail (HIPAA audit log requirements) |
| **Backup** | Standard | Standard | Encrypted backups with restricted access | Encrypted backups, tested restores, cross-region |
| **Sharing (internal)** | Unrestricted | FusionEMS personnel | Need-to-know, labeled | Minimum necessary, audit-logged |
| **Sharing (external)** | Unrestricted | NDA required | NDA + Security Officer approval | BAA required + Security Officer approval + encrypted channel |
| **Email** | Permitted | Permitted | Encrypted email or secure link | Prohibited (use platform export functions only) |
| **Printing** | Permitted | Minimize | Approved purpose only, secure shred | Prohibited unless regulatory requirement; secure shred |
| **Personal devices** | Permitted (view) | View only (no download) | No access from personal devices without MDM | Prohibited on personal devices |
| **Retention** | Content schedule | Type-dependent | 7 years (financial); contract term + 3 years | 7 years minimum (state dependent) |
| **Disposal method** | Standard delete | Standard delete | Secure delete + confirmation | Crypto-shred + disposal certificate |

## 8. FusionEMS Data Inventory

The following table provides a representative inventory of key FusionEMS data elements and their classifications. This inventory is maintained by the Security Officer and reviewed annually.

### 8.1 Patient/Clinical Domain

| Data Element | Storage | Classification | Retention |
|-------------|---------|----------------|-----------|
| Patient demographics (name, DOB, address, SSN) | RDS `patients` table | RESTRICTED/PHI | 7 years |
| ePCR records (assessment, treatment, narrative) | RDS `epcr_records` table | RESTRICTED/PHI | 7 years |
| Vital signs (HR, BP, SpO2, EtCO2, temp) | RDS `vitals` table | RESTRICTED/PHI | 7 years |
| Medication administration logs | RDS `medications` table | RESTRICTED/PHI | 7 years |
| Patient signatures (digital) | S3 documents bucket | RESTRICTED/PHI | 7 years |
| Incident/dispatch records | RDS `incidents` table | RESTRICTED/PHI | 7 years |
| NEMSIS XML submissions | S3 NEMSIS bucket | RESTRICTED/PHI | 7 years |
| AI analytics (patient-derived) | RDS/S3 as applicable | RESTRICTED/PHI | 7 years |

### 8.2 Billing/Financial Domain

| Data Element | Storage | Classification | Retention |
|-------------|---------|----------------|-----------|
| Billing claims (CMS-1500, diagnosis codes) | RDS `billing_claims` table | RESTRICTED/PHI | 7 years |
| Insurance information | RDS `insurance` table | RESTRICTED/PHI | 7 years |
| Payment records (Stripe references) | RDS `payments` table | CONFIDENTIAL | 7 years |
| Agency billing summaries (no patient data) | RDS `billing_summaries` table | CONFIDENTIAL | 7 years |
| Stripe webhook events | RDS `stripe_events` table | CONFIDENTIAL | 3 years |

### 8.3 Operational Domain

| Data Element | Storage | Classification | Retention |
|-------------|---------|----------------|-----------|
| Agency (tenant) configuration | RDS `agencies` table | CONFIDENTIAL | Life of tenant |
| User accounts (name, email, role) | Cognito + RDS `users` table | CONFIDENTIAL | Life of account + 7 years |
| Fleet/vehicle data | RDS `fleet` table | INTERNAL | Life of asset + 1 year |
| Crew assignments and schedules | RDS `crew_schedules` table | INTERNAL | 3 years |
| Compliance pack configurations | RDS/S3 | INTERNAL | Life of pack |

### 8.4 Infrastructure/Technical Domain

| Data Element | Storage | Classification | Retention |
|-------------|---------|----------------|-----------|
| Application source code | GitHub (private repo) | INTERNAL | Indefinite (Git history) |
| Terraform configurations | GitHub (private repo) | INTERNAL | Indefinite (Git history) |
| Secrets and credentials | Secrets Manager | RESTRICTED | Life of credential |
| KMS key material | AWS KMS (HSM-backed) | RESTRICTED | Per key lifecycle |
| CloudTrail logs | S3 + CloudWatch | CONFIDENTIAL | 7 years |
| Application logs (no PHI) | CloudWatch Logs | INTERNAL | 1 year |
| Application logs (with PHI) | CloudWatch Logs (encrypted, restricted) | RESTRICTED/PHI | 1 year (then archived) |
| Audit trail logs | S3 audit bucket | RESTRICTED/PHI | 7 years |
| VPC Flow Logs | CloudWatch Logs | INTERNAL | 1 year |
| WAF logs | S3 + CloudWatch | INTERNAL | 1 year |
| Vulnerability scan results | Security Hub / S3 | CONFIDENTIAL | 3 years |
| Penetration test reports | Secure document storage | CONFIDENTIAL | 5 years |

## 9. Third-Party Data Sharing

### 9.1 Sharing Requirements by Classification

| Classification | Sharing Prerequisite |
|---------------|---------------------|
| PUBLIC | No restrictions |
| INTERNAL | NDA executed |
| CONFIDENTIAL | NDA executed + Security Officer approval + encrypted transfer |
| RESTRICTED/PHI | BAA executed + Security Officer approval + encrypted transfer + minimum necessary data set + audit logged |

### 9.2 Current Third-Party Data Flows

| Third Party | Data Shared | Classification | Safeguard |
|------------|-------------|----------------|-----------|
| AWS | All data (infrastructure hosting) | RESTRICTED/PHI | BAA, encryption, VPC isolation |
| Stripe | Payment metadata (no clinical PHI) | CONFIDENTIAL | PCI DSS compliance, TLS, Stripe BAA |
| Telnyx | Telephony metadata, phone numbers | CONFIDENTIAL | TLS, signed webhooks |
| State NEMSIS Systems | Patient encounter reports | RESTRICTED/PHI | Encrypted NEMSIS submission, state DUA |
| Covered Entity Customers | Patient data (their data, we are BA) | RESTRICTED/PHI | BAA, access controls, audit trail |

## 10. Reclassification

Data may be reclassified when:

- The sensitivity or regulatory status changes (e.g., data is de-identified per HIPAA Safe Harbor).
- A new regulation applies to previously unregulated data.
- Business use changes the risk profile.

Reclassification requires:

1. Written request from the data owner with justification.
2. Security Officer review and approval.
3. Updated data inventory entry.
4. Adjustment of technical controls to match the new classification.
5. Documentation of the reclassification decision and effective date.

Reclassification to a lower level for PHI data requires documented evidence of compliant de-identification.

## 11. Enforcement

Compliance with this policy is monitored through:

- Automated Macie scans to detect PHI in unauthorized S3 locations.
- Code review checks to ensure PHI is not logged, exposed in error messages, or stored in inappropriate fields.
- Quarterly data inventory review.
- SOC 2 audit testing of data classification controls.

Violations are handled per the Information Security Policy (ISP-001) enforcement provisions.

## 12. Related Policies

- Information Security Policy (ISP-001)
- Encryption Policy (ENC-001)
- Data Retention and Disposal Policy (DRD-001)
- Access Control Policy (ACP-001)
- Acceptable Use Policy (AUP-001)
- Breach Notification Procedure (BNP-001)

## 13. Revision History

| Version | Date           | Author           | Description          |
|---------|----------------|------------------|----------------------|
| 1.0     | March 9, 2026  | Security Officer | Initial release      |

# Data Retention and Disposal Policy

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Policy ID**      | DRD-001                                    |
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
3. [Retention Schedule](#3-retention-schedule)
4. [AWS Storage Lifecycle Rules](#4-aws-storage-lifecycle-rules)
5. [Database Retention](#5-database-retention)
6. [Backup Retention](#6-backup-retention)
7. [Log Retention](#7-log-retention)
8. [Data Disposal Methods](#8-data-disposal-methods)
9. [Crypto-Shred Procedures](#9-crypto-shred-procedures)
10. [Customer Data Return and Deletion](#10-customer-data-return-and-deletion)
11. [Legal Hold](#11-legal-hold)
12. [Evidence of Disposal](#12-evidence-of-disposal)
13. [Roles and Responsibilities](#13-roles-and-responsibilities)
14. [Enforcement](#14-enforcement)
15. [Related Policies](#15-related-policies)
16. [Revision History](#16-revision-history)

---

## 1. Purpose

This Data Retention and Disposal Policy defines the retention periods and secure disposal procedures for all data processed by FusionEMS Quantum. Proper retention ensures compliance with HIPAA, state medical records laws, financial regulations, and contractual obligations. Proper disposal minimizes the risk of unauthorized data exposure after the business need has ended. This policy balances regulatory requirements for long-term record keeping with the security principle of minimizing retained data.

## 2. Scope

This policy applies to all data stored within FusionEMS systems across all environments, including:

- Production RDS PostgreSQL databases.
- Amazon S3 buckets (documents, exports, NEMSIS submissions, audit logs).
- Amazon ElastiCache Redis clusters.
- CloudWatch Logs.
- AWS Backup recovery points.
- RDS automated and manual snapshots.
- CloudTrail logs.
- Version control repositories (Git history).
- Any offline or archival media.

## 3. Retention Schedule

### 3.1 Retention by Data Type

| Data Type | Classification | Retention Period | Regulatory Basis | Storage Location |
|-----------|---------------|-----------------|------------------|-----------------|
| ePCR records (patient care reports) | RESTRICTED/PHI | 7 years from date of service | State EMS records requirements (most states 7-10 years); HIPAA general practice | RDS `epcr_records` + S3 documents |
| Patient demographics | RESTRICTED/PHI | 7 years from last encounter | HIPAA; state medical records laws | RDS `patients` |
| Vital signs data | RESTRICTED/PHI | 7 years from date of capture | State EMS records requirements | RDS `vitals` |
| Medication administration records | RESTRICTED/PHI | 7 years from date of administration | DEA requirements (Schedule II-V: 2 years minimum); FusionEMS extends to 7 years | RDS `medications` |
| NEMSIS submissions | RESTRICTED/PHI | 7 years from submission date | State DUA requirements | S3 NEMSIS bucket |
| Patient signatures | RESTRICTED/PHI | 7 years from date of service | State requirements | S3 documents bucket |
| Dispatch/CAD records | RESTRICTED/PHI | 7 years from incident date | State EMS records requirements | RDS `incidents` |
| Billing claims (CMS-1500) | RESTRICTED/PHI | 7 years from date of service | Medicare/Medicaid (7 years); state Medicaid; False Claims Act (6 years + 3 years) | RDS `billing_claims` |
| Insurance information | RESTRICTED/PHI | 7 years from last use | HIPAA | RDS `insurance` |
| Payment / remittance records | CONFIDENTIAL | 7 years from transaction date | IRS requirements; state tax laws | RDS `payments` + Stripe |
| Agency (tenant) configuration | CONFIDENTIAL | Life of tenant + 1 year post-termination | Contractual | RDS `agencies` |
| User accounts | CONFIDENTIAL | Life of account + 7 years (deactivated state) | HIPAA audit requirements | Cognito + RDS `users` |
| Audit trail logs | RESTRICTED/PHI | 7 years from log date | HIPAA §164.312(b) audit controls | S3 audit bucket |
| CloudTrail logs | CONFIDENTIAL | 7 years from log date | SOC 2 audit evidence; HIPAA | S3 CloudTrail bucket |
| Application logs (no PHI) | INTERNAL | 1 year from creation | Operational need | CloudWatch Logs |
| Application logs (with PHI) | RESTRICTED/PHI | 1 year operational + 6 years archived | HIPAA | CloudWatch Logs → S3 archive |
| VPC Flow Logs | INTERNAL | 1 year from capture | Security monitoring | CloudWatch Logs |
| WAF logs | INTERNAL | 1 year from capture | Security monitoring | S3 / CloudWatch |
| Security scan results | CONFIDENTIAL | 3 years from scan date | SOC 2 evidence | Security Hub / S3 |
| Penetration test reports | CONFIDENTIAL | 5 years from test date | SOC 2 evidence | Secure document store |
| Employee HR records | CONFIDENTIAL | Duration of employment + 7 years | Federal and state employment law | HR system |
| Contracts and BAAs | CONFIDENTIAL | Contract term + 6 years | Statute of limitations | Secure document store |
| Compliance policy documents | INTERNAL | Indefinite (superseded versions retained) | SOC 2 audit trail | Git version history |
| Source code | INTERNAL | Indefinite | Business asset | Git version history |

### 3.2 Retention for Minors

For patient records involving minors (patients under 18 at time of service), the 7-year retention period begins on the patient's 18th birthday, or 7 years from date of service, whichever is later. This ensures records are available until at least 7 years after the patient reaches the age of majority, consistent with state statute of limitations for malpractice claims involving minors.

## 4. AWS Storage Lifecycle Rules

### 4.1 S3 Lifecycle Policies

S3 lifecycle rules are configured in Terraform for each bucket class. The following rules apply:

#### Documents / Exports Bucket (`fusionems-{env}-documents`)

| Rule | Transition / Action | Days from Creation |
|------|--------------------|--------------------|
| Standard → S3 Intelligent-Tiering | Transition | 30 days |
| S3 Intelligent-Tiering → S3 Glacier Flexible Retrieval | Transition | 90 days |
| S3 Glacier → S3 Glacier Deep Archive | Transition | 365 days |
| Expiration (non-critical exports) | Delete | 730 days (2 years) |
| Abort incomplete multipart uploads | Clean up | 7 days |

Note: Objects tagged `retain=long-term` are excluded from the 730-day expiration rule.

#### NEMSIS Submissions Bucket (`fusionems-{env}-nemsis`)

| Rule | Transition / Action | Days from Creation |
|------|--------------------|--------------------|
| Standard → S3 Glacier Flexible Retrieval | Transition | 90 days |
| S3 Glacier → S3 Glacier Deep Archive | Transition | 365 days |
| Expiration | **Never** (retained for 7 years minimum; manual cleanup after retention period) |

#### Audit Log Bucket (`fusionems-{env}-audit`)

| Rule | Transition / Action | Days from Creation |
|------|--------------------|--------------------|
| Standard → S3 Glacier Flexible Retrieval | Transition | 90 days |
| S3 Glacier → S3 Glacier Deep Archive | Transition | 365 days |
| Expiration | **Never** (retained for 7 years minimum; manual cleanup after retention period) |
| Object Lock | Governance mode, 7-year retention |

#### CloudTrail Bucket (`fusionems-{env}-cloudtrail`)

| Rule | Transition / Action | Days from Creation |
|------|--------------------|--------------------|
| Standard → S3 Glacier Flexible Retrieval | Transition | 90 days |
| S3 Glacier → S3 Glacier Deep Archive | Transition | 365 days |
| Expiration | **Never** (retained for 7 years minimum) |

### 4.2 S3 Object Lock

The audit log bucket uses S3 Object Lock in Governance mode with a 7-year retention period. This ensures:

- Audit log objects cannot be deleted or overwritten for 7 years.
- Only users with `s3:BypassGovernanceRetention` permission (restricted to Security Officer/founder role) can override the lock.
- Object Lock prevents accidental or malicious destruction of audit evidence.

### 4.3 S3 Versioning

All S3 buckets storing CONFIDENTIAL or RESTRICTED data have versioning enabled. Previous versions follow the same lifecycle transition rules as current versions. Noncurrent version expiration is set to 90 days after becoming noncurrent (to recover from accidental deletion) except for audit and CloudTrail buckets where noncurrent versions follow the same 7-year retention.

## 5. Database Retention

### 5.1 Active Data Management

PHI and billing data remain in the active RDS database for the full retention period. FusionEMS does not currently archive database records to cold storage; the RDS instance is sized to accommodate the full 7-year retention window.

### 5.2 Soft Deletion

Patient records, ePCR records, and billing claims use soft deletion (a `deleted_at` timestamp and `is_deleted` flag). Soft-deleted records:

- Are excluded from application queries by default.
- Remain accessible for audit, legal, and compliance purposes.
- Follow the same retention schedule as active records.
- Are permanently purged (hard-deleted) only after the retention period expires, via a scheduled database maintenance job.

### 5.3 Database Purge Process

When data reaches the end of its retention period:

1. The automated retention job identifies records eligible for purge (retention period expired, no legal hold, no pending audit).
2. A pre-purge report is generated listing record counts by type and tenant.
3. The Security Officer reviews and approves the purge batch.
4. Records are hard-deleted from the database in a transaction.
5. A disposal record is created in the audit log (Section 12).
6. Corresponding S3 objects (documents, signatures) are deleted.
7. Post-purge validation confirms the records are no longer queryable.

## 6. Backup Retention

### 6.1 RDS Automated Backups

| Backup Type | Retention | Frequency | Encryption |
|------------|-----------|-----------|-----------|
| RDS automated snapshots | 35 days | Daily (automated by RDS) | Encrypted with RDS KMS key |
| RDS manual snapshots (monthly) | 7 years | Monthly (automated via AWS Backup) | Encrypted with RDS KMS key |
| RDS cross-region snapshot copies | 35 days | Daily (for DR region) | Re-encrypted with DR region KMS key |

### 6.2 AWS Backup Vault

AWS Backup is configured with the following backup plans:

| Resource | Backup Frequency | Retention | Vault |
|---------|-----------------|-----------|-------|
| RDS (primary) | Daily | 35 days | `fusionems-{env}-backup-vault` |
| RDS (monthly long-term) | Monthly | 7 years | `fusionems-{env}-backup-vault-lt` |
| EBS volumes | Daily | 14 days | `fusionems-{env}-backup-vault` |
| S3 (audit bucket) | Weekly | 90 days | `fusionems-{env}-backup-vault` |

Backup vault access policy restricts deletion to the Security Officer role only. Vault lock may be enabled for the long-term vault to enforce immutability.

### 6.3 Redis Backup

ElastiCache Redis uses:

- **Automatic failover**: Multi-AZ replication for high availability; not a long-term backup.
- **Snapshot retention**: Last 7 snapshots retained (approximately 7 days).
- **Data volatility**: Redis is used as a cache and session store. Data in Redis is ephemeral and reconstructable from the authoritative RDS database. Long-term backup of Redis is not required.

## 7. Log Retention

### 7.1 CloudWatch Logs Retention

| Log Group | Retention | Classification |
|-----------|-----------|---------------|
| `/ecs/fusionems-{env}-api` (application logs) | 365 days | INTERNAL (PHI scrubbed at log emission) |
| `/ecs/fusionems-{env}-worker` (background worker logs) | 365 days | INTERNAL |
| `/rds/fusionems-{env}` (RDS logs) | 365 days | CONFIDENTIAL |
| `/vpc/flowlogs` | 365 days | INTERNAL |
| `/waf/fusionems-{env}` | 365 days | INTERNAL |
| `/lambda/` (rotation functions) | 90 days | INTERNAL |

### 7.2 Log Archival

Application logs older than 365 days are not retained in CloudWatch. If logs containing PHI references are needed beyond 1 year, they must be exported to the audit S3 bucket before the CloudWatch retention window expires. This export is handled by a scheduled CloudWatch Logs export task configured in the Terraform monitoring module.

## 8. Data Disposal Methods

### 8.1 Disposal Methods by Storage Type

| Storage Type | Disposal Method | Verification |
|-------------|----------------|-------------|
| **RDS records** | Hard DELETE with transaction commit; vacuum reclaims space | Row count verification pre/post delete |
| **RDS snapshots** | `delete-db-snapshot` API call | Snapshot no longer appears in `describe-db-snapshots` |
| **S3 objects** | `DeleteObject` API (versioned: delete all versions + delete markers) | Object no longer retrievable; verified via `HeadObject` |
| **S3 bucket (full)** | Empty all objects + versions, then `DeleteBucket` | Bucket no longer exists |
| **CloudWatch Log group** | Retention policy auto-expires; or `DeleteLogGroup` for immediate | Log group/streams no longer exist |
| **ElastiCache Redis** | `FLUSHALL` for data; `DeleteCacheCluster` for instance | Cluster no longer exists |
| **EBS volumes** | `DeleteVolume` API; AWS-managed secure wipe | Volume no longer exists in `describe-volumes` |
| **Secrets Manager secrets** | `DeleteSecret` with 30-day recovery window (or force-delete) | Secret no longer retrievable |
| **Cognito user** | `AdminDeleteUser` API | User no longer in user pool |
| **Terraform state** | State file in S3 with versioning; old state versions follow S3 lifecycle | State validated against live infrastructure |

### 8.2 Physical Media

FusionEMS Quantum operates entirely in AWS cloud infrastructure. No physical media (hard drives, tapes, USB devices) is used for production data storage. If any physical media were to contain FusionEMS data:

- Hard drives: NIST SP 800-88 Purge (cryptographic erase or degaussing) followed by physical destruction.
- Portable media: Physical destruction (shredding).
- Paper documents: Cross-cut shredding.

Disposal of physical media requires a certificate of destruction from a qualified vendor.

## 9. Crypto-Shred Procedures

Crypto-shredding is the primary method for rendering large volumes of encrypted data irrecoverable without decrypting and deleting individual records. This is used when:

- A customer (tenant) terminates their contract and requests data deletion.
- A KMS key has been compromised and the data must be rendered inaccessible.
- The retention period for all data encrypted by a specific key has expired.

### 9.1 Process

1. **Pre-shred inventory**: Enumerate all data encrypted with the target KMS key (S3 buckets, RDS, backup snapshots).
2. **Verification**: Confirm no data encrypted with this key is still within its retention period or subject to legal hold.
3. **Key scheduling**: Schedule the KMS key for deletion via `ScheduleKeyDeletion` with the mandatory 30-day waiting period.
4. **Notification**: Notify the Security Officer and data owner that the key will be deleted in 30 days.
5. **Waiting period**: During the 30-day window, the key is disabled (cannot be used for encryption/decryption). This provides a safety window to cancel if needed.
6. **Deletion**: After 30 days, AWS permanently deletes the key material. All data encrypted exclusively with this key is irrecoverable.
7. **Documentation**: Record the crypto-shred event in the disposal log with: key ID, key alias, data scope, deletion timestamp, authorization.

### 9.2 Tenant-Specific Crypto-Shred

For per-tenant data isolation via crypto-shred, FusionEMS can provision a per-tenant KMS data key. Upon tenant termination:

- All tenant data in S3 encrypted with the tenant-specific data key is rendered irrecoverable by scheduling the data key's KMS key for deletion.
- Database records are hard-deleted via the standard purge process (Section 5.3) since RDS uses instance-level encryption, not per-tenant encryption.

## 10. Customer Data Return and Deletion

### 10.1 Contract Termination

Upon termination of a customer (tenant) contract, FusionEMS must process the data as follows within 30 days of the termination effective date:

1. **Notification**: FusionEMS notifies the departing tenant that their data will be available for export for 30 days.
2. **Export**: If requested, FusionEMS provides a complete data export in machine-readable format:
   - ePCR records: NEMSIS-compliant XML or JSON.
   - Billing data: CSV or JSON export.
   - Documents and signatures: Original format (PDF, PNG) via S3 presigned URLs.
   - User list: CSV export of user accounts.
   - Audit logs: JSON export of the tenant's audit trail.
3. **Retention hold**: During the 30-day export window, no data is deleted.
4. **Deletion**: After the export window (or upon written confirmation that export is complete or waived):
   - All tenant records are soft-deleted immediately.
   - Within 90 days, all tenant records are hard-deleted from the database.
   - All tenant S3 objects are deleted (all versions).
   - If a tenant-specific KMS key was used, it is scheduled for deletion (crypto-shred).
   - Tenant user accounts are deleted from Cognito.
5. **Certification**: FusionEMS provides a written certification of data deletion to the departing tenant.

### 10.2 Exceptions

- Data required by legal hold (Section 11) is excluded from deletion until the hold is released.
- Aggregate, anonymized analytics data derived from tenants may be retained per the terms of the customer agreement.
- Audit log entries referencing the tenant (created by FusionEMS system operations) are retained per the 7-year audit log retention policy but are not accessible to any active tenant.

## 11. Legal Hold

### 11.1 Purpose

A legal hold suspends the normal retention and disposal schedule for specific data that may be relevant to pending or anticipated litigation, regulatory investigation, or audit.

### 11.2 Process

1. Legal counsel or the Security Officer issues a legal hold notice specifying the data scope (tenant, date range, data types).
2. The data scope is tagged in the system (S3 object tags, database flags) to prevent automated purge.
3. All disposal processes check for legal hold before executing deletion.
4. The legal hold remains in effect until released by legal counsel in writing.
5. Upon release, the data reverts to the normal retention schedule and is eligible for disposal when the retention period expires.

### 11.3 Documentation

Legal holds are tracked in a register maintained by the Security Officer, including: hold ID, issue date, issuing authority, data scope, status (active/released), release date.

## 12. Evidence of Disposal

### 12.1 Disposal Log

Every disposal action generates a record in the disposal log stored in the audit S3 bucket. Each record includes:

| Field | Description |
|-------|-------------|
| `disposal_id` | Unique identifier for the disposal event |
| `disposal_date` | Date and time (UTC) of disposal execution |
| `data_type` | Type of data disposed (e.g., ePCR records, billing claims, snapshot) |
| `data_scope` | Scope (tenant ID, date range, record count) |
| `classification` | Data classification level |
| `disposal_method` | Method used (hard delete, S3 delete, crypto-shred, snapshot deletion) |
| `authorization` | Name and role of the person who authorized disposal |
| `executed_by` | Name/system that executed the disposal (may be automated job) |
| `verification` | Confirmation that disposal was verified (row count, object existence check) |
| `retention_policy_ref` | Reference to the retention rule that triggered disposal |
| `legal_hold_check` | Confirmation that no legal hold applied to the disposed data |

### 12.2 Customer Disposal Certification

For customer data deleted upon contract termination, FusionEMS provides a signed certification letter that includes:

- Customer (tenant) name and ID.
- Date range of data covered.
- Data types deleted.
- Disposal methods used.
- Date of disposal completion.
- Attestation that no copies remain in active systems.
- Note that data may persist in encrypted backups until backup retention expires (with reference to backup retention schedule and encryption protection).

## 13. Roles and Responsibilities

| Role | Responsibility |
|------|---------------|
| **Security Officer** | Policy owner; approves disposal batches; maintains disposal log; issues legal holds; provides customer certifications |
| **CTO** | Oversees Terraform-managed lifecycle rules and backup plans; ensures automated processes function correctly |
| **Engineering** | Implements soft-delete, purge jobs, and S3 lifecycle rules in code and infrastructure |
| **DevOps** | Configures AWS Backup plans, CloudWatch retention, S3 lifecycle policies in Terraform |
| **Agency Admin** | Data owner for patient records within their tenant |
| **Legal Counsel** | Issues and releases legal holds; advises on retention period questions |

## 14. Enforcement

Compliance with this policy is enforced through:

- Automated S3 lifecycle rules configured in Terraform (verified by Checkov).
- Automated CloudWatch Logs retention periods configured in Terraform.
- AWS Backup plans with defined retention policies.
- Scheduled database purge jobs with Security Officer approval gate.
- Quarterly review of retention compliance (verifying data is retained for required periods and disposed when periods expire).
- SOC 2 audit testing of data retention and disposal controls.

Violations are handled per the Information Security Policy (ISP-001) enforcement provisions.

## 15. Related Policies

- Information Security Policy (ISP-001)
- Data Classification Policy (DCP-001)
- Encryption Policy (ENC-001)
- Access Control Policy (ACP-001)
- Breach Notification Procedure (BNP-001)
- Business Continuity / Disaster Recovery Plan (BCP-001)

## 16. Revision History

| Version | Date           | Author           | Description          |
|---------|----------------|------------------|----------------------|
| 1.0     | March 9, 2026  | Security Officer | Initial release      |

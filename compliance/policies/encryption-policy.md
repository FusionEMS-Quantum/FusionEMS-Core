# Encryption Policy

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Policy ID**      | ENC-001                                    |
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
3. [Encryption at Rest](#3-encryption-at-rest)
4. [Encryption in Transit](#4-encryption-in-transit)
5. [Key Management](#5-key-management)
6. [Certificate Management](#6-certificate-management)
7. [Prohibited Algorithms and Practices](#7-prohibited-algorithms-and-practices)
8. [Data Handling by Classification Level](#8-data-handling-by-classification-level)
9. [Application-Level Encryption](#9-application-level-encryption)
10. [Backup Encryption](#10-backup-encryption)
11. [Cryptographic Incident Response](#11-cryptographic-incident-response)
12. [Compliance Mapping](#12-compliance-mapping)
13. [Enforcement](#13-enforcement)
14. [Related Policies](#14-related-policies)
15. [Revision History](#15-revision-history)

---

## 1. Purpose

This Encryption Policy defines the cryptographic standards and key management practices required for all FusionEMS Quantum systems. FusionEMS processes Protected Health Information (PHI) for EMS, HEMS, Fire, ePCR, CAD, Fleet, Billing, MDT, and AI Analytics operations. Encryption is a primary technical safeguard under the HIPAA Security Rule and a foundational control for SOC 2 Trust Services Criteria. This policy ensures that all data is protected against unauthorized disclosure through approved cryptographic mechanisms.

## 2. Scope

This policy applies to all data created, processed, stored, or transmitted by FusionEMS systems across all environments (production, staging, development), including:

- All AWS-managed data stores (RDS, S3, ElastiCache, EBS, CloudWatch Logs).
- All data in transit between clients, services, and external integrations.
- All encryption keys, certificates, and cryptographic material.
- All backup and disaster recovery data.
- All secrets and credentials managed by the platform.

## 3. Encryption at Rest

All data stored within FusionEMS infrastructure must be encrypted at rest using AWS KMS (Key Management Service) with automatic key rotation.

### 3.1 AWS Service Encryption Configuration

| AWS Service | Encryption Method | Key Type | Rotation |
|-------------|------------------|----------|----------|
| **RDS PostgreSQL** | AES-256 via KMS | AWS-managed CMK (`aws/rds`) or dedicated CMK per environment | Annual automatic rotation |
| **S3 Buckets** | SSE-KMS (AES-256) | Dedicated CMK per bucket class (audit, documents, exports, NEMSIS) | Annual automatic rotation |
| **ElastiCache Redis** | At-rest encryption enabled | AWS-managed CMK (`aws/elasticache`) | Managed by AWS |
| **EBS Volumes** | AES-256 via KMS | AWS-managed CMK (`aws/ebs`) | Annual automatic rotation |
| **Secrets Manager** | AES-256 via KMS | AWS-managed CMK (`aws/secretsmanager`) or dedicated CMK | Managed by AWS |
| **CloudWatch Logs** | AES-256 via KMS | Dedicated CMK for log encryption | Annual automatic rotation |
| **AWS Backup Vault** | AES-256 via KMS | Dedicated CMK for backup vault | Annual automatic rotation |
| **ECR Container Images** | AES-256 via KMS | AWS-managed CMK (`aws/ecr`) | Managed by AWS |
| **DynamoDB (if used)** | AES-256 via KMS | AWS-managed CMK | Managed by AWS |

### 3.2 S3 Bucket Policy Enforcement

All S3 buckets must enforce encryption through bucket policies that:

- Deny `s3:PutObject` requests that do not include `x-amz-server-side-encryption: aws:kms`.
- Deny `s3:PutObject` requests that do not specify the correct KMS key ID.
- Enable S3 default encryption as a fallback.
- Block all public access via S3 Block Public Access settings (enabled at account and bucket level).

### 3.3 RDS Encryption

- RDS instances are created with `storage_encrypted = true` in Terraform.
- Encryption is applied at the instance level and covers all data files, automated backups, read replicas, and snapshots.
- Unencrypted RDS instances are prohibited. Checkov IaC scanning (CKV_AWS_16) validates this in the CI pipeline.
- Performance Impact Note: RDS encryption uses the AES-256-GCM cipher with hardware acceleration and has negligible performance impact.

### 3.4 Redis Encryption

- ElastiCache Redis clusters are configured with `at_rest_encryption_enabled = true` and `transit_encryption_enabled = true` in Terraform.
- Redis AUTH tokens are stored in Secrets Manager and rotated per the credential rotation schedule.

## 4. Encryption in Transit

All data in transit must be encrypted using TLS (Transport Layer Security).

### 4.1 TLS Requirements

| Connection Path | Minimum TLS Version | Preferred Version | Certificate |
|----------------|--------------------|--------------------|------------|
| Client → CloudFront | TLS 1.2 | TLS 1.3 | ACM-managed certificate |
| Client → ALB (direct) | TLS 1.2 | TLS 1.3 | ACM-managed certificate |
| ALB → ECS (internal) | TLS 1.2 | TLS 1.2 | Internal certificate |
| ECS → RDS | TLS 1.2 | TLS 1.2 | RDS-managed CA certificate |
| ECS → Redis | TLS 1.2 | TLS 1.2 | ElastiCache-managed certificate |
| ECS → S3 (VPC endpoint) | TLS 1.2 | TLS 1.2 | AWS-managed |
| ECS → Secrets Manager | TLS 1.2 | TLS 1.2 | AWS-managed (VPC endpoint) |
| ECS → External APIs (Stripe, Telnyx) | TLS 1.2 | TLS 1.3 | Provider-managed |
| GitHub Actions → AWS (OIDC) | TLS 1.2 | TLS 1.3 | AWS STS-managed |

### 4.2 ALB TLS Configuration

The Application Load Balancer is configured with:

- **Security Policy**: `ELBSecurityPolicy-TLS13-1-2-2021-06` (supports TLS 1.3 and TLS 1.2 only).
- **Cipher Suites**: Only AEAD cipher suites are permitted:
  - `TLS_AES_128_GCM_SHA256` (TLS 1.3)
  - `TLS_AES_256_GCM_SHA384` (TLS 1.3)
  - `TLS_CHACHA20_POLY1305_SHA256` (TLS 1.3)
  - `ECDHE-RSA-AES128-GCM-SHA256` (TLS 1.2)
  - `ECDHE-RSA-AES256-GCM-SHA384` (TLS 1.2)
- **HTTP Strict Transport Security (HSTS)**: Enabled via CloudFront response headers policy (`max-age=63072000; includeSubDomains; preload`).

### 4.3 RDS SSL Enforcement

- RDS parameter group sets `rds.force_ssl = 1` to reject unencrypted connections.
- Application connection strings include `sslmode=verify-full` to enforce certificate verification.
- RDS CA certificates are validated against the AWS RDS Certificate Authority.

### 4.4 Internal Service Communication

- Service-to-service communication within the ECS cluster uses signed JWT tokens for authentication and TLS for transport encryption.
- VPC endpoints eliminate the need for internet traversal when accessing AWS services (S3, Secrets Manager, KMS, CloudWatch, ECR).

## 5. Key Management

### 5.1 Key Management Service (KMS)

All encryption keys are managed by AWS KMS. FusionEMS does not store, generate, or manage cryptographic keys outside of AWS KMS and Secrets Manager.

### 5.2 Key Hierarchy

```
AWS KMS Root Keys (AWS-managed infrastructure)
├── Production CMKs
│   ├── fusionems-prod-rds-key          → RDS encryption
│   ├── fusionems-prod-s3-audit-key     → Audit log bucket
│   ├── fusionems-prod-s3-docs-key      → Document storage bucket
│   ├── fusionems-prod-s3-exports-key   → Export/NEMSIS bucket
│   ├── fusionems-prod-logs-key         → CloudWatch Logs
│   ├── fusionems-prod-backup-key       → AWS Backup vault
│   └── fusionems-prod-secrets-key      → Secrets Manager (optional override)
├── Staging CMKs
│   └── (mirrors production key structure)
└── Development CMKs
    └── (mirrors production key structure, may use AWS-managed keys)
```

### 5.3 Key Rotation

| Key Category | Rotation Period | Mechanism |
|-------------|----------------|-----------|
| KMS CMKs (symmetric) | Annual | AWS KMS automatic rotation (`enable_key_rotation = true` in Terraform) |
| KMS CMKs (asymmetric) | Manual, per policy | Manual rotation with key alias update |
| Cognito signing keys | Managed by AWS | Automatic (no user action) |
| Secrets Manager secrets | 90 days | Secrets Manager automatic rotation with Lambda rotator |
| TLS certificates (ACM) | Prior to expiry | ACM auto-renewal for DNS-validated certs |

### 5.4 Key Access Controls

- KMS key policies restrict key usage to specific IAM roles and services.
- Key administrators (who can manage key policies) are separate from key users (who can encrypt/decrypt).
- All KMS API calls (Encrypt, Decrypt, GenerateDataKey, CreateGrant) are logged in CloudTrail.
- Cross-account key sharing is prohibited unless explicitly authorized by the Security Officer for the DR environment.

### 5.5 Key Deletion

- KMS keys scheduled for deletion have a mandatory 30-day waiting period.
- Key deletion requires Security Officer approval and documented justification.
- Before key deletion, all data encrypted with the key must be re-encrypted with a new key or confirmed as no longer needed (crypto-shred scenario).
- Key deletion events are logged and included in the quarterly key management review.

## 6. Certificate Management

### 6.1 AWS Certificate Manager (ACM)

All TLS certificates for FusionEMS public-facing endpoints are managed via AWS Certificate Manager:

- **Validation**: DNS validation via Route53 CNAME records (automated in Terraform).
- **Renewal**: Automatic renewal managed by ACM. Certificates are renewed 60 days before expiration.
- **Monitoring**: CloudWatch alarm on `DaysToExpiry` metric for all ACM certificates with threshold at 30 days.

### 6.2 Certificate Inventory

| Certificate | Domain | Service | Validation |
|------------|--------|---------|------------|
| Production API | api.fusionems.com | ALB | DNS (Route53) |
| Production Web | app.fusionems.com | CloudFront | DNS (Route53) |
| Staging API | api.staging.fusionems.com | ALB | DNS (Route53) |
| Staging Web | app.staging.fusionems.com | CloudFront | DNS (Route53) |

### 6.3 Certificate Compliance

- Self-signed certificates are prohibited in production.
- Wildcard certificates are minimized; per-service certificates are preferred.
- Certificate transparency logs are monitored for unauthorized certificate issuance.
- Certificate pinning is not used (to avoid operational brittleness); instead, standard CA validation is relied upon.

## 7. Prohibited Algorithms and Practices

### 7.1 Prohibited Cryptographic Algorithms

The following algorithms are prohibited on all FusionEMS systems:

| Category | Prohibited | Reason |
|----------|-----------|--------|
| Hash functions | MD5, SHA-1 | Known collision vulnerabilities |
| Symmetric encryption | DES, 3DES, RC4, Blowfish | Insufficient key length or known weaknesses |
| TLS versions | SSL 2.0, SSL 3.0, TLS 1.0, TLS 1.1 | Deprecated, known vulnerabilities (POODLE, BEAST) |
| Key exchange | Static RSA (non-ephemeral) | No forward secrecy |
| RSA key size | < 2048 bits | Insufficient security margin |
| ECDSA/ECDH curve size | < 256 bits | Insufficient security margin |

### 7.2 Prohibited Key Management Practices

- Storing encryption keys in source code, container images, or environment variables.
- Transmitting keys via email, Slack, or any unencrypted channel.
- Sharing keys between environments (production keys must never be used in staging or development).
- Importing externally generated keys into KMS without Security Officer approval.
- Disabling key rotation without a documented, time-bound exception approved by the Security Officer.

## 8. Data Handling by Classification Level

Encryption requirements vary by data classification per the Data Classification Policy (DCP-001):

| Classification | Encryption at Rest | Encryption in Transit | Key Management | Additional Controls |
|---------------|-------------------|----------------------|----------------|-------------------|
| **PUBLIC** | Recommended (S3 default encryption) | Required (TLS 1.2+) | AWS-managed keys acceptable | None |
| **INTERNAL** | Required (KMS) | Required (TLS 1.2+) | AWS-managed or dedicated CMK | Access logging |
| **CONFIDENTIAL** | Required (dedicated CMK) | Required (TLS 1.2+) | Dedicated CMK with rotation | Access logging, restricted key policy |
| **RESTRICTED/PHI** | Required (dedicated CMK) | Required (TLS 1.2+, TLS 1.3 preferred) | Dedicated CMK with annual rotation, key policy restricts to specific roles | Access logging, audit trail, field-level encryption for PII subfields |

## 9. Application-Level Encryption

### 9.1 Field-Level Encryption

For RESTRICTED/PHI data requiring additional protection beyond storage-layer encryption:

- Social Security Numbers (SSNs) are encrypted at the application level before database storage using a dedicated field-encryption key in Secrets Manager.
- The encryption function uses AES-256-GCM with unique initialization vectors per value.
- Decryption is performed only at the point of authorized use, not at the query layer.
- Field-level encryption keys are rotated annually with a re-encryption migration.

### 9.2 Token Signing

- Cognito JWT tokens use RS256 (RSA-SHA256) with 2048-bit keys managed by Cognito.
- Internal service-to-service tokens use HS256 with a signing key stored in Secrets Manager, rotated per the 90-day secret rotation schedule.

### 9.3 Password Hashing

- User passwords are hashed by Cognito using the Secure Remote Password (SRP) protocol. FusionEMS backend never receives or stores plaintext passwords.
- Any application-level password hashing (if applicable for non-Cognito flows) must use bcrypt with a minimum cost factor of 12 or Argon2id.

## 10. Backup Encryption

### 10.1 Automated Backups

- RDS automated backups inherit the instance's KMS encryption. All snapshots are encrypted.
- S3 objects are encrypted at rest; cross-region replicated objects inherit the destination bucket's encryption configuration with the destination region's KMS key.
- AWS Backup vault uses a dedicated KMS key. All backup recovery points are encrypted.

### 10.2 Cross-Region DR Encryption

- Cross-region RDS snapshot copies are re-encrypted with the DR region's KMS key.
- S3 cross-region replication uses the destination bucket's KMS key.
- The DR region maintains its own KMS key hierarchy, mirroring the production structure, managed via the Terraform DR environment module.

### 10.3 Backup Integrity

- Backup integrity is verified quarterly by performing test restores.
- Encrypted backups are validated to confirm decryption succeeds with the intended KMS key.
- Backup encryption status is included in the monthly security metrics report.

## 11. Cryptographic Incident Response

### 11.1 Key Compromise

In the event of suspected key compromise:

1. The Security Officer is notified immediately.
2. The compromised key is disabled (not deleted) to prevent further use.
3. A new replacement key is generated.
4. Data encrypted with the compromised key is evaluated for exposure risk.
5. If PHI was encrypted with the compromised key and exposure is confirmed, the Breach Notification Procedure (BNP-001) is invoked.
6. Affected data is re-encrypted with the new key.
7. A post-incident review documents the root cause, timeline, and corrective actions.

### 11.2 Certificate Compromise

In the event of suspected certificate compromise:

1. The compromised certificate is replaced immediately in ACM (new cert issued).
2. ALB/CloudFront listeners are updated to use the new certificate.
3. If the private key was exposed, the old certificate is revoked.
4. HSTS prevents downgrade attacks during the transition.

### 11.3 Algorithm Deprecation

When a cryptographic algorithm is deprecated by standards bodies (NIST, IETF):

1. The Security Officer evaluates the timeline and impact.
2. A migration plan is developed to transition to approved algorithms.
3. Migration is executed within the recommended timeline (typically before the algorithm is formally prohibited).
4. This policy is updated to reflect the new prohibited algorithms.

## 12. Compliance Mapping

| Requirement | Framework | This Policy Section |
|------------|-----------|-------------------|
| ePHI encryption at rest | HIPAA §164.312(a)(2)(iv) | Section 3 |
| ePHI encryption in transit | HIPAA §164.312(e)(1) | Section 4 |
| Encryption key management | HIPAA §164.312(a)(2)(iv) | Section 5 |
| Cryptographic controls | SOC 2 CC6.1, CC6.7 | Sections 3-5 |
| Data protection in transit | SOC 2 CC6.7 | Section 4 |
| Encryption of sensitive data | ISO 27001 A.8.24, A.8.26 | Sections 3, 4, 8 |
| Key management | ISO 27001 A.8.24 | Section 5 |

## 13. Enforcement

Compliance with this policy is enforced through:

- **Automated IaC scanning**: Checkov policies validate encryption configuration in all Terraform modules before deployment. Unencrypted resources are blocked at the CI gate.
- **AWS Config rules**: Monitor for unencrypted RDS instances, S3 buckets without default encryption, and EBS volumes without encryption.
- **Security Hub**: Aggregates encryption compliance findings across all AWS services.
- **Manual audit**: Quarterly review of encryption configuration across all environments.

Violations are handled per the Information Security Policy (ISP-001) enforcement provisions.

## 14. Related Policies

- Information Security Policy (ISP-001)
- Access Control Policy (ACP-001)
- Data Classification Policy (DCP-001)
- Data Retention and Disposal Policy (DRD-001)
- Vulnerability Management Policy (VMP-001)
- Business Continuity / Disaster Recovery Plan (BCP-001)

## 15. Revision History

| Version | Date           | Author           | Description          |
|---------|----------------|------------------|----------------------|
| 1.0     | March 9, 2026  | Security Officer | Initial release      |

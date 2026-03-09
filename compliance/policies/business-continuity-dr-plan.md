# Business Continuity and Disaster Recovery Plan

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Policy ID**      | BCP-001                                    |
| **Version**        | 1.0                                        |
| **Effective Date** | March 9, 2026                              |
| **Review Cadence** | Annual                                     |
| **Next Review**    | March 9, 2027                              |
| **Owner**          | Security Officer                           |
| **Approved By**    | Security Officer, CEO — FusionEMS Quantum  |
| **Classification** | CONFIDENTIAL                               |

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Scope](#2-scope)
3. [Business Impact Analysis](#3-business-impact-analysis)
4. [RPO and RTO Targets](#4-rpo-and-rto-targets)
5. [DR Architecture](#5-dr-architecture)
6. [Recovery Procedures by Service](#6-recovery-procedures-by-service)
7. [Failover Decision Matrix](#7-failover-decision-matrix)
8. [Communication During DR](#8-communication-during-dr)
9. [Testing Schedule](#9-testing-schedule)
10. [Key Personnel Succession](#10-key-personnel-succession)
11. [Vendor Dependency Matrix](#11-vendor-dependency-matrix)
12. [Plan Maintenance](#12-plan-maintenance)
13. [Compliance Mapping](#13-compliance-mapping)
14. [Related Policies](#14-related-policies)
15. [Revision History](#15-revision-history)

---

## 1. Purpose

This Business Continuity and Disaster Recovery Plan (BCP/DR) establishes the framework for maintaining FusionEMS platform operations during disruptive events and recovering critical systems within defined objectives. FusionEMS is a 24/7 life-safety SaaS platform — service interruptions can directly impact emergency medical response, patient care, and dispatch operations. This plan ensures that RPO and RTO targets are met for all critical services, that recovery procedures are documented and tested, and that FusionEMS Quantum can resume operations after any foreseeable disaster scenario.

## 2. Scope

### 2.1 Systems in Scope

| System | Criticality | Description |
|--------|------------|-------------|
| FusionEMS API (ECS Fargate) | Critical | Backend API serving all platform functions (ePCR, CAD, Billing, MDT, AI) |
| FusionEMS Frontend (Next.js) | Critical | Web application for all user interactions |
| RDS PostgreSQL | Critical | Authoritative data store for all PHI, billing, and operational data |
| ElastiCache Redis | High | Session cache, rate limiter, real-time data cache |
| S3 Document Storage | High | ePCR documents, patient signatures, NEMSIS submissions |
| S3 Audit Logs | High | Compliance audit trail |
| Cognito User Pools | Critical | User authentication and identity management |
| ALB / CloudFront | Critical | Traffic ingress, TLS termination, CDN |
| Route53 (DNS) | Critical | Domain resolution and health-check failover |
| WAF | Critical | Web application firewall (security control) |
| Secrets Manager | Critical | Application secrets (database credentials, API keys) |
| KMS | Critical | Encryption key management for all data at rest |
| ECR | High | Container image registry |
| CloudWatch | High | Monitoring, logging, alerting |
| Telnyx Integration | Medium | Telephony services |
| Stripe Integration | Medium | Payment processing |

### 2.2 Disaster Scenarios

| Scenario | Category | Impact |
|----------|----------|--------|
| AZ failure | Infrastructure | Partial capacity loss; handled by Multi-AZ design |
| Region failure | Infrastructure | Full service loss in primary region; requires DR failover |
| RDS failure (instance) | Data | Database unavailable; failover to Multi-AZ standby |
| RDS corruption | Data | Data integrity loss; restore from snapshot |
| S3 data loss | Data | Document/audit log loss; restore from cross-region replica or backup |
| ECS cluster failure | Compute | API unavailable; redeploy to healthy infrastructure |
| Cognito outage | Identity | Authentication impossible; degraded mode (limited) |
| DDoS attack | Security | Service degradation; WAF and Shield mitigation |
| Ransomware | Security | System compromise; isolate, restore from clean backups |
| Third-party failure (AWS-wide) | External | Major cloud outage; limited mitigation options |
| Key personnel unavailability | Operational | Loss of critical knowledge; succession plan |

## 3. Business Impact Analysis

### 3.1 Critical Business Functions

| Business Function | Systems Required | Maximum Tolerable Downtime | Impact if Unavailable |
|-------------------|-----------------|---------------------------|----------------------|
| **Real-time dispatch / CAD** | API, RDS, Redis, ALB, DNS | 1 hour | Ambulances cannot be dispatched; direct patient safety impact |
| **ePCR documentation** | API, RDS, S3, ALB | 4 hours | Crews cannot document patient care; regulatory and clinical impact |
| **Patient data access** | API, RDS, ALB, Cognito | 4 hours | Clinicians cannot access patient history; clinical decision impact |
| **Billing / Claims** | API, RDS, Stripe, ALB | 24 hours | Revenue cycle delay; financial impact |
| **NEMSIS submission** | API, RDS, S3, ALB | 24 hours | Regulatory submission delay; compliance impact |
| **MDT communications** | API, RDS, Redis, Telnyx, ALB | 4 hours | Field crews lose mobile terminal coordination |
| **AI Analytics** | API, RDS, ALB | 24 hours | Analytics unavailable; no immediate patient care impact |
| **Fleet management** | API, RDS, ALB | 24 hours | Fleet tracking unavailable; operational impact |
| **User authentication** | Cognito, ALB, DNS | 1 hour | No user can access the platform; complete function loss |
| **Audit logging** | S3, CloudWatch, API | 4 hours | Compliance gap; no immediate operational impact but regulatory risk |

### 3.2 Financial Impact

| Downtime Duration | Estimated Impact |
|-------------------|-----------------|
| 0–1 hour | Low — most tenants have offline fallback for short interruptions |
| 1–4 hours | Moderate — dispatch operations impacted, ePCR backlog accumulates |
| 4–24 hours | High — billing disruption, regulatory reporting delays, customer SLA violations |
| >24 hours | Severe — customer churn risk, regulatory investigation, legal liability |

## 4. RPO and RTO Targets

### 4.1 Recovery Point Objective (RPO)

| Data Category | RPO Target | Mechanism |
|--------------|-----------|-----------|
| PHI data (ePCR, patient, billing, vitals) | **1 hour** | RDS Multi-AZ synchronous replication (RPO ≈ 0 for AZ failure); automated snapshots every 1 hour for region failure |
| Audit logs | **1 hour** | S3 cross-region replication (near real-time); CloudWatch Logs export |
| Non-PHI operational data (fleet, scheduling) | **4 hours** | RDS automated snapshots (continuous backup with point-in-time recovery) |
| Session / cache data (Redis) | **N/A (ephemeral)** | Redis data is ephemeral and reconstructable; no backup-based RPO |
| Container images | **0 (immutable artifacts)** | ECR images are immutable and replicated; rebuild from source if needed |
| Infrastructure configuration | **0 (code-based)** | All infrastructure is Terraform (code in Git); no data-based RPO |

### 4.2 Recovery Time Objective (RTO)

| System | RTO Target | Recovery Method |
|--------|-----------|-----------------|
| DNS (Route53) | **5 minutes** | Health check failover to DR endpoint (automated) |
| ALB / CloudFront | **15 minutes** | Terraform apply in DR region or CloudFront origin failover |
| ECS API / Workers (Fargate) | **30 minutes** | Terraform apply in DR region using existing ECR images |
| Cognito | **15 minutes** | Cognito is regional; DR region has pre-provisioned user pool with data sync |
| RDS PostgreSQL | **1 hour** | Restore from cross-region snapshot copy; promote read replica |
| ElastiCache Redis | **15 minutes** | Terraform apply in DR region; cache warms from RDS on first requests |
| S3 (documents, audit) | **0 (via replication)** | Cross-region replication provides immediate availability in DR region |
| Secrets Manager | **15 minutes** | Replicate secrets to DR region via Secrets Manager replication configuration |
| KMS | **0 (per-region keys)** | DR region has its own KMS keys (data re-encrypted on cross-region copy) |
| WAF | **15 minutes** | Terraform apply in DR region; WAF rules maintained as code |
| Full platform (end-to-end) | **4 hours** | Complete DR failover including DNS cutover, validation, and smoke testing |

## 5. DR Architecture

### 5.1 Primary Region Architecture

The primary production environment runs in **us-east-1** with the following high-availability design:

- **Multi-AZ RDS**: Primary and standby instances in separate AZs with synchronous replication. Automatic failover on primary failure (typically 1-2 minutes).
- **Multi-AZ ElastiCache**: Redis cluster with replica in a second AZ. Automatic failover to replica.
- **Multi-AZ ECS Fargate**: Tasks distributed across AZs via the ALB. Fargate manages AZ placement.
- **Multi-AZ ALB**: Application Load Balancer spans all AZs in the VPC.
- **S3**: S3 is regional and inherently redundant across AZs within the region.

Multi-AZ design handles single-AZ failures automatically without operator intervention or DR failover.

### 5.2 DR Region Architecture

The DR environment in **us-west-2** is maintained as a warm standby via Terraform:

```
Primary Region (us-east-1)                    DR Region (us-west-2)
┌─────────────────────────┐                   ┌─────────────────────────┐
│  Route53 (health check) │──failover──────── │  Route53 (alias)        │
│  CloudFront CDN         │                   │  CloudFront CDN         │
│  ALB + WAF              │                   │  ALB + WAF (standby)    │
│  ECS Fargate (active)   │                   │  ECS Fargate (scale 0)  │
│  RDS Multi-AZ (primary) │──snapshot copy───▶│  RDS (from snapshot)    │
│  Redis Multi-AZ         │                   │  Redis (cold)           │
│  S3 (documents)         │──CRR────────────▶│  S3 (replica)           │
│  S3 (audit)             │──CRR────────────▶│  S3 (replica)           │
│  Cognito User Pool      │──export/sync────▶│  Cognito User Pool      │
│  Secrets Manager        │──replication────▶│  Secrets Manager        │
│  KMS keys               │                   │  KMS keys (DR region)   │
└─────────────────────────┘                   └─────────────────────────┘
```

### 5.3 Terraform DR Module

The DR environment is managed by the Terraform `dr` environment module (`infra/terraform/environments/dr/`), which:

- Provisions the VPC, subnets, security groups, ALB, WAF, and ECS cluster in the DR region.
- Configures S3 cross-region replication (CRR) for document and audit buckets.
- Configures RDS cross-region snapshot copy schedule (daily).
- Provisions Secrets Manager replica secrets.
- Maintains the DR Cognito user pool.
- Maintains ECS service at desired count 0 (no running tasks) to minimize cost.
- On activation: `terraform apply -var="dr_active=true"` scales ECS services, restores RDS, and updates DNS.

### 5.4 Data Replication

| Data | Replication Method | Lag |
|------|-------------------|-----|
| RDS | Cross-region automated snapshot copy (daily) + manual on-demand | Up to 24 hours (snapshot schedule) |
| S3 (documents) | S3 Cross-Region Replication (CRR) | Minutes (near real-time) |
| S3 (audit logs) | S3 Cross-Region Replication (CRR) | Minutes (near real-time) |
| Secrets Manager | Secrets Manager replication | Near real-time |
| Cognito | Daily scheduled export + DR pool import (or manual) | Up to 24 hours |
| ECR images | ECR cross-region replication | Near real-time |

## 6. Recovery Procedures by Service

### 6.1 RDS PostgreSQL Recovery

#### Scenario A: AZ Failure (Primary AZ down)
1. RDS automatic Multi-AZ failover activates (1-2 minutes).
2. No operator action required.
3. Application reconnects to the new primary endpoint (same DNS name).
4. Validate via Grafana that database queries are succeeding.

#### Scenario B: Instance Corruption / Data Issue
1. Identify the point-in-time before corruption.
2. Use RDS point-in-time recovery: `aws rds restore-db-instance-to-point-in-time`.
3. New instance is created from continuous backup.
4. Validate data integrity on the restored instance.
5. Update application connection string (Secrets Manager) to point to restored instance.
6. Deploy updated ECS tasks to pick up new connection.

#### Scenario C: Full Region Failure
1. Identify the latest cross-region snapshot copy in us-west-2.
2. Restore RDS from the snapshot in the DR region: `aws rds restore-db-instance-from-db-snapshot`.
3. Update Secrets Manager in DR region with the new RDS endpoint.
4. Deploy ECS services in DR region.
5. Update Route53 to point to DR ALB.
6. **RPO impact**: Up to 24 hours of data loss (distance between last snapshot copy).

### 6.2 ElastiCache Redis Recovery

#### Scenario A: AZ Failure
1. ElastiCache automatic failover promotes the replica to primary (seconds to minutes).
2. No operator action required.
3. Application reconnects to the Redis cluster endpoint.

#### Scenario B: Full Failure / Region DR
1. Create a new ElastiCache Redis cluster in the DR region via Terraform.
2. Redis starts cold (empty cache).
3. Application continues to function — cache misses fall through to RDS.
4. Cache warms organically as requests are processed.
5. **Performance impact**: Elevated RDS query load and higher latency for 15-30 minutes during cache warm-up.

### 6.3 ECS Fargate Recovery

#### Scenario A: Task Failure
1. ECS service auto-recovery restarts failed tasks.
2. ALB health checks route traffic to healthy tasks.
3. No operator action required.

#### Scenario B: Service Degradation
1. Scale the ECS service (`aws ecs update-service --desired-count <N>`).
2. Monitor health checks and CloudWatch metrics.
3. If container image is compromised: deploy new task definition with a known-good image from ECR.

#### Scenario C: Region DR
1. Terraform apply in DR region with `dr_active=true`:
   - ECS services scale to production desired count.
   - Task definitions reference ECR images (cross-region replicated).
   - Service connects to DR RDS and Redis.
2. Validate health check endpoints return 200.
3. Run smoke tests against DR API.

### 6.4 S3 Recovery

#### Scenario A: Object Deletion (Accidental)
1. S3 versioning preserves deleted objects as noncurrent versions.
2. Restore by copying the noncurrent version back to current: `aws s3api copy-object --copy-source bucket/key?versionId=xxx`.

#### Scenario B: Region Failure
1. S3 cross-region replication has already copied objects to the DR region bucket.
2. Update application configuration to use the DR region bucket names.
3. **Audit bucket**: Replicated in near real-time; minimal data loss.
4. **Document bucket**: Replicated in near real-time.

### 6.5 Route53 DNS Failover

1. Route53 health checks monitor the primary ALB endpoint.
2. If the health check fails for the configured threshold (3 consecutive failures, 30-second interval):
   - Route53 automatically updates the DNS record to point to the DR ALB IP.
   - DNS TTL is set to 60 seconds for fast propagation.
3. The DR ALB routes traffic to DR ECS services.
4. **Important**: DNS failover is automatic but requires that the DR environment is activated (ECS services running, RDS restored) before Route53 failover routes traffic.

### 6.6 Cognito Recovery

#### Region Failure
1. The DR Cognito user pool contains a synchronized copy of user data.
2. Update application OIDC configuration to point to the DR Cognito user pool.
3. Existing user sessions (JWT tokens) will be invalid — users must re-authenticate.
4. **Impact**: All users must log in again. MFA devices remain configured in the DR pool.

## 7. Failover Decision Matrix

| Scenario | Auto-Failover? | Decision Authority | Activation Procedure |
|----------|---------------|-------------------|---------------------|
| Single AZ failure | Yes (RDS, Redis, ECS) | N/A (automatic) | No action |
| ALB health check failure | Yes (Route53) | N/A (automatic) | DR must be pre-activated |
| Single service degradation | No | CTO / On-call | Scale up or redeploy specific service |
| RDS data corruption | No | CTO + Security Officer | Point-in-time recovery; assess data integrity |
| Full region failure | No | CEO + CTO | Full DR activation procedure |
| Ransomware | No | CEO + Security Officer | Isolate, assess, restore from clean backup |
| Extended AWS outage (>4 hours) | No | CEO | Evaluate: wait vs. DR failover |

### 7.1 Full DR Failover Procedure

1. **Decision**: CEO authorizes full DR failover (with CTO and Security Officer input).
2. **Communication**: Notify all personnel, update status page to "Major Incident — DR Failover".
3. **RDS**: Restore from most recent cross-region snapshot in DR region (60-90 minutes).
4. **Secrets**: Verify Secrets Manager replicas are current in DR region.
5. **ECS**: `terraform apply -var="dr_active=true"` in DR environment (15-30 minutes).
6. **Cognito**: Verify DR user pool is accessible; update application OIDC config.
7. **DNS**: Verify Route53 health check has failed-over, or manually update DNS if auto-failover has not triggered.
8. **Validation**: Run full smoke test suite against DR endpoints.
9. **Monitoring**: Confirm all CloudWatch alarms are monitoring DR resources.
10. **Communication**: Update status page: "Service Restored (DR Region)".
11. **Sustained operations**: Monitor DR environment for stability over 24 hours.

### 7.2 Failback Procedure

Once the primary region is restored:

1. Verify primary region infrastructure is healthy.
2. Restore primary RDS from a snapshot of the DR RDS (to capture data written during DR).
3. Verify data integrity in primary.
4. Gradually shift traffic back to primary via Route53 weighted routing.
5. Monitor both regions during transition.
6. Scale down DR environment once primary is confirmed stable (24 hours).
7. Resume normal cross-region replication.

## 8. Communication During DR

| Phase | Internal Communication | External Communication |
|-------|----------------------|----------------------|
| Incident detected | Slack #incident-active, PagerDuty page | Status page: "Investigating" |
| DR decision made | All-hands Slack notification | Status page: "Major Incident — DR Failover in Progress" |
| DR failover executing | Regular updates in Slack (every 15 minutes) | Status page updates (every 30 minutes) |
| DR complete, service restored | Slack confirmation | Status page: "Service Restored (DR Region)" + customer email |
| Failback complete | Slack confirmation | Status page: "Resolved" + customer email |

## 9. Testing Schedule

### 9.1 Exercise Types

| Exercise | Frequency | Scope | Participants |
|----------|-----------|-------|-------------|
| **Tabletop DR exercise** | Quarterly | Discussion-based walkthrough of DR scenarios | IRT, Engineering, DevOps |
| **Component recovery test** | Quarterly (rotating) | Test individual recovery procedures (RDS restore, ECS redeploy, S3 recovery) | DevOps + Engineering |
| **Full DR failover test** | Annually | Complete failover to DR region, run production-equivalent traffic, validate all systems | All technical staff |
| **Backup restore validation** | Monthly | Restore a random RDS snapshot; validate data integrity | DevOps |
| **DNS failover test** | Semi-annually | Simulate primary health check failure; verify Route53 fails over | DevOps |

### 9.2 Testing Documentation

Each test produces:

| Document | Contents |
|----------|---------|
| Test plan | Objectives, scope, procedures, expected outcomes, rollback plan |
| Test results | Actual outcomes, time measurements (did we meet RTO?), issues encountered |
| Gap analysis | Differences between expected and actual results; required improvements |
| Action items | Corrective actions with owners and deadlines |

### 9.3 Success Criteria

| Metric | Target |
|--------|--------|
| RDS restore completes within RTO | < 1 hour |
| ECS services healthy in DR within RTO | < 30 minutes |
| Full platform recovery within RTO | < 4 hours |
| No data loss beyond RPO | RPO met (≤ 1 hour for PHI) |
| All health checks pass | 100% |
| Smoke test suite passes | 100% |

## 10. Key Personnel Succession

### 10.1 Succession Plan

| Role | Primary | First Successor | Second Successor |
|------|---------|-----------------|------------------|
| CEO | [CEO Name] | CTO | Security Officer |
| CTO | [CTO Name] | Senior Engineer | DevOps Lead |
| Security Officer | [SO Name] | CTO | CEO |
| Incident Commander | Security Officer | CTO | Senior Engineer |
| DevOps Lead | [DevOps Name] | Senior Engineer | CTO |
| Backend Lead | [Backend Name] | Senior Engineer | CTO |

### 10.2 Knowledge Continuity

- All runbooks, procedures, and configurations are documented in the repository (not in individual heads).
- Terraform manages all infrastructure — no manual AWS Console configuration that only one person knows.
- All Secrets Manager secrets have documented purposes and rotation procedures.
- Access to AWS root account credentials is shared between CEO and Security Officer (stored in a physical safe, split custody).
- At least two people hold every critical permission (no single point of failure for access).

### 10.3 Cross-Training

- Every critical system has at least two trained operators.
- Quarterly rotation of on-call duties ensures knowledge distribution.
- DR exercises (Section 9) are used as cross-training opportunities.

## 11. Vendor Dependency Matrix

| Vendor | Service | Criticality | SLA | DR Capability | FusionEMS Mitigation |
|--------|---------|------------|-----|---------------|---------------------|
| **AWS** | Full infrastructure | Critical | 99.99% (SLA varies by service) | Multi-region (our DR responsibility) | Multi-AZ + cross-region DR |
| **AWS RDS** | Database | Critical | 99.95% (Multi-AZ) | Cross-region snapshot | Automated snapshots + cross-region copy |
| **AWS Cognito** | Authentication | Critical | 99.9% | Regional service | DR user pool in secondary region |
| **AWS S3** | Object storage | Critical | 99.9% (single region) | Cross-region replication | CRR to DR region |
| **Stripe** | Payment processing | Medium | 99.99% | Stripe manages DR | Queue billing operations during outage; retry on recovery |
| **Telnyx** | Telephony | Medium | 99.95% | Telnyx manages DR | Graceful degradation; telephony features unavailable during outage |
| **GitHub** | Source code, CI/CD | Medium | 99.9% | GitHub manages DR | Local git clones provide code availability; CI/CD paused during outage |
| **Grafana Cloud (if used)** | Monitoring dashboards | Low | 99.9% | Provider-managed | CloudWatch provides backup monitoring |
| **Domain registrar** | DNS delegation | Critical | 99.99% | Registrar-managed | Registrar failover; long TTL on NS records |

### 11.1 Vendor Communication

During a vendor outage:

- Check the vendor's status page for official updates.
- Open a support case with the vendor (AWS Premium Support for critical issues).
- Notify affected customers that the issue is vendor-related and provide estimated recovery.
- Execute FusionEMS-side mitigations (DR failover, queue operations, graceful degradation).

## 12. Plan Maintenance

### 12.1 Review Triggers

This plan is reviewed and updated:

- Annually (scheduled).
- After any DR activation or DR test (within 14 days).
- After significant infrastructure changes (new AWS services, new regions, architecture changes).
- After any incident that exposed gaps in DR capability.
- After changes to the vendor dependency matrix.

### 12.2 Maintenance Responsibilities

| Task | Owner | Frequency |
|------|-------|-----------|
| Full plan review | Security Officer + CTO | Annual |
| Contact roster update | Security Officer | Monthly |
| Terraform DR module validation | DevOps | Quarterly |
| Backup restore test | DevOps | Monthly |
| Vendor SLA review | CTO | Annual |
| Cross-training verification | CTO | Quarterly |

## 13. Compliance Mapping

| Requirement | Framework | This Plan Section |
|------------|-----------|-------------------|
| Contingency plan | HIPAA §164.308(a)(7)(i) | Sections 3-7 |
| Data backup plan | HIPAA §164.308(a)(7)(ii)(A) | Sections 4, 6 |
| Disaster recovery plan | HIPAA §164.308(a)(7)(ii)(B) | Sections 5-7 |
| Emergency mode operation plan | HIPAA §164.308(a)(7)(ii)(C) | Section 7 |
| Testing and revision procedures | HIPAA §164.308(a)(7)(ii)(D) | Section 9 |
| Availability | SOC 2 A1.1-A1.3 | Sections 3-9 |
| Recovery objectives | SOC 2 A1.2 | Section 4 |
| Business continuity | ISO 27001 A.5.29-A.5.30 | Sections 3-12 |

## 14. Related Policies

- Information Security Policy (ISP-001)
- Incident Response Plan (IRP-001)
- Encryption Policy (ENC-001)
- Data Retention and Disposal Policy (DRD-001)
- Access Control Policy (ACP-001)

## 15. Revision History

| Version | Date           | Author           | Description          |
|---------|----------------|------------------|----------------------|
| 1.0     | March 9, 2026  | Security Officer | Initial release      |

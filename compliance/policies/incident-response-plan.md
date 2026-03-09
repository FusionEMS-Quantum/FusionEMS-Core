# Incident Response Plan

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Policy ID**      | IRP-001                                    |
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
3. [Incident Classification](#3-incident-classification)
4. [Response Team](#4-response-team)
5. [Phase 1: Preparation](#5-phase-1-preparation)
6. [Phase 2: Detection and Identification](#6-phase-2-detection-and-identification)
7. [Phase 3: Triage and Escalation](#7-phase-3-triage-and-escalation)
8. [Phase 4: Containment](#8-phase-4-containment)
9. [Phase 5: Eradication](#9-phase-5-eradication)
10. [Phase 6: Recovery](#10-phase-6-recovery)
11. [Phase 7: Post-Incident Activity](#11-phase-7-post-incident-activity)
12. [Communication Plan](#12-communication-plan)
13. [HIPAA Breach Determination](#13-hipaa-breach-determination)
14. [Evidence Preservation](#14-evidence-preservation)
15. [GuardDuty Response Playbooks](#15-guardduty-response-playbooks)
16. [Testing and Exercises](#16-testing-and-exercises)
17. [Compliance Mapping](#17-compliance-mapping)
18. [Related Policies](#18-related-policies)
19. [Revision History](#19-revision-history)

---

## 1. Purpose

This Incident Response Plan (IRP) establishes the procedures for detecting, responding to, containing, eradicating, and recovering from security incidents affecting FusionEMS Quantum systems and data. FusionEMS is a 24/7 life-safety SaaS platform processing PHI for EMS, HEMS, Fire, ePCR, CAD, Fleet, Billing, MDT, and AI Analytics. An effective incident response capability is essential to minimize the impact of security events on patient care, data integrity, and service availability.

## 2. Scope

This plan applies to all security incidents affecting:

- FusionEMS platform services (production, staging, development).
- AWS infrastructure and cloud resources.
- Data processed by FusionEMS, including PHI.
- Third-party integrations (Telnyx, Stripe, NEMSIS state repositories).
- Employee and contractor devices used to access FusionEMS systems.
- Physical security events that impact information systems.

## 3. Incident Classification

### 3.1 Priority Levels

| Priority | Name | Description | Response Timeline | Examples |
|----------|------|-------------|-------------------|----------|
| **P1** | Critical | Active compromise of PHI, total service outage, active threat actor in the environment, or availability loss affecting dispatch/patient care | Response begins immediately (within 15 minutes of detection) | Confirmed data breach with PHI exfiltration; RDS compromise; complete service outage; ransomware; active unauthorized access to production |
| **P2** | High | Degraded service affecting multiple tenants, confirmed unauthorized access without PHI exposure, significant security control failure | Response begins within 1 hour | Partial service outage (API degraded, latency spike); compromised employee credentials; WAF bypass detected; MFA bypass; single database table exposed |
| **P3** | Medium | Incident affecting a single tenant, security policy violation detected, unsuccessful attack attempt requiring investigation | Response begins within 4 hours | Single-tenant data access anomaly; Cognito brute-force attempt blocked but investigation needed; insider threat investigation; malware on employee device |
| **P4** | Low | Security anomaly requiring review, minor policy violation, informational security event | Response within 24 hours | GuardDuty LOW severity finding; port scan detected and blocked; failed phishing attempt; minor configuration drift detected by AWS Config |

### 3.2 Classification Criteria

Incidents are classified based on:

- **Data impact**: Was PHI or RESTRICTED data accessed, exposed, or exfiltrated?
- **Availability impact**: Are critical services (API, database, dispatch, ePCR) unavailable or degraded?
- **Tenant impact**: How many tenants (agencies) are affected?
- **Regulatory impact**: Does the incident trigger breach notification obligations?
- **Active threat**: Is a threat actor currently active in the environment?

When in doubt, classify at the higher priority level and downgrade after triage.

## 4. Response Team

### 4.1 Incident Response Team (IRT) Roles

| Role | Primary | Backup | Responsibilities |
|------|---------|--------|-----------------|
| **Incident Commander (IC)** | Security Officer | CTO | Overall incident coordination, priority decisions, status communication, resource allocation |
| **Technical Lead** | CTO | Senior Engineer | Technical investigation, containment execution, eradication, recovery |
| **Communications Lead** | CEO | Security Officer | Customer communication, status page updates, media inquiries, regulatory notifications |
| **Security Analyst** | Security Officer | Designated Security Champion | Log analysis, forensic investigation, evidence preservation, IOC identification |
| **Infrastructure Lead** | DevOps Lead | Senior DevOps Engineer | AWS console actions, Terraform emergency changes, network containment, backup restoration |
| **Application Lead** | Backend Lead | Frontend Lead | Application-layer investigation, code-level containment (feature flags, endpoint disabling) |

### 4.2 Contact Information

An up-to-date contact roster is maintained in a secure, offline-accessible document (encrypted PDF, printed copy in the Security Officer's custody). The roster includes:

- Personal phone numbers for all IRT members.
- Escalation chain (on-call rotation).
- AWS Support contact (Premium Support).
- Legal counsel contact.
- Cyber insurance carrier contact and policy number.
- HIPAA breach reporting contacts (HHS OCR portal).
- Law enforcement contacts (FBI IC3, local field office).

This roster is reviewed and updated monthly.

## 5. Phase 1: Preparation

### 5.1 Tools and Access

The following tools must be pre-configured and accessible to the IRT:

| Tool | Purpose | Access |
|------|---------|--------|
| AWS Console + CLI | Infrastructure investigation, containment, recovery | IAM SSO roles with MFA |
| CloudWatch Logs Insights | Log querying and analysis | Security Officer, CTO, DevOps |
| CloudTrail Lake | Historical API activity analysis | Security Officer, CTO |
| GuardDuty console | Threat finding review | Security Officer, CTO |
| Security Hub | Aggregated security finding review | Security Officer, CTO |
| Grafana dashboards | Service health and performance monitoring | Engineering, DevOps |
| Prometheus | Metric queries | Engineering, DevOps |
| GitHub | Source code review, deployment history | Engineering |
| Slack (#incident channel) | Real-time incident coordination | All IRT members |
| PagerDuty / on-call system | Alerting and escalation | Security Officer, CTO, on-call engineer |

### 5.2 Runbooks

Pre-written runbooks are maintained for common incident scenarios:

| Runbook | Location | Covers |
|---------|----------|--------|
| RDS compromise response | `/backend/RUNBOOK_BILLING.txt` (billing-specific) + incident runbook repo | Database investigation, snapshot, isolation |
| Cognito account compromise | Incident runbook repo | User disable, token revocation, log review |
| S3 data exposure | Incident runbook repo | Bucket policy lockdown, access log review |
| DDoS / rate limit breach | Incident runbook repo | WAF escalation, CloudFront shield |
| Ransomware | Incident runbook repo | Isolation, backup assessment, recovery |
| Insider threat | Incident runbook repo | Account disable, log preservation, investigation |
| Third-party breach (Telnyx, Stripe) | Incident runbook repo | Credential rotation, impact assessment |

### 5.3 Training

- All IRT members complete incident response training annually.
- Tabletop exercises are conducted quarterly (Section 16).
- New engineers receive IR orientation within 30 days of onboarding.

## 6. Phase 2: Detection and Identification

### 6.1 Detection Sources

| Source | Finding Types | Alert Mechanism |
|--------|--------------|-----------------|
| **Amazon GuardDuty** | EC2/ECS compromise indicators, IAM anomalies, S3 anomalies, DNS anomalies, cryptocurrency mining, malware | CloudWatch Events → SNS → Slack + PagerDuty (HIGH/CRITICAL) |
| **AWS Security Hub** | Aggregated findings from GuardDuty, Inspector, Macie, Config, IAM Access Analyzer | Dashboard review + automated alerts for CRITICAL |
| **CloudWatch Alarms** | CPU/memory spikes, error rate increase, latency degradation, 5xx surge, login failure spike, disk usage | SNS → Slack + PagerDuty |
| **CloudTrail** | Unauthorized API calls, IAM policy changes, console sign-in anomalies, root account usage | CloudWatch Events → alerts on specific event patterns |
| **Amazon Macie** | PHI/PII detected in unauthorized S3 locations | Security Hub + direct Slack alert |
| **WAF logs** | Blocked attack attempts, rate limit triggers, rule group matches | CloudWatch + dashboard |
| **Application logs** | Authentication failures, authorization denials (OPA), application errors, anomalous request patterns | CloudWatch Logs Insights + Grafana alerts |
| **User reports** | Suspicious activity observed by users, customers, or third parties | Email to security@fusionems.com, Slack report |
| **External intelligence** | Threat feeds, vendor advisories, CVE notifications | Security Officer review |

### 6.2 Identification Criteria

An event becomes a potential incident when:

- A GuardDuty finding is classified HIGH or CRITICAL.
- An unauthorized access attempt succeeds (OPA allow for unexpected principal).
- PHI is detected outside of authorized storage locations (Macie).
- A production service experiences unexplained degradation or outage.
- Multiple related security events correlate (e.g., login failures + successful login + unusual data access).
- An employee reports suspicious activity on their account.
- A third party reports unauthorized data exposure.

## 7. Phase 3: Triage and Escalation

### 7.1 Triage Procedure

1. The on-call engineer or Security Officer receives the alert.
2. Within 15 minutes, perform initial assessment:
   - Is this a true positive or false positive?
   - What systems are affected?
   - Is PHI potentially exposed?
   - Is service availability impacted?
   - Is a threat actor currently active?
3. Assign a priority level (P1-P4) per Section 3.
4. If P1 or P2: Activate the IRT, open the Slack #incident channel, page the Incident Commander.
5. If P3 or P4: Assign to the appropriate team for investigation; notify the Security Officer.

### 7.2 Escalation Matrix

| Condition | Escalate To | Timeline |
|-----------|-------------|----------|
| Any PHI exposure | Security Officer → CEO | Immediate |
| P1 incident confirmed | Entire IRT | Immediate |
| P2 incident not resolved in 2 hours | CTO + CEO | 2 hours |
| Any potential HIPAA breach | Security Officer + Legal Counsel | Within 1 hour of determination |
| Law enforcement involvement needed | CEO + Legal Counsel | Before any law enforcement contact |
| Media inquiry about incident | CEO (sole spokesperson) | Immediate |
| AWS service disruption causing incident | DevOps → AWS Support (Premium) | Within 30 minutes |

## 8. Phase 4: Containment

### 8.1 Containment Strategy

Containment aims to limit the scope and impact of the incident while preserving evidence. Containment actions are authorized by the Incident Commander.

### 8.2 Automated Containment

The following containment actions can be triggered automatically by CloudWatch Events rules or GuardDuty auto-remediation:

| Trigger | Automated Action | Implementation |
|---------|-----------------|----------------|
| GuardDuty CRITICAL finding on ECS task | Isolate the ECS task (stop task, prevent new tasks on affected service) | Lambda function triggered by CloudWatch Events |
| Rate limit exceeded (WAF) | Block source IP via WAF IP set update | WAF rate-based rule (automatic) |
| Cognito brute-force (>20 failed attempts) | Temporary account lockout | Cognito built-in lockout policy |
| S3 public access detected | S3 Block Public Access re-enabled | AWS Config auto-remediation rule |
| IAM root account sign-in | Alert + assume compromised | CloudWatch Events → SNS → immediate page |

### 8.3 Manual Containment Actions

| Action | Command / Procedure | Authorized By |
|--------|-------------------|---------------|
| Isolate ECS service | Scale service desired count to 0, or deploy updated task def with network isolation | Technical Lead |
| Block IP in WAF | Add IP to WAF IP set block list via AWS Console or Terraform | Infrastructure Lead |
| Disable Cognito user | `AdminDisableUser` + `AdminUserGlobalSignOut` via AWS CLI | Security Analyst |
| Revoke IAM role sessions | `aws iam put-role-policy` to add deny-all; or update trust policy | Infrastructure Lead |
| Isolate RDS instance | Modify Security Group to deny all inbound; or snapshot + isolate in separate VPC | Infrastructure Lead + IC approval |
| Block external integration | Rotate webhook secret (Stripe, Telnyx), disabling the old secret | Technical Lead |
| Enable maintenance mode | Deploy frontend maintenance page via CloudFront custom error response | Infrastructure Lead |
| Isolate S3 bucket | Update bucket policy to deny all access except forensic role | Security Analyst |

### 8.4 Containment Documentation

All containment actions must be documented in the incident channel with:

- Timestamp.
- Action taken.
- Who authorized and executed.
- Expected impact on service availability.
- Rollback procedure.

## 9. Phase 5: Eradication

### 9.1 Root Cause Identification

Before eradication, the root cause must be identified or sufficiently narrowed:

- **Log analysis**: CloudTrail for API calls, CloudWatch for application behavior, VPC Flow Logs for network activity, Cognito logs for auth events.
- **Forensic imaging**: If an ECS container is compromised, preserve the container image and task metadata before termination.
- **IOC identification**: Extract indicators of compromise (IP addresses, user agents, file hashes, compromised credentials) for blocking and monitoring.
- **Timeline construction**: Build a detailed timeline of the incident from first indicator to detection to containment.

### 9.2 Eradication Actions

| Root Cause | Eradication Action |
|-----------|-------------------|
| Compromised credentials | Rotate all affected credentials in Secrets Manager; force password reset for affected Cognito users; rotate API keys |
| Vulnerable application code | Develop and test patch; deploy via emergency pipeline |
| Vulnerable dependency | Update dependency; rebuild and deploy container image |
| Infrastructure misconfiguration | Fix via Terraform; apply with peer review (expedited for P1) |
| Malware / unauthorized code | Remove malicious code; rebuild affected containers from clean image; scan all images |
| Compromised third-party integration | Rotate integration credentials; re-validate webhook signatures; contact vendor |

### 9.3 Verification

After eradication:

- Rescan affected systems with Inspector, ECR scanning, and Checkov.
- Verify the root cause is fully addressed.
- Confirm IOCs are blocked (IP blocks, credential rotations complete).
- Test affected functionality in staging before production deployment (time permitting for P1).

## 10. Phase 6: Recovery

### 10.1 Recovery Strategy

Recovery restores affected systems to normal, verified operation. The recovery strategy depends on the incident type:

### 10.2 Recovery Procedures

| System | Recovery Procedure |
|--------|-------------------|
| **ECS services** | Redeploy from clean container image; scale to normal desired count; validate health checks pass |
| **RDS database** | If compromised: restore from the last known-good automated snapshot; validate data integrity; update connection strings if endpoint changes |
| **S3 data** | If deleted: restore from S3 versioning or AWS Backup; if exfiltrated: data cannot be recalled, focus on breach notification |
| **Redis cache** | Flush and allow cache rebuild from RDS; or failover to replica |
| **Cognito** | Re-enable locked users after credential rotation; communicate password reset to affected users |
| **DNS (Route53)** | Verify DNS records, TTL; failover to DR if primary unavailable |

### 10.3 Recovery Validation

Before declaring the incident recovered:

1. All affected services report healthy via health check endpoints.
2. Grafana dashboards show normal operational metrics (error rate, latency, throughput).
3. CloudWatch alarms are in OK state.
4. No new GuardDuty findings related to the incident.
5. A sample of critical transactions is tested (e.g., create ePCR, submit billing claim, authenticate user).
6. External monitoring confirms the platform is accessible.

### 10.4 Gradual Restoration

For P1 incidents with extended outage:

1. Restore service in limited capacity (reduced scaling).
2. Monitor for 30 minutes to confirm stability.
3. Gradually increase traffic (remove maintenance page, restore DNS if failed-over).
4. Continue elevated monitoring for 24 hours.

## 11. Phase 7: Post-Incident Activity

### 11.1 Root Cause Analysis (RCA)

An RCA document must be completed within **72 hours** of incident closure for P1 and P2 incidents, and within 7 days for P3 incidents. P4 incidents do not require a formal RCA unless they reveal systemic issues.

### 11.2 RCA Document Template

| Section | Content |
|---------|---------|
| Incident ID | Unique identifier |
| Priority | P1/P2/P3/P4 |
| Summary | One-paragraph description of the incident |
| Timeline | Detailed chronological timeline from first indicator through recovery |
| Root Cause | Technical root cause identified through investigation |
| Contributing Factors | Organizational, process, or environmental factors that enabled the incident |
| Impact | Data impact (PHI exposed? how many records/patients?), availability impact (downtime duration), tenant impact (which agencies?), financial impact |
| Detection | How was the incident detected? Was detection timely? |
| Response Effectiveness | What worked well? What was slow or ineffective? |
| Remediation Actions | What was done to fix the immediate issue? |
| Preventive Actions | What changes will prevent recurrence? (specific, assigned, with deadlines) |
| Lessons Learned | Key takeaways for the team |
| HIPAA Breach Determination | Was this a reportable breach? (See Section 13) |

### 11.3 Lessons Learned Meeting

A post-incident meeting is conducted within 5 business days of incident closure for P1/P2 incidents. The meeting:

- Reviews the RCA document.
- Discusses detection, response, and recovery effectiveness.
- Assigns owners and deadlines for preventive actions.
- Updates this IRP, runbooks, and monitoring as needed.
- Is attended by all IRT members who participated in the response.
- Is blameless — focused on process improvement, not individual fault.

### 11.4 Control Updates

Post-incident preventive actions may include:

- New or updated CloudWatch alarms or GuardDuty rules.
- Updated WAF rules.
- Updated OPA policies.
- New Checkov checks.
- Revised access controls.
- Updated runbooks.
- Updated this IRP.

All control updates are tracked in the RCA preventive actions and verified as complete.

## 12. Communication Plan

### 12.1 Internal Communication

| Channel | Use | Audience |
|---------|-----|----------|
| Slack #incident-active | Real-time coordination during active incident | IRT members only (private channel) |
| Slack #incident-updates | Status updates for broader team | Engineering + leadership |
| PagerDuty | Alerting and escalation | On-call, IRT |
| Email | Formal notification, RCA distribution | All affected personnel |
| Video call | Complex coordination during P1 | IRT members |

### 12.2 External Communication

| Audience | Method | Timeline | Content |
|----------|--------|----------|---------|
| Affected customers (P1) | Status page + email | Within 1 hour of P1 confirmation | Acknowledgment of issue, impact scope, estimated resolution |
| Affected customers (P2) | Status page + email | Within 4 hours | Acknowledgment, impact, workaround if available |
| All customers (P1 resolved) | Status page + email | Within 2 hours of resolution | Resolution confirmation, summary, follow-up timeline |
| HHS (if HIPAA breach) | HHS OCR breach portal | Per BNP-001 timelines (60 days) | Per BNP-001 |
| Individuals (if HIPAA breach) | Written notification | Per BNP-001 timelines (60 days) | Per BNP-001 |
| Media | Press statement via CEO only | As needed | Coordinated with legal counsel |
| Law enforcement | Formal report via CEO + legal | As needed | Coordinated with legal counsel |

### 12.3 Communication Principles

- **Accuracy over speed**: Do not speculate publicly. Confirm facts before external communication.
- **Transparency**: Communicate what happened, what is being done, and what customers should do.
- **Coordination**: All external communications are approved by the Incident Commander and Communications Lead.
- **Single voice**: Only the designated spokesperson communicates with media.
- **Regulatory compliance**: HIPAA breach notifications follow the Breach Notification Procedure (BNP-001).

## 13. HIPAA Breach Determination

### 13.1 Breach Assessment Checklist

For every P1 and P2 incident involving potential PHI exposure, the Security Officer completes the following assessment:

**Step 1: Was PHI involved?**
- [ ] Did the incident involve PHI (identifiable health information)?
- [ ] If no → Not a HIPAA breach. Document finding and close.

**Step 2: Was the PHI unsecured?**
- [ ] Was the PHI encrypted with an approved algorithm at the time of exposure?
- [ ] If PHI was encrypted per HIPAA/HHS guidance and the key was not compromised → Not a breach (Safe Harbor). Document and close.

**Step 3: Does an exception apply?**
- [ ] Unintentional acquisition by workforce member acting in good faith, within scope of authority, no further use/disclosure?
- [ ] Inadvertent disclosure by authorized person to another authorized person within the same organization?
- [ ] Unauthorized person would not reasonably be able to retain the information?
- [ ] If any exception applies → Not a reportable breach. Document and close.

**Step 4: Four-Factor Risk Assessment**
If no exception applies, perform the four-factor test:

| Factor | Assessment |
|--------|-----------|
| 1. Nature and extent of PHI involved (what types of identifiers, clinical data?) | [Assess] |
| 2. Unauthorized person who used/received the PHI (known? malicious? another CE/BA?) | [Assess] |
| 3. Was PHI actually acquired or viewed? (vs. opportunity to access) | [Assess] |
| 4. Extent to which risk has been mitigated (data recovered? access terminated? assurances obtained?) | [Assess] |

**Determination**: If the four-factor assessment shows a low probability that PHI was compromised → Not a reportable breach. If probability is not low → Reportable breach. Invoke BNP-001.

All breach assessments are documented and retained for 6 years.

## 14. Evidence Preservation

### 14.1 Preservation Principles

- **Do not destroy evidence.** Containment actions must preserve evidence before isolating systems.
- **Chain of custody.** All evidence must have documented handling (who collected it, when, how it was stored).
- **Immutability.** Evidence is copied to a dedicated forensic S3 bucket with Object Lock.

### 14.2 Evidence Types

| Evidence | Collection Method | Storage |
|----------|------------------|---------|
| CloudTrail logs | Already in S3 (immutable via bucket policy) | CloudTrail S3 bucket |
| CloudWatch Logs | Export to S3 using `CreateExportTask` | Forensic S3 bucket |
| VPC Flow Logs | Already in CloudWatch / S3 | VPC Flow Logs destination |
| GuardDuty findings | Export via API or Security Hub | Forensic S3 bucket (JSON export) |
| RDS data snapshot | Create manual snapshot before any DB changes | RDS snapshot (encrypted, dedicated) |
| ECS task metadata | Describe and record task definition, network config, environment | Forensic S3 bucket |
| Container image | Copy image digest to forensic ECR repository | Forensic ECR repo |
| WAF logs | Already in S3 / CloudWatch | WAF log bucket |
| Application request logs | Export from CloudWatch | Forensic S3 bucket |
| Cognito user events | Export from Cognito `AdminListUserAuthEvents` | Forensic S3 bucket |

### 14.3 Forensic S3 Bucket

A dedicated forensic evidence bucket (`fusionems-{env}-forensic-evidence`) is configured with:

- KMS encryption with a dedicated forensic key.
- S3 Object Lock in Compliance mode (prevents deletion even by root).
- Access restricted to Security Officer IAM role only.
- Versioning enabled.
- CloudTrail data events logging all access.

## 15. GuardDuty Response Playbooks

### 15.1 High-Priority Finding Types

| GuardDuty Finding Type | Severity | Immediate Action |
|-----------------------|----------|-----------------|
| `Recon:EC2/PortProbeUnprotectedPort` | Medium | Review Security Group rules; verify no unintended exposure; block source IP in WAF if external |
| `UnauthorizedAccess:EC2/TorClient` or `TorRelay` | High | Isolate affected ECS task immediately; investigate whether task is compromised; rebuild from clean image |
| `UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B` | High | Verify login was legitimate; if not, disable IAM user, revoke sessions, rotate credentials |
| `Trojan:EC2/BlackholeTraffic` | High | Isolate affected task; investigate for malware; rebuild from clean image |
| `CryptoCurrency:EC2/BitcoinTool.B` | High | Isolate immediately; containerimage is compromised; rebuild; investigate supply chain |
| `Backdoor:EC2/C&CActivity.B` | Critical | P1 incident — isolate, preserve evidence, full investigation |
| `Exfiltration:S3/AnomalousBehavior` | High | Review S3 access logs; identify source principal; block if unauthorized; assess PHI exposure |
| `Impact:S3/AnomalousBehavior.Delete` | High | Verify S3 versioning is protecting data; investigate source; assess data loss |
| `Stealth:IAMUser/CloudTrailLoggingDisabled` | Critical | P1 incident — re-enable CloudTrail immediately; investigate who disabled it; assume compromise |
| `PrivilegeEscalation:IAMUser/AdministrativePermissions` | High | Review IAM change; revert if unauthorized; investigate source |
| `UnauthorizedAccess:S3/TorIPCaller` | High | Block Tor exit nodes in WAF; investigate accessed data; assess PHI exposure |
| `Policy:S3/BucketBlockPublicAccessDisabled` | High | Re-enable Block Public Access immediately; investigate who disabled it |

### 15.2 General GuardDuty Response Procedure

1. Security Officer reviews the finding in the GuardDuty console.
2. Determine if the finding is a true positive (correlate with other signals — CloudTrail, application logs).
3. If true positive: classify priority, activate IRT if P1/P2, execute containment.
4. If false positive: suppress the finding with documented justification; update suppression filter.
5. All HIGH and CRITICAL findings are reviewed within 1 hour; MEDIUM within 4 hours; LOW within 24 hours.

## 16. Testing and Exercises

### 16.1 Tabletop Exercises

| Exercise | Frequency | Participants | Scenario Examples |
|----------|-----------|-------------|-------------------|
| Tabletop (discussion-based) | Quarterly | IRT members | Data breach with PHI exposure; ransomware; insider threat; third-party breach; DDoS during major incident response |
| Functional (hands-on) | Semi-annually | Engineering + DevOps | Simulated GuardDuty finding → containment → recovery on staging environment |
| Full DR test | Annually | IRT + Engineering + DevOps | Complete DR failover to backup region (per BCP-001) |

### 16.2 Exercise Documentation

Each exercise produces:

- Summary of scenario and objectives.
- Observations (what went well, what needs improvement).
- Action items with owners and deadlines.
- Updates to this IRP and runbooks.

### 16.3 Metrics

IRP effectiveness is measured by:

| Metric | Target |
|--------|--------|
| Mean Time to Detect (MTTD) | < 15 minutes for P1 |
| Mean Time to Respond (MTTR) | < 30 minutes for P1 |
| Mean Time to Contain (MTTC) | < 1 hour for P1 |
| Mean Time to Recover | < 4 hours for P1 |
| RCA completion rate | 100% for P1/P2 within 72 hours |
| Exercise completion | 4 tabletop, 2 functional, 1 DR per year |

## 17. Compliance Mapping

| Requirement | Framework | This Plan Section |
|------------|-----------|-------------------|
| Security incident procedures | HIPAA §164.308(a)(6)(i) | Sections 3-11 |
| Response and reporting | HIPAA §164.308(a)(6)(ii) | Sections 7, 12 |
| Breach determination | HIPAA §164.402 | Section 13 |
| Incident response | SOC 2 CC7.3, CC7.4 | Sections 3-11 |
| Communication | SOC 2 CC2.3 | Section 12 |
| Incident management | ISO 27001 A.5.24-A.5.28 | Sections 3-11 |

## 18. Related Policies

- Information Security Policy (ISP-001)
- Breach Notification Procedure (BNP-001)
- Business Continuity / Disaster Recovery Plan (BCP-001)
- Access Control Policy (ACP-001)
- Vulnerability Management Policy (VMP-001)
- Data Classification Policy (DCP-001)

## 19. Revision History

| Version | Date           | Author           | Description          |
|---------|----------------|------------------|----------------------|
| 1.0     | March 9, 2026  | Security Officer | Initial release      |

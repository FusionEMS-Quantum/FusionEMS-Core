# Breach Notification Procedure

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Policy ID**      | BNP-001                                    |
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
3. [HIPAA Breach Definitions](#3-hipaa-breach-definitions)
4. [Breach Assessment Methodology](#4-breach-assessment-methodology)
5. [Notification Timelines](#5-notification-timelines)
6. [Notification Content Requirements](#6-notification-content-requirements)
7. [Notification Procedures by Audience](#7-notification-procedures-by-audience)
8. [BAA Breach Chain](#8-baa-breach-chain)
9. [Documentation Requirements](#9-documentation-requirements)
10. [Breach Log](#10-breach-log)
11. [State Law Addendum](#11-state-law-addendum)
12. [Post-Breach Actions](#12-post-breach-actions)
13. [Roles and Responsibilities](#13-roles-and-responsibilities)
14. [Compliance Mapping](#14-compliance-mapping)
15. [Related Policies](#15-related-policies)
16. [Revision History](#16-revision-history)

---

## 1. Purpose

This Breach Notification Procedure establishes the process for evaluating potential breaches of unsecured Protected Health Information (PHI) and executing timely notifications as required by the HIPAA Breach Notification Rule (45 CFR §§164.400–414) and applicable state laws. FusionEMS Quantum operates as a Business Associate (BA) processing PHI on behalf of Covered Entity (CE) customers across EMS, HEMS, Fire, ePCR, CAD, Fleet, Billing, MDT, and AI Analytics workflows. This procedure ensures that FusionEMS meets all obligations in the breach notification chain — from discovery through final regulatory reporting.

## 2. Scope

This procedure applies to:

- All incidents involving potential unauthorized access, use, disclosure, or loss of PHI managed by FusionEMS systems.
- All FusionEMS environments where PHI is processed or stored (production).
- The notification chain from FusionEMS (BA) to Covered Entity customers, and from Covered Entities to affected individuals and HHS.
- Any breach by a FusionEMS subprocessor (e.g., AWS as infrastructure provider under BAA).

## 3. HIPAA Breach Definitions

### 3.1 Breach

Under HIPAA (45 CFR §164.402), a **breach** is the acquisition, access, use, or disclosure of PHI in a manner not permitted by the HIPAA Privacy Rule that compromises the security or privacy of the PHI.

The term "compromises the security or privacy" means it poses a significant risk of financial, reputational, or other harm to the individual.

### 3.2 Unsecured PHI

**Unsecured PHI** is PHI that has not been rendered unusable, unreadable, or indecipherable to unauthorized persons through the use of approved technologies:

- **Encryption**: PHI encrypted per NIST SP 800-111 guidance using AES-128 or AES-256, where the encryption key was not compromised.
- **Destruction**: PHI on paper that has been shredded or on electronic media that has been cleared, purged, or destroyed per NIST SP 800-88.

**Safe Harbor**: If PHI was encrypted per HIPAA guidance and the encryption key was not compromised, the incident is not a breach and notification is not required. FusionEMS encryption practices (AES-256 via KMS for all data at rest, TLS 1.2+ for data in transit) qualify for Safe Harbor when the KMS key is not compromised.

### 3.3 Exceptions to the Breach Definition

A use or disclosure of PHI is NOT a breach if:

1. **Unintentional acquisition by workforce member**: Made in good faith, within scope of authority, and the PHI is not further used or disclosed impermissibly.
2. **Inadvertent disclosure between authorized persons**: Made by a person authorized to access PHI to another person within the organization authorized to access PHI, and the PHI is not further used or disclosed impermissibly.
3. **Inability to retain**: The unauthorized person to whom the disclosure was made would not reasonably be able to retain the information (e.g., transient exposure in logs that were immediately overwritten).

### 3.4 Discovery

A breach is treated as "discovered" on the first day the breach is known, or by exercising reasonable diligence would have been known, to any person (other than the person committing the breach) who is a workforce member or agent of FusionEMS. This includes automated detection by GuardDuty, Macie, CloudWatch alarms, or any security monitoring tool.

## 4. Breach Assessment Methodology

### 4.1 Four-Factor Risk Assessment

When a potential breach is identified that does not qualify for an exception (Section 3.3) or Safe Harbor (Section 3.2), the Security Officer conducts a four-factor risk assessment to determine if the probability of PHI compromise is low:

#### Factor 1: Nature and Extent of PHI Involved

| Question | Assessment Guidance |
|----------|-------------------|
| What types of PHI were involved? | Higher risk: SSN, financial data, diagnostic codes, clinical narratives. Lower risk: name and date of service only. |
| How many records/patients were affected? | Higher risk: large volume. Lower risk: single record. |
| What identifiers were included? | More identifiers = higher risk of re-identification and harm. |
| What clinical data was included? | Sensitive diagnoses (behavioral health, substance abuse, HIV) carry higher risk. |

#### Factor 2: Unauthorized Person Who Received the PHI

| Question | Assessment Guidance |
|----------|-------------------|
| Who was the unauthorized recipient? | Known BA/CE employee (lower risk) vs. unknown external actor (higher risk). |
| Did the recipient have an obligation to protect the PHI? | Other healthcare entity under HIPAA (lower risk) vs. public exposure (higher risk). |
| Was the disclosure to a malicious actor? | Intentional exfiltration by threat actor = high risk. |
| Can the recipient be identified and contacted? | If contactable, assurances can be obtained (lower risk). |

#### Factor 3: Was PHI Actually Acquired or Viewed?

| Question | Assessment Guidance |
|----------|-------------------|
| Is there evidence the PHI was actually accessed or viewed? | Access logs show the data was queried/downloaded = higher risk. |
| Was there only opportunity to access (e.g., system exposure without evidence of actual access)? | No evidence of access = lower risk. |
| Were there forensic indicators of data exfiltration? | Unusual outbound data transfer, S3 GetObject logs = higher risk. |

#### Factor 4: Extent to Which Risk Has Been Mitigated

| Question | Assessment Guidance |
|----------|-------------------|
| Was the PHI recovered or returned? | Data deleted/recovered from unauthorized location = lower risk. |
| Were assurances obtained from the recipient? | Written assurance of non-retention and non-disclosure = lower risk. |
| Were compensating controls applied? | Credential rotation, system patching, access revocation = some mitigation. |
| Can the organization verify the mitigation was effective? | Verified deletion > verbal assurance. |

### 4.2 Determination

After evaluating all four factors:

- If the assessment demonstrates a **low probability** that PHI was compromised → **Not a reportable breach.** Document the assessment and retain for 6 years.
- If the assessment shows the probability is **not low** (or is indeterminate) → **Reportable breach.** Proceed with notification procedures.

FusionEMS presumes a breach unless the four-factor assessment demonstrates low probability of compromise. The burden is on FusionEMS to demonstrate no breach occurred.

## 5. Notification Timelines

### 5.1 Business Associate to Covered Entity

FusionEMS, as a Business Associate, must notify affected Covered Entity customers of a breach **without unreasonable delay** and no later than **60 calendar days** from the date of discovery.

FusionEMS targets notification to Covered Entities within **10 business days** of breach confirmation to give Covered Entities adequate time to complete their own notification obligations.

### 5.2 Covered Entity to Individuals

Covered Entities must notify affected individuals **without unreasonable delay** and no later than **60 calendar days** from the date they discover (or are notified of) the breach.

FusionEMS will provide the Covered Entity with all information necessary to issue individual notifications.

### 5.3 Covered Entity to HHS

| Scenario | Timeline |
|----------|----------|
| Breach affecting **500 or more** individuals | Notification to HHS without unreasonable delay, no later than **60 days** from discovery. Submitted via HHS OCR breach portal. |
| Breach affecting **fewer than 500** individuals | Notification to HHS within **60 days of the end of the calendar year** in which the breach was discovered (annual log submission). |

### 5.4 Covered Entity to Media

If the breach affects **500 or more** residents of a single state or jurisdiction, the Covered Entity must notify prominent media outlets serving that state within **60 days** of discovery.

### 5.5 FusionEMS Internal Milestones

| Milestone | Target |
|-----------|--------|
| Breach discovered (detection) | Day 0 |
| Initial assessment complete | Day 0–2 |
| Four-factor risk assessment complete | Day 2–5 |
| Breach determination finalized | Day 5–7 |
| Covered Entity notification sent | Day 7–10 |
| Support CE with individual notification content | Day 10–20 |
| All documentation finalized | Day 30 |
| HHS breach portal submission support (if applicable) | Day 30–60 |

## 6. Notification Content Requirements

### 6.1 Covered Entity Notification (from FusionEMS)

FusionEMS's notification to affected Covered Entities must include:

| Required Element | Content |
|-----------------|---------|
| Date of breach / date of discovery | Specific dates or best available estimate |
| Description of the breach | What happened, how it was discovered, what systems were involved |
| Types of PHI involved | List of data elements (e.g., patient names, DOB, SSN, diagnosis codes, treatment records) |
| Number of individuals affected | Exact count or best estimate, broken down by tenant/agency |
| Actions taken | Containment, eradication, mitigation steps completed |
| Actions recommended | Steps the CE should take (e.g., monitor, notify individuals, credit monitoring) |
| Contact information | Security Officer name, email, phone for follow-up questions |
| Supporting data for individual notifications | Patient list per agency, PHI elements per patient, recommended notification language |

### 6.2 Individual Notification (issued by Covered Entity, supported by FusionEMS)

FusionEMS will provide Covered Entities with draft notification content including:

| Required Element | HIPAA Requirement (§164.404(c)) |
|-----------------|-------------------------------|
| Description of breach | Brief description of what happened, including dates |
| Types of PHI involved | Categories of unsecured PHI involved (not the actual data) |
| Protective steps for individuals | Steps individuals should take (e.g., monitor EOBs, request credit report, change credentials if applicable) |
| FusionEMS actions | What FusionEMS has done to investigate and mitigate |
| Contact information | Point of contact for questions (typically the Covered Entity, with FusionEMS Security Officer backup) |

### 6.3 Notification Delivery Methods

| Audience | Primary Method | Substitute Method |
|----------|---------------|-------------------|
| Covered Entity (from FusionEMS) | Encrypted email to designated privacy/compliance contact per BAA | Phone call + certified mail |
| Individuals (from CE) | First-class mail to last known address | Email if individual has agreed to electronic notice; substitute notice for outdated contact info |
| HHS (from CE) | HHS OCR breach portal (ocrportal.hhs.gov) | N/A |
| Media (from CE) | Press release to prominent state media | N/A |

## 7. Notification Procedures by Audience

### 7.1 Covered Entity Notification Procedure

1. Security Officer drafts the breach notification letter using the template in Section 6.1.
2. CEO reviews and approves the notification.
3. Legal counsel reviews the notification for accuracy and completeness.
4. Notification is sent to each affected Covered Entity's designated BAA contact via encrypted email.
5. Delivery is confirmed (read receipt or follow-up phone call).
6. A copy of the notification is retained in the breach log.

### 7.2 Support for Individual Notification

1. FusionEMS provides each affected Covered Entity with:
   - List of affected patients (members of that agency/tenant).
   - PHI elements exposed per patient.
   - Draft individual notification letter.
   - FAQ document for call center support.
2. If the Covered Entity has contracted FusionEMS to handle individual notification: FusionEMS mails notifications on behalf of the CE (rare; typically the CE handles this directly).
3. FusionEMS offers credit monitoring/identity protection services to affected individuals when the breach includes SSN or financial identifiers (funded by FusionEMS if the breach was caused by FusionEMS systems).

### 7.3 HHS Notification Support

For Covered Entities reporting to HHS:

- FusionEMS provides all required data elements for the HHS breach portal submission.
- FusionEMS retains its own records of the breach for its own compliance purposes.
- If FusionEMS independently determines a breach, it also files its own report with HHS as a BA (per BAA terms, if applicable).

## 8. BAA Breach Chain

FusionEMS operates in a multi-party BAA chain. The notification flow for a breach originating at any point in the chain is:

### 8.1 Breach at Subprocessor (e.g., AWS)

```
AWS (subprocessor) → FusionEMS (BA) → Covered Entity → Individuals + HHS
```

1. AWS notifies FusionEMS of a breach under the AWS BAA terms.
2. FusionEMS assesses the impact on FusionEMS-managed PHI.
3. FusionEMS notifies affected Covered Entities per Section 7.1.
4. Covered Entities notify individuals and HHS per their own procedures.

### 8.2 Breach at FusionEMS

```
FusionEMS (BA) → Covered Entity → Individuals + HHS
```

1. FusionEMS discovers and confirms the breach.
2. FusionEMS notifies affected Covered Entities per Section 7.1.
3. Covered Entities notify individuals and HHS.

### 8.3 Breach at Covered Entity

```
Covered Entity → Individuals + HHS (FusionEMS involvement only if requested)
```

If a Covered Entity experiences a breach of PHI stored in FusionEMS (e.g., due to compromised CE credentials), FusionEMS:

- Provides log data and forensic support to the CE for investigation.
- Is not responsible for notification (the CE is the upstream responsible party).
- Documents its support activities.

### 8.4 Other Subprocessor BAA Chain

| Subprocessor | BAA Status | Breach Flow |
|-------------|-----------|-------------|
| AWS | BAA in place | AWS → FusionEMS → CE |
| Stripe | BAA in place (per Stripe Healthcare terms) | Stripe → FusionEMS → CE |
| Telnyx | BAA in place (if processing PHI) | Telnyx → FusionEMS → CE |
| State NEMSIS Systems | DUA/BAA per state | State → FusionEMS → CE (if applicable) |

## 9. Documentation Requirements

### 9.1 Required Documentation

HIPAA requires that breach documentation be retained for **6 years** from the date of the breach or the date of the last action taken in response to the breach, whichever is later.

All of the following must be documented and retained:

| Document | Description |
|----------|-------------|
| Incident report | Full incident report from IRP-001 |
| Four-factor risk assessment | Completed assessment worksheet per Section 4 |
| Breach determination | Written determination (breach / not breach) with rationale |
| Notification letters | Copies of all notifications sent to CEs |
| Individual notification support | Draft letters, patient lists (per agency) |
| HHS submission | Copy of HHS breach portal submission (if applicable) |
| Remediation evidence | Evidence of containment, eradication, and preventive actions |
| Communication log | Record of all communications with CEs, legal, HHS |
| Timeline | Detailed timeline from discovery through notification completion |

### 9.2 Storage

All breach documentation is stored in the forensic evidence S3 bucket (`fusionems-{env}-forensic-evidence`) with:

- KMS encryption.
- S3 Object Lock in Compliance mode (6-year retention minimum).
- Access restricted to Security Officer.

## 10. Breach Log

The Security Officer maintains a breach log that records all potential and confirmed breaches. This log supports the annual HHS submission for breaches affecting fewer than 500 individuals and provides a historical record for compliance audits.

### 10.1 Breach Log Template

| Field | Description |
|-------|-------------|
| `log_id` | Unique identifier (BL-YYYY-NNN) |
| `date_discovered` | Date the potential breach was discovered |
| `date_reported` | Date the breach was reported to affected CEs |
| `description` | Brief description of the incident |
| `phi_types` | Types of PHI involved |
| `individuals_affected` | Number of individuals affected |
| `tenants_affected` | Agency/tenant names and IDs |
| `four_factor_result` | Low probability / Not low probability |
| `breach_determination` | Breach / Not breach |
| `safe_harbor` | Yes (encrypted) / No |
| `notifications_sent` | CE, individuals, HHS, media (as applicable) |
| `notification_dates` | Dates each notification was sent |
| `remediation_summary` | Brief description of corrective actions |
| `documentation_location` | S3 path to full documentation package |
| `status` | Open / Closed |
| `closure_date` | Date the breach response is finalized |

### 10.2 Annual HHS Submission

By March 1 of each calendar year, the Security Officer compiles all breaches from the prior calendar year affecting fewer than 500 individuals and submits them to HHS via the OCR breach portal. The breach log provides the source data for this annual submission.

## 11. State Law Addendum

### 11.1 General Obligation

In addition to HIPAA, FusionEMS must comply with state breach notification laws in every state where affected individuals reside. State laws may impose requirements that are more stringent than HIPAA (e.g., shorter timelines, broader notification triggers, specific content requirements).

### 11.2 Wisconsin-Specific Requirements

As FusionEMS Quantum is headquartered in Wisconsin, the following Wisconsin-specific requirements apply:

| Requirement | Wisconsin Statute (Wis. Stat. §134.98) |
|-------------|----------------------------------------|
| **Trigger** | Unauthorized acquisition of personal information (name + SSN, driver's license, financial account number, or DNA profile) |
| **Timeline** | Notification within a reasonable time, no longer than **45 days** after determination of unauthorized acquisition |
| **Content** | What happened, types of information involved, what entity is doing, contact information |
| **To whom** | Affected Wisconsin residents |
| **Regulator notification** | Not explicitly required by statute (but notification to consumer reporting agencies is required if >1,000 residents affected) |
| **Encryption safe harbor** | Information that is encrypted is excluded from the definition of "personal information" for breach notification purposes |

**Note**: Wisconsin's 45-day timeline is shorter than HIPAA's 60-day timeline. FusionEMS uses the more restrictive timeline (45 days for Wisconsin residents, 60 days for HIPAA compliance to HHS/CEs).

### 11.3 Multi-State Obligations

When a breach affects individuals in multiple states, the Security Officer:

1. Identifies all states with affected residents.
2. Reviews the breach notification requirements for each applicable state.
3. Applies the most restrictive timeline and content requirements.
4. Ensures the Covered Entity is informed of state-specific obligations (since CEs typically handle individual notification).
5. Maintains a state breach notification law reference matrix (updated annually by legal counsel).

## 12. Post-Breach Actions

### 12.1 Immediate Actions

- Confirm containment and eradication per IRP-001.
- Verify no ongoing unauthorized access.
- Complete all required notifications within timelines.

### 12.2 Remediation

- Implement all preventive actions identified in the RCA (per IRP-001).
- Update security controls, access policies, and monitoring as identified.
- Conduct a follow-up vulnerability assessment on affected systems.

### 12.3 Compliance Review

- Review and update this procedure, IRP-001, and related policies based on lessons learned.
- Assess whether the breach indicates a systemic issue requiring broader remediation.
- Strengthen training programs if the breach resulted from human error.

### 12.4 Credit Monitoring and Identity Protection

If the breach involves SSN or financial identifiers:

- FusionEMS funds credit monitoring and identity protection services for affected individuals for a minimum of 12 months.
- Services are offered through the Covered Entity's notification to individuals.
- FusionEMS contracts with a qualified identity protection vendor.

## 13. Roles and Responsibilities

| Role | Responsibility |
|------|---------------|
| **Security Officer** | Leads breach assessment, four-factor analysis, notification drafting, breach log maintenance, HHS submission support, documentation retention |
| **CEO** | Approves breach notifications, authorizes credit monitoring expenditure, sole media spokesperson |
| **Legal Counsel** | Reviews breach determination, notification content, advises on state law requirements, engages with regulators |
| **CTO** | Provides technical investigation support, containment and eradication execution, forensic evidence collection |
| **Communications Lead** | Drafts customer-facing communications, manages status page updates |
| **Covered Entity (Customer)** | Receives notification from FusionEMS, notifies individuals and HHS, coordinates with FusionEMS on investigation |

## 14. Compliance Mapping

| Requirement | Framework | This Procedure Section |
|------------|-----------|----------------------|
| Breach notification (BA to CE) | HIPAA §164.410 | Sections 5, 7 |
| Breach notification (CE to individuals) | HIPAA §164.404 | Section 6 |
| Breach notification (CE to HHS) | HIPAA §164.408 | Section 5.3 |
| Breach notification (CE to media) | HIPAA §164.406 | Section 5.4 |
| Breach documentation | HIPAA §164.414(b), §164.530(j) | Section 9 |
| Risk assessment | HIPAA §164.402(2) | Section 4 |
| Incident communication | SOC 2 CC7.4 | Sections 5-8 |
| Breach management | ISO 27001 A.5.26 | Sections 3-12 |

## 15. Related Policies

- Information Security Policy (ISP-001)
- Incident Response Plan (IRP-001)
- Access Control Policy (ACP-001)
- Data Classification Policy (DCP-001)
- Encryption Policy (ENC-001)
- Data Retention and Disposal Policy (DRD-001)

## 16. Revision History

| Version | Date           | Author           | Description          |
|---------|----------------|------------------|----------------------|
| 1.0     | March 9, 2026  | Security Officer | Initial release      |

# Acceptable Use Policy

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Policy ID**      | AUP-001                                    |
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
3. [Acceptable Use of Company Systems](#3-acceptable-use-of-company-systems)
4. [Prohibited Activities](#4-prohibited-activities)
5. [Personal Use](#5-personal-use)
6. [Email and Messaging](#6-email-and-messaging)
7. [Social Media](#7-social-media)
8. [Bring Your Own Device (BYOD)](#8-bring-your-own-device-byod)
9. [Monitoring and Privacy](#9-monitoring-and-privacy)
10. [Software and Licensing](#10-software-and-licensing)
11. [Physical Security](#11-physical-security)
12. [Consequences of Violation](#12-consequences-of-violation)
13. [Acknowledgment](#13-acknowledgment)
14. [Related Policies](#14-related-policies)
15. [Revision History](#15-revision-history)

---

## 1. Purpose

This Acceptable Use Policy (AUP) defines the boundaries for authorized use of FusionEMS Quantum information systems, networks, and data. FusionEMS is a life-safety SaaS platform processing Protected Health Information (PHI) for EMS, HEMS, Fire, ePCR, CAD, Fleet, Billing, MDT, and AI Analytics operations. Improper use of these systems can expose patient data, disrupt emergency response operations, and create legal liability. This policy ensures that all personnel understand their obligations when interacting with FusionEMS resources.

## 2. Scope

This policy applies to:

- All employees, contractors, consultants, and temporary workers of FusionEMS Quantum.
- All devices (company-owned and personal) used to access FusionEMS systems.
- All FusionEMS platform resources, including but not limited to:
  - AWS infrastructure (ECS, RDS, S3, ElastiCache, CloudFront, and all other services).
  - Source code repositories (GitHub).
  - CI/CD pipelines (GitHub Actions, ECR).
  - Internal communication tools (Slack, email).
  - Development environments (codespaces, local development).
  - Production, staging, and development environments.
  - Administrative dashboards (AWS Console, Grafana, Prometheus).
  - Third-party services integrated into FusionEMS (Telnyx, Stripe, OpenTelemetry).

## 3. Acceptable Use of Company Systems

### 3.1 General Principles

FusionEMS Quantum systems are provided to enable personnel to perform their job responsibilities. All use must be:

- **Authorized**: Users may only access systems, data, and environments for which they have been explicitly granted access per the Access Control Policy (ACP-001).
- **Professional**: Use must be consistent with the Organization's mission of providing reliable, secure public safety technology.
- **Lawful**: Use must comply with all applicable federal, state, and local laws, including HIPAA, the Computer Fraud and Abuse Act, and the Electronic Communications Privacy Act.
- **Purposeful**: System access should serve a legitimate business function.

### 3.2 Permitted Activities

- Accessing FusionEMS production systems for authorized operational duties (deployment, monitoring, incident response).
- Accessing development and staging environments for software development, testing, and quality assurance.
- Using corporate email and Slack for business communications.
- Accessing AWS Console resources for which the user holds valid IAM/SSO credentials.
- Accessing Grafana dashboards and Prometheus metrics for performance monitoring.
- Using GitHub for source code management, code review, and issue tracking.
- Accessing internal documentation and policy files in the compliance repository.
- Using corporate VPN or approved remote access methods to connect to FusionEMS resources.

### 3.3 Data Handling

- PHI must be handled exclusively within authorized FusionEMS systems. PHI must never be copied to local devices, personal storage, or unapproved cloud services.
- Test environments must use synthetic data. PHI from production must never be used in development or staging environments without formal de-identification and Security Officer approval.
- Data exports from FusionEMS (NEMSIS submissions, billing exports, patient reports) must only be transmitted through platform-approved channels with encryption in transit.

## 4. Prohibited Activities

The following activities are strictly prohibited on FusionEMS systems:

### 4.1 Security Violations

- Attempting to access systems, data, or environments without authorization.
- Circumventing or disabling security controls, including OPA policy enforcement, MFA requirements, or WAF rules.
- Sharing credentials, JWT tokens, API keys, or session tokens with any other person.
- Using another person's credentials or impersonating another user.
- Installing unauthorized software, backdoors, or malicious code on any FusionEMS system.
- Performing network scanning, port scanning, or vulnerability scanning against FusionEMS infrastructure without explicit Security Officer authorization.
- Using break-glass access (SupportAccessGrant) without a documented emergency and immediate notification to the Security Officer.
- Disabling or modifying CloudWatch alarms, GuardDuty detectors, or Security Hub standards without change management approval.

### 4.2 Data Violations

- Accessing, copying, or exporting PHI without a legitimate business need (minimum necessary principle).
- Storing PHI on personal devices, removable media, personal cloud storage (e.g., personal Google Drive, Dropbox), or unapproved services.
- Transmitting PHI via unencrypted channels (unencrypted email, SMS, public messaging platforms, public Slack channels).
- Altering, falsifying, or deleting audit logs, patient records, or financial records.
- Exfiltrating source code, infrastructure configurations, or proprietary data.

### 4.3 System Misuse

- Using FusionEMS systems for cryptocurrency mining or any resource-intensive personal activity.
- Running unauthorized services, containers, or workloads in AWS environments.
- Introducing unauthorized Terraform resources or modifying infrastructure outside of the approved CI/CD pipeline.
- Using FusionEMS systems for harassment, discrimination, or creation/distribution of offensive material.
- Engaging in illegal activities using any FusionEMS resource.
- Sending spam, chain letters, or unsolicited mass communications.
- Using FusionEMS systems for personal commercial activities or side businesses.

### 4.4 Bypass Prohibitions

- Bypassing CI/CD pipeline safety checks (e.g., using `--no-verify`, skipping Checkov scans, force-pushing to protected branches).
- Deploying code to production without peer review.
- Granting IAM permissions outside of the Terraform-managed process.
- Creating AWS resources via the console that are not reflected in infrastructure-as-code.

## 5. Personal Use

### 5.1 Permitted Personal Use

Limited, incidental personal use of FusionEMS systems is permitted provided it:

- Does not interfere with job performance.
- Does not consume excessive system resources.
- Does not involve any prohibited activity listed in Section 4.
- Does not involve accessing, storing, or transmitting inappropriate content.
- Does not create legal liability for the Organization.

### 5.2 Restrictions

- Personal use of AWS resources (compute, storage, network) is prohibited.
- Personal projects must not be developed in FusionEMS repositories or infrastructure.
- Personal devices used for work must comply with BYOD requirements (Section 8).
- The Organization assumes no responsibility for personal data stored on company systems.

## 6. Email and Messaging

### 6.1 Email Guidelines

- Corporate email is for business communications. PHI must never be sent via email unless using an encrypted email service approved by the Security Officer.
- Email containing confidential business information must be sent only to authorized recipients on a need-to-know basis.
- External email communications regarding security incidents, breaches, or legal matters must be coordinated with the Security Officer and legal counsel.
- Automatic email forwarding to personal email accounts is prohibited.
- Email accounts of terminated personnel must be disabled within 24 hours per the Access Control Policy.

### 6.2 Slack and Internal Messaging

- FusionEMS uses Slack as the primary internal communication tool.
- PHI must never be shared in Slack channels or direct messages. Patient identifiers, vitals, demographic data, and billing information must remain within the FusionEMS platform.
- Incident response communications should use the designated incident channel with restricted membership.
- Slack integrations with third-party services require Security Officer approval.
- Slack conversations related to security incidents or breaches are subject to preservation requirements.

### 6.3 External Communications

- Only authorized spokespersons may communicate with media regarding security incidents or breaches.
- Customer communications regarding service outages must follow the Incident Response Plan (IRP-001) communication procedures.
- Technical discussions about FusionEMS architecture or security controls in public forums (conferences, meetups, online communities) require prior CTO approval to avoid inadvertent disclosure.

## 7. Social Media

### 7.1 General Guidelines

- Personnel may not represent themselves as official FusionEMS spokespersons on social media unless authorized.
- Personnel must not disclose confidential business information, security practices, infrastructure details, or customer information on social media.
- Social media posts must not include screenshots of FusionEMS dashboards, admin interfaces, Grafana metrics, or AWS Console views.
- Personnel must clearly distinguish personal opinions from official FusionEMS positions when discussing the Organization or its industry.

### 7.2 Restrictions

- Public disclosure of security vulnerabilities, incidents, or system weaknesses via social media is prohibited.
- Posting source code snippets, configuration excerpts, or API responses on public platforms (Twitter/X, LinkedIn, Reddit, Stack Overflow) requires CTO review to ensure no sensitive information is included.

## 8. Bring Your Own Device (BYOD)

### 8.1 General Requirements

Personal devices used to access FusionEMS systems must comply with the following minimum security requirements:

- Operating system must be current and receiving security updates (no end-of-life OS versions).
- Device must have full-disk encryption enabled (FileVault on macOS, BitLocker on Windows, LUKS on Linux).
- Screen lock must be enabled with a maximum idle timeout of 5 minutes.
- Device must have anti-malware software installed and up to date (commercial endpoints).
- Device must not be jailbroken or rooted.

### 8.2 Restrictions

- PHI must not be stored on personal devices under any circumstances. FusionEMS is a web-based platform; all patient data remains server-side.
- Personal devices may access FusionEMS systems only through the web interface or approved VPN.
- Personal devices are subject to remote wipe of company data upon termination of employment or contract, or upon loss/theft of the device.
- Installation of MDM (Mobile Device Management) software may be required for devices with persistent access to administrative systems.

### 8.3 Lost or Stolen Devices

Personnel must report lost or stolen devices that have been used to access FusionEMS systems to the Security Officer within 4 hours. The Organization will:

- Invalidate all active sessions associated with the user (Cognito token revocation).
- Reset the user's Cognito password.
- Review recent access logs for the user's account.
- Evaluate whether a security incident has occurred.

## 9. Monitoring and Privacy

### 9.1 Notice of Monitoring

FusionEMS Quantum monitors the use of its information systems to protect the security, integrity, and availability of its resources and the data they process. By accessing FusionEMS systems, users consent to monitoring of:

- Network traffic and firewall logs (VPC Flow Logs).
- Application access logs (ALB access logs, API request logs).
- Authentication events (Cognito sign-in/sign-out, MFA events).
- AWS Console and API activity (CloudTrail).
- Source code repository activity (GitHub audit log).
- Email and messaging metadata (as required for security investigations).
- File access and modification events on corporate systems.

### 9.2 Scope of Monitoring

Monitoring is conducted for legitimate business purposes including:

- Detecting unauthorized access attempts.
- Identifying security incidents and policy violations.
- Ensuring compliance with HIPAA, SOC 2, and other regulatory requirements.
- Supporting incident investigation and forensic analysis.
- Validating appropriate use of privileged access.

### 9.3 Privacy Expectations

Users should have no expectation of privacy when using FusionEMS Quantum systems. All data created, stored, sent, or received on company systems is the property of FusionEMS Quantum. However, monitoring activity itself is subject to access controls — only the Security Officer and designated personnel may review monitoring data.

## 10. Software and Licensing

### 10.1 Authorized Software

- Only software approved by the CTO or Security Officer may be installed on company systems or used in FusionEMS environments.
- All software dependencies in FusionEMS repositories must be declared in dependency manifests (`requirements.txt`, `pyproject.toml`, `package.json`) and subject to Dependabot vulnerability scanning.
- Open-source software must be evaluated for license compatibility before adoption.

### 10.2 Prohibited Software

- No peer-to-peer file-sharing software.
- No remote administration tools other than those approved by the Organization (SSH via approved jump hosts, approved remote desktop solutions).
- No personal VPN software that tunnels traffic outside of organizational monitoring.
- No AI/ML tools or services for processing PHI unless approved by the Security Officer and CTO (to prevent unauthorized data exposure to third-party model providers).

## 11. Physical Security

### 11.1 Remote Work Environment

Given FusionEMS Quantum operates as a distributed organization:

- Work-from-home environments must have a dedicated, private workspace when handling confidential or restricted data.
- Screens displaying FusionEMS administrative interfaces must not be visible to unauthorized individuals.
- Phone calls or video conferences discussing PHI or sensitive business matters must be conducted in private settings.
- Printed materials containing confidential or restricted data must be secured and shredded when no longer needed.

### 11.2 Travel

- Screens must be protected with a privacy filter when working in public spaces.
- FusionEMS systems must only be accessed via trusted networks or VPN when traveling.
- Devices must not be left unattended in public spaces, hotel rooms, or vehicles.

## 12. Consequences of Violation

### 12.1 Disciplinary Scale

Violations of this policy are subject to disciplinary action based on severity:

| Severity | Example | Consequence |
|----------|---------|-------------|
| **Minor** | Incidental personal use exceeding limits; failure to lock workstation | Verbal warning, documented |
| **Moderate** | Sharing PHI in Slack; installing unauthorized software; failing to report lost device within SLA | Written warning, mandatory training, temporary access restriction |
| **Major** | Unauthorized access to PHI; disabling security controls; credential sharing | Suspension of access, formal investigation, potential termination |
| **Critical** | Intentional data exfiltration; malicious activity; HIPAA violation causing breach | Immediate termination, legal referral, regulatory notification |

### 12.2 Investigation Process

1. The Security Officer is notified of the suspected violation.
2. System access may be temporarily suspended during investigation.
3. Relevant logs and evidence are preserved per the Incident Response Plan.
4. The individual is given an opportunity to explain the circumstances.
5. Disciplinary action is determined in consultation with HR and legal counsel.
6. The outcome is documented and maintained in the personnel file and security records.

### 12.3 Contractor and Vendor Violations

Violations by contractors or vendors may result in immediate contract termination and removal of all system access. The Organization reserves the right to pursue legal remedies for damages resulting from policy violations.

## 13. Acknowledgment

All personnel must acknowledge this policy upon onboarding and annually upon each revision. Acknowledgment indicates that the individual has:

- Read and understood the entire Acceptable Use Policy.
- Agrees to comply with all provisions.
- Understands the consequences of non-compliance.
- Understands that FusionEMS systems are monitored.

The acknowledgment record is maintained by the Security Officer and is available for audit review.

## 14. Related Policies

- Information Security Policy (ISP-001)
- Access Control Policy (ACP-001)
- Encryption Policy (ENC-001)
- Data Classification Policy (DCP-001)
- Incident Response Plan (IRP-001)
- Breach Notification Procedure (BNP-001)

## 15. Revision History

| Version | Date           | Author           | Description          |
|---------|----------------|------------------|----------------------|
| 1.0     | March 9, 2026  | Security Officer | Initial release      |

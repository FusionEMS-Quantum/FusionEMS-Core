# Access Control Policy

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Policy ID**      | ACP-001                                    |
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
3. [Principles](#3-principles)
4. [Role-Based Access Control](#4-role-based-access-control)
5. [Authentication](#5-authentication)
6. [Password and Credential Standards](#6-password-and-credential-standards)
7. [Multi-Factor Authentication](#7-multi-factor-authentication)
8. [Account Lifecycle Management](#8-account-lifecycle-management)
9. [Privileged Access Management](#9-privileged-access-management)
10. [Service Account Management](#10-service-account-management)
11. [Session Management](#11-session-management)
12. [API Key and Token Management](#12-api-key-and-token-management)
13. [Emergency Access (Break-Glass)](#13-emergency-access-break-glass)
14. [Access Reviews](#14-access-reviews)
15. [Network Access Control](#15-network-access-control)
16. [Logging and Monitoring](#16-logging-and-monitoring)
17. [Enforcement](#17-enforcement)
18. [Related Policies](#18-related-policies)
19. [Revision History](#19-revision-history)

---

## 1. Purpose

This Access Control Policy establishes the requirements for managing access to all FusionEMS Quantum information systems and data. Effective access control is foundational to protecting the confidentiality, integrity, and availability of Protected Health Information (PHI), ensuring HIPAA compliance, and maintaining multi-tenant isolation across all customer agencies using the FusionEMS platform.

## 2. Scope

This policy applies to:

- All user accounts on the FusionEMS platform (human and service).
- All AWS IAM roles, policies, and federation mechanisms.
- AWS Cognito user pools and identity management.
- OPA (Open Policy Agent) authorization policies.
- All environments: production, staging, development.
- Physical and logical access to data centers (managed by AWS).
- Third-party access to FusionEMS systems (vendor, BAA partner).

## 3. Principles

### 3.1 Least Privilege

All users, services, and processes are granted the minimum level of access necessary to perform their authorized functions. No access is granted by default — all permissions must be explicitly assigned.

### 3.2 Deny by Default

Access to all FusionEMS resources is denied unless explicitly granted. This applies to:

- OPA policy evaluation: the default decision is `deny`. Every API endpoint requires an explicit `allow` rule.
- AWS IAM: IAM policies use explicit `Allow` statements; implicit deny is the baseline.
- Network Security Groups: inbound traffic is denied unless a rule permits it.
- S3 bucket policies: public access is blocked at the account level via S3 Block Public Access.

### 3.3 Separation of Duties

Critical functions are divided among multiple individuals to prevent unauthorized actions:

- Infrastructure changes require peer review of Terraform plans before apply.
- Code deployment requires a separate reviewer from the author.
- User provisioning for privileged roles (founder, agency_admin) requires Security Officer approval.
- Financial operations (billing configuration, Stripe webhook setup) require billing_admin role with agency_admin oversight.

### 3.4 Need-to-Know

Access to data is granted based on business need. Tenant data is isolated — users in one agency cannot access data belonging to another agency unless explicitly authorized (e.g., founder role for platform operations). This is enforced at the database query layer via mandatory `agency_id` filtering on all tenant-scoped models.

## 4. Role-Based Access Control

### 4.1 FusionEMS Platform Roles

FusionEMS implements role-based access control (RBAC) through OPA policy evaluation on every API request. The following roles are defined:

| Role | Description | Scope | Typical Permissions |
|------|-------------|-------|-------------------|
| **founder** | Platform owner with global administrative access | All tenants | Full read/write across all resources, all tenants. User management, system configuration, compliance tooling. |
| **agency_admin** | Administrator for a specific tenant (agency) | Single tenant | Manage agency users, configure agency settings, manage crews, view all agency data, manage compliance packs. |
| **supervisor** | Operational supervisor within an agency | Single tenant | View/edit incident records, manage crew assignments, view performance metrics, approve PCRs, view billing summary. |
| **billing_admin** | Billing and revenue cycle management lead | Single tenant | Full access to billing module, claims management, payment processing (Stripe), RCM analytics, NEMSIS billing fields. |
| **billing** | Billing staff within an agency | Single tenant | Create/edit billing claims, process payments, view patient billing data. No access to clinical data beyond billing-relevant fields. |
| **ems_crew** | Field EMS providers (paramedics, EMTs) | Single tenant | Create/edit ePCR records, view patient data for active incidents, update run status, access MDT functions. |
| **patient** | Patient portal user | Own records | View own medical records, download copies, manage consent, update demographics. |
| **readonly** | Auditors, observers, reporting users | Single tenant | Read-only access to data within their authorized scope. No create, update, or delete permissions. |
| **system** | Internal system processes and integrations | Platform-wide | Service-to-service communication, background job execution, scheduled tasks. Not assignable to human users. |

### 4.2 Role Assignment Rules

- Every user has exactly one role per tenant assignment.
- The `founder` role is limited to a maximum of 3 users and requires CEO approval for assignment.
- The `agency_admin` role is assigned by a `founder` or by another `agency_admin` within the same tenant with Security Officer notification.
- All other role assignments are managed by `agency_admin` users within their tenant.
- The `system` role is used exclusively for internal service accounts and must never be assigned to a human user.
- The `patient` role is self-registered with email/phone verification and is limited to the patient portal.

### 4.3 OPA Policy Enforcement

Authorization decisions are made by the OPA policy engine, which evaluates:

- The authenticated user's role.
- The target resource and action (CRUD operation).
- The user's tenant (agency_id) relationship to the resource.
- Any contextual attributes (time, IP, resource state).

OPA policies are maintained as code in the `/opa/policies/` directory, versioned alongside the application, and deployed with each release. Policy changes require code review and Security Officer approval.

## 5. Authentication

### 5.1 Identity Provider

AWS Cognito is the sole identity provider for FusionEMS user authentication. Cognito provides:

- OIDC-compliant authentication flows.
- Managed user pool with configurable password policies.
- MFA support (TOTP and SMS).
- Token management (ID token, access token, refresh token).
- User attribute management and verification.

### 5.2 Authentication Requirements

- All human users must authenticate via Cognito before accessing any FusionEMS resource.
- No static username/password authentication is permitted outside of the Cognito-managed flow.
- Social identity federation (Google, Apple) may be enabled for the patient portal with Security Officer approval.
- SAML/OIDC federation with customer identity providers may be enabled for enterprise tenants via Cognito identity provider configuration.

### 5.3 Authentication Logging

All authentication events are logged in CloudWatch Logs with correlation IDs, including:

- Successful and failed sign-in attempts.
- MFA challenge/response events.
- Password change and reset events.
- Token refresh events.
- Account lockout events.

## 6. Password and Credential Standards

### 6.1 Password Requirements

FusionEMS enforces the following password requirements via Cognito user pool configuration:

| Requirement | Standard |
|-------------|----------|
| Minimum length | 12 characters |
| Uppercase letters | At least 1 required |
| Lowercase letters | At least 1 required |
| Numbers | At least 1 required |
| Special characters | At least 1 required |
| Password history | Last 6 passwords prohibited (enforced at application level) |
| Maximum age | 90 days for privileged roles (founder, agency_admin); 365 days for standard roles |
| Account lockout | 5 failed attempts triggers temporary lockout (30 minutes) |

### 6.2 Credential Storage

- User passwords are stored exclusively in Cognito (hashed by AWS using SRP protocol). FusionEMS backend never stores or processes plaintext passwords.
- Application secrets (database credentials, API keys, signing keys) are stored in AWS Secrets Manager with automatic rotation enabled.
- No credentials, tokens, or secrets are stored in source code, environment variables baked into container images, or configuration files in the repository.
- Terraform state files containing sensitive values are stored in S3 with server-side encryption (KMS) and restricted bucket policies.

### 6.3 Credential Rotation

| Credential Type | Rotation Schedule | Mechanism |
|----------------|-------------------|-----------|
| Database passwords (RDS) | 90 days | Secrets Manager automatic rotation |
| Cognito signing keys | Managed by AWS | Automatic |
| KMS keys | Annual | AWS KMS automatic rotation |
| Stripe API keys | Annual or on compromise | Manual rotation, Secrets Manager |
| Telnyx API keys | Annual or on compromise | Manual rotation, Secrets Manager |
| GitHub deploy keys | Annual | Manual rotation |
| Service account tokens | 24 hours (JWT) | Automatic via token refresh |

## 7. Multi-Factor Authentication

### 7.1 MFA Requirements

| Role | MFA Requirement |
|------|----------------|
| founder | Required (TOTP mandatory) |
| agency_admin | Required (TOTP mandatory) |
| supervisor | Required (TOTP or SMS) |
| billing_admin | Required (TOTP or SMS) |
| billing | Required (TOTP or SMS) |
| ems_crew | Required (TOTP or SMS) |
| patient | Optional (SMS-based, encouraged) |
| readonly | Required (TOTP or SMS) |

### 7.2 MFA Methods

- **TOTP (Time-based One-Time Password)**: Preferred method. Users configure an authenticator application (Google Authenticator, Authy, 1Password). Required for all privileged roles.
- **SMS**: Secondary method for roles where TOTP is impractical (e.g., field crews). SMS codes are delivered via the Cognito-managed SMS channel.
- **Hardware tokens**: Supported for high-security roles if requested (configured as TOTP in Cognito).

### 7.3 MFA Enforcement

MFA is enforced at the Cognito user pool level. Users cannot complete authentication without satisfying the MFA challenge. MFA configuration changes require Security Officer approval.

### 7.4 AWS Console MFA

All AWS IAM users with console access must have MFA enabled. This is enforced via IAM policy conditions (`aws:MultiFactorAuthPresent`). Programmatic access for CI/CD is via OIDC federation (GitHub Actions → IAM role assumption) — no long-lived access keys exist.

## 8. Account Lifecycle Management

### 8.1 Provisioning

New user accounts are provisioned through the following process:

1. **Request**: Authorized requestor (agency_admin for tenant users; founder for admins; HR for employees) submits a user creation request specifying the requested role and tenant.
2. **Approval**: The request is reviewed against the principle of least privilege. Privileged role requests (founder, agency_admin, billing_admin) require Security Officer approval.
3. **Creation**: The user account is created in Cognito via the FusionEMS admin API. An invitation email is sent with a temporary password.
4. **Activation**: The user signs in, changes the temporary password, and configures MFA.
5. **Verification**: The user's email address is verified via Cognito verification code.
6. **Audit**: The provisioning event is logged with the requestor, approver, role assigned, and timestamp.

### 8.2 Modification

Role changes and access modifications follow the same approval chain as provisioning. All modifications are logged in the audit trail. Role escalation (e.g., ems_crew → supervisor) requires agency_admin approval. Cross-tenant access grants require founder approval.

### 8.3 Deprovisioning

User accounts must be deprovisioned within the following timelines:

| Trigger | Timeline | Actions |
|---------|----------|---------|
| Voluntary termination | Day of departure | Disable Cognito account, revoke all tokens, remove from active rosters |
| Involuntary termination | Immediately upon notification | Disable Cognito account, revoke all tokens, remove from active rosters, review access logs for 30 days prior |
| Contractor end of engagement | End of last working day | Disable Cognito account, revoke all tokens |
| Role change (lose privileges) | Same day as role change | Modify Cognito groups, update OPA-relevant attributes |
| Extended leave (>30 days) | Day leave begins | Disable Cognito account (reactivated upon return) |

### 8.4 Deprovisioning Procedure

1. Disable the user's Cognito account (sets `UserStatus` to `DISABLED`).
2. Issue global sign-out to invalidate all active tokens.
3. Remove the user from all Cognito groups.
4. Update the user's `is_active` flag in the FusionEMS user model.
5. Review and reassign any resources owned by the departing user (e.g., open incidents, pending billing claims).
6. Log the deprovisioning event with timestamp and executing administrator.
7. Retain the user record for audit purposes (do not delete; mark as deactivated).

## 9. Privileged Access Management

### 9.1 Privileged Accounts

Privileged accounts include:

- `founder` role users in FusionEMS.
- `agency_admin` role users in FusionEMS.
- AWS IAM roles with administrative permissions.
- Database administrator access to RDS (via Secrets Manager, not direct credentials).
- GitHub organization owners.

### 9.2 Controls for Privileged Access

- Privileged accounts require TOTP-based MFA (no SMS fallback).
- Privileged session tokens have the same 60-minute JWT lifetime as standard tokens but are subject to additional OPA policy checks.
- All privileged actions are logged with full request/response metadata in the audit trail.
- Privileged users must acknowledge the Acceptable Use Policy and this Access Control Policy annually.
- AWS console access for administrative tasks is via SSO with session duration limited to 1 hour.

### 9.3 Privileged Access Review

Privileged accounts are reviewed monthly by the Security Officer. The review verifies:

- Each privileged account has a current, active business justification.
- No orphaned privileged accounts exist.
- Privileged access logs show no anomalous activity.
- MFA is properly configured and active.

## 10. Service Account Management

### 10.1 Service Account Types

| Account Type | Purpose | Authentication |
|-------------|---------|----------------|
| ECS Task Roles | FusionEMS backend/worker containers accessing AWS services | IAM Task Role (no credentials in container) |
| GitHub Actions OIDC | CI/CD pipeline accessing AWS for deployment | OIDC federation to IAM role |
| Internal API | Service-to-service communication within ECS cluster | JWT signed with internal key from Secrets Manager |
| Stripe Webhook | Stripe delivering payment events to FusionEMS | Webhook signature verification (Stripe signing secret) |
| Telnyx Webhook | Telnyx delivering telephony events | Webhook signature verification |

### 10.2 Service Account Controls

- Service accounts use IAM roles with scoped permissions — no long-lived access keys.
- ECS Task Roles follow least privilege: each service has its own role with only the permissions it needs.
- Service account permissions are defined in Terraform and subject to code review.
- Service-to-service JWT tokens use short lifetimes (5 minutes) and are non-renewable.
- Service accounts are inventoried and reviewed quarterly.

## 11. Session Management

### 11.1 Token Lifecycle

FusionEMS uses JWT tokens issued by Cognito with the following configuration:

| Token Type | Lifetime | Renewal |
|-----------|----------|---------|
| ID Token | 60 minutes | Via refresh token |
| Access Token | 60 minutes | Via refresh token |
| Refresh Token | 30 days | One-time use (rotation enabled) |

### 11.2 Token Security

- Refresh token rotation is enabled in Cognito. Each refresh token can be used exactly once; a new refresh token is issued with each access token refresh.
- If a refresh token is reused (potential token theft), all tokens for the user session are invalidated.
- Tokens are transmitted only over TLS-encrypted connections.
- Frontend stores tokens in memory (not localStorage or cookies accessible to JavaScript) to mitigate XSS-based token theft.
- Backend validates token signature, expiration, issuer, and audience on every API request.

### 11.3 Session Termination

Sessions are terminated under the following conditions:

- User explicitly signs out.
- Access token expires and refresh token is expired or invalid.
- Admin initiates global sign-out for the user (Cognito `AdminUserGlobalSignOut`).
- User's account is disabled or deprovisioned.
- Anomalous activity is detected (e.g., impossible travel, concurrent sessions from conflicting geolocations).

## 12. API Key and Token Management

### 12.1 API Keys

FusionEMS does not issue static API keys to human users. All human authentication is OIDC-based via Cognito. For machine-to-machine integrations:

- API keys are issued per-integration and stored in Secrets Manager.
- Each key is scoped to specific endpoints and tenant(s).
- Keys are rotated annually or immediately upon suspected compromise.
- Inactive keys (no usage in 90 days) are automatically flagged for review.

### 12.2 Webhook Secrets

Third-party webhook secrets (Stripe, Telnyx) are:

- Stored in Secrets Manager.
- Used exclusively for signature verification (HMAC validation) — not for outbound authentication.
- Rotated via the provider's key rotation mechanism during the annual rotation cycle.

## 13. Emergency Access (Break-Glass)

### 13.1 Purpose

Emergency access procedures exist for situations where normal access controls would impede response to a life-safety or system-critical event. The `SupportAccessGrant` model in FusionEMS provides a controlled mechanism for temporary elevated access.

### 13.2 Procedure

1. **Justification**: The requesting individual documents the emergency requiring elevated access (e.g., production outage affecting dispatch, active security incident requiring cross-tenant investigation).
2. **Grant**: A `founder` user creates a `SupportAccessGrant` record specifying:
   - The target user receiving elevated access.
   - The scope of elevated access (specific tenant, all tenants, specific resource).
   - The time-limited duration (maximum 4 hours).
   - The justification text.
3. **Notification**: The Security Officer is automatically notified via Slack and email when a break-glass grant is created.
4. **Usage**: The elevated access is active immediately. All actions taken during the break-glass window are logged with the grant ID for audit correlation.
5. **Expiration**: Access automatically reverts when the grant duration expires. Grants cannot be renewed — a new grant must be created with fresh justification.
6. **Review**: The Security Officer reviews all break-glass grants within 24 hours. A post-incident review is required for each use.

### 13.3 Audit Requirements

Break-glass events generate high-priority audit records including:

- Grant creation timestamp, requestor, target user, scope, duration, justification.
- All API requests made during the grant window by the target user.
- Grant expiration or manual revocation timestamp.
- Post-incident review findings and any control improvements.

## 14. Access Reviews

### 14.1 Review Schedule

| Review Type | Frequency | Scope | Reviewer |
|------------|-----------|-------|----------|
| Privileged account review | Monthly | founder, agency_admin roles | Security Officer |
| User access review | Quarterly | All active user accounts | Security Officer + agency_admins |
| Service account review | Quarterly | All IAM roles, service accounts | CTO + Security Officer |
| AWS IAM review | Quarterly | All IAM policies, roles, SSO configs | CTO |
| OPA policy review | Per release | Authorization policy changes | Security Officer + CTO |
| Break-glass review | Per event + quarterly summary | All SupportAccessGrant records | Security Officer |

### 14.2 Review Procedure

1. Generate the access report from FusionEMS admin API (list all users, roles, last login, tenant assignments).
2. Cross-reference with HR active employee/contractor list.
3. Identify stale accounts (no login in 90 days) and flag for deprovisioning review.
4. Verify privileged role assignments have current business justification.
5. Confirm MFA is active for all required roles.
6. Document review findings, actions taken, and reviewer attestation.
7. Store review records in the compliance evidence repository for SOC 2 audit.

### 14.3 Recertification

Every user with access to PHI must have their access recertified quarterly by their agency_admin and countersigned by the Security Officer. Users whose access is not recertified within 15 days of the review deadline have their accounts automatically disabled.

## 15. Network Access Control

### 15.1 Network Segmentation

FusionEMS AWS infrastructure uses VPC-based network segmentation:

- **Public subnets**: ALB only — no application or data tier components exposed to the internet.
- **Private subnets (application tier)**: ECS Fargate tasks, internal ALB.
- **Private subnets (data tier)**: RDS PostgreSQL, ElastiCache Redis — no direct internet access.
- **VPC endpoints**: Used for S3, Secrets Manager, CloudWatch Logs, ECR, and KMS to eliminate internet traversal for AWS service calls.

### 15.2 Security Groups

Security Groups enforce the following rules:

- ALB SG: allows inbound HTTPS (443) from the internet (via WAF). No other inbound.
- ECS SG: allows inbound only from ALB SG on application port. No direct internet inbound.
- RDS SG: allows inbound PostgreSQL (5432) only from ECS SG. No other inbound.
- Redis SG: allows inbound Redis (6379) only from ECS SG. No other inbound.

### 15.3 WAF

AWS WAF is deployed on the ALB with managed rule sets including:

- AWS Managed Rules: Core Rule Set (CRS), Known Bad Inputs, SQL Injection, XSS.
- Rate limiting: per-IP request throttling.
- Geo-blocking: optional per-tenant configuration.
- Custom rules for FusionEMS-specific protections as identified by the security team.

## 16. Logging and Monitoring

### 16.1 Access Logging

All access events are logged with:

- Timestamp (UTC).
- User identity (Cognito sub, email).
- Source IP address.
- Target resource and action.
- Authorization decision (allow/deny) with policy name.
- Correlation ID for request tracing.

### 16.2 Alerting

CloudWatch Alarms are configured for:

- Failed authentication spike (>10 failures per user in 5 minutes).
- Privileged role activity outside business hours.
- Break-glass grant activation.
- Unauthorized access attempts (OPA deny decisions exceeding threshold).
- GuardDuty findings related to credential compromise or unauthorized access.

## 17. Enforcement

Violations of this policy are subject to disciplinary action per the Information Security Policy (ISP-001) and Acceptable Use Policy (AUP-001), up to and including termination and legal action. Automated technical controls (OPA deny-by-default, Cognito MFA enforcement, IAM policy restrictions) provide primary enforcement. Manual compliance verification occurs through access reviews and audit processes.

## 18. Related Policies

- Information Security Policy (ISP-001)
- Acceptable Use Policy (AUP-001)
- Encryption Policy (ENC-001)
- Data Classification Policy (DCP-001)
- Incident Response Plan (IRP-001)
- Breach Notification Procedure (BNP-001)

## 19. Revision History

| Version | Date           | Author           | Description          |
|---------|----------------|------------------|----------------------|
| 1.0     | March 9, 2026  | Security Officer | Initial release      |

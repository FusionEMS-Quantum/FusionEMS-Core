# Vendor Management Policy

| Field | Value |
|---|---|
| Policy ID | VMP-002 |
| Version | 1.0 |
| Effective Date | March 9, 2026 |
| Review Cadence | Annual |
| Owner | Security Officer |
| Approved By | Security Officer, CEO |

## Purpose

Define how FusionEMS evaluates, approves, monitors, and offboards third-party vendors and subprocessors with emphasis on PHI risk, availability risk, and supply-chain security.

## Vendor Tiers

- **Critical**: AWS, Stripe, Telnyx, OpenAI
- **Standard**: Microsoft, Lob, monitoring/compliance tools
- **Low**: Non-production office tooling with no PHI access

## Mandatory Due Diligence

For Critical and Standard vendors:

1. Security questionnaire
2. Latest SOC 2 Type II (or equivalent) report
3. Penetration/security summary where available
4. Data flow and subprocessor disclosure
5. Incident notification commitments
6. BAA required for any PHI access or potential access

## Risk Scoring Criteria

- PHI access level (none/indirect/direct)
- Tenant data exposure blast radius
- Availability impact if vendor outage occurs
- Privileged integration depth (webhooks, API scopes)
- Encryption and key management posture

## Ongoing Monitoring

- Annual vendor reassessment
- Annual SOC report refresh
- Quarterly review for Critical vendors
- Immediate review upon breach/adverse disclosure

## BAA Rules

A BAA is required before production use when vendor can access PHI directly or indirectly (support channels, storage, logs, backups).

## Offboarding

On termination:

- Revoke tokens/keys/webhook trust
- Remove IAM/OIDC trust paths
- Request written data deletion/return attestation
- Update subprocessor register

## Vendor Register Minimum Fields

- Vendor name
- Tier
- Service owner
- Data classes accessed
- PHI access scope
- BAA status/date
- SOC report date
- Last risk review date
- Next review date

## Evidence

- `vendor-register.csv`
- BAA repository
- Annual risk review records
- SOC report archive

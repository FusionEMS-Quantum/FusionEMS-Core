# Risk Assessment Methodology

| Field | Value |
|---|---|
| Policy ID | RAM-001 |
| Version | 1.0 |
| Effective Date | March 9, 2026 |
| Review Cadence | Annual + event-driven |
| Owner | Security Officer |

## Standard

FusionEMS uses NIST SP 800-30 aligned methodology with a 5x5 likelihood/impact matrix.

## Process

1. **Asset inventory** (systems, data stores, integrations)
2. **Threat identification** (external, insider, vendor, misconfiguration)
3. **Vulnerability identification** (technical/process/control gaps)
4. **Likelihood scoring** (1 Rare → 5 Almost Certain)
5. **Impact scoring** (1 Negligible → 5 Severe)
6. **Risk score** = Likelihood × Impact
7. **Treatment** = Accept / Mitigate / Transfer / Avoid
8. **Residual risk** documented after controls

## Risk Matrix

- 1–4: Low
- 5–9: Moderate
- 10–14: High
- 15–25: Critical

## Tolerance

- **Critical**: must be mitigated immediately, executive escalation
- **High**: mitigation plan within 30 days
- **Moderate**: planned treatment within quarter
- **Low**: track and review annually

## Triggered Assessments

In addition to annual review, run on:

- New PHI integration
- Major architecture changes
- Material incident/breach
- New regulatory/customer requirement

## Governance

- Security Officer owns process and final scoring
- CTO validates technical assumptions
- Business owners accept residual risk in writing

## Evidence Outputs

- Updated risk register
- Treatment plans with owners/dates
- Quarterly risk review minutes

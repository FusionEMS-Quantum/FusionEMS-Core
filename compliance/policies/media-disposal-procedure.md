# Media Disposal Procedure

| Field | Value |
|---|---|
| Policy ID | MDP-001 |
| Version | 1.0 |
| Effective Date | March 9, 2026 |
| Owner | Security Officer |

## Scope

Covers digital cloud media, endpoint storage, paper records, and removable media that may hold FusionEMS data.

## Digital Disposal Standards

- Cloud data: secure deletion plus lifecycle/version cleanup
- Keys: crypto-shred where applicable via KMS key retirement process
- Physical media: NIST 800-88 aligned wipe/destruction when used

## Cloud Disposal Steps

1. Confirm retention/legal hold status
2. Remove object versions/delete markers as required
3. Delete related snapshots/recovery artifacts per policy
4. Verify data non-retrievability
5. Log disposal evidence

## Paper Disposal

- Cross-cut shredding or certified shredding vendor
- Certificate of destruction retained

## Chain of Custody

Every disposal event records owner, executor, timestamp, dataset scope, method, and verification outcome.

## Evidence

- Disposal logs
- Certificates of destruction
- Verification outputs

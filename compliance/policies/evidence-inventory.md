# Evidence Inventory

## Automated Sources

- Terraform outputs for control plane resources (`cloudtrail_trail_arn`, `guardduty_detector_id`, `aws_config_recorder_id`, `security_hub_finding_rule_arn`, `backup_vault_arn`, `vulnerability_alarm_arn`)
- CI workflow logs for lint/test/security gates
- Checkov/TFLint/Terraform validate outputs
- CloudWatch alarm history and metric exports

## Operational Evidence

- Access review logs
- Incident response timelines and RCAs
- Backup restore drill records
- Vulnerability triage and remediation logs
- Security awareness completion records
- Vendor and BAA review records

## Retention Targets

- Audit/compliance evidence: minimum 7 years
- SOC 2 observation evidence: retain through audit cycles and contract obligations

## Packaging Standard

Each evidence artifact should include:

1. Control ID reference
2. Time period covered
3. Source system and immutable reference
4. Reviewer/approver metadata

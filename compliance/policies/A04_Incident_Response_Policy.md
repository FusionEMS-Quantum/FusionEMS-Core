# A.04 Incident Response Policy

## 1. Purpose
Define the process for detecting, managing, and resolving security incidents at FusionEMS, with strict adherence to HIPAA Breach Notification rules and GDPR/ISO 27701 timelines.

## 2. Severity Classification
- **SEV-1 (Critical):** Confirmed data breach of PHI/PII or complete service down. (Target response: 15 mins)
- **SEV-2 (High):** Suspected data exposure or severe degradation. (Target response: 1 hour)
- **SEV-3 (Medium):** WAF blocks, GuardDuty alerts handled via automation.

## 3. Incident Lifecycle
1. **Detection:** Alerts from GuardDuty, Security Hub, WAF, or manual report.
2. **Containment:** Isolate affected ECS/EKS instances, revoke compromised IAM credentials.
3. **Eradication:** Patch vulnerability, clean up malware.
4. **Recovery:** Restore from immutable AWS Backup vaults.
5. **Post-Mortem:** Conduct retro, update playbooks, implement permanent fixes.

## 4. Breach Notification Protocol
- **HIPAA:** Breach of unsecured PHI affecting 500+ individuals MUST be reported to HHS without unreasonable delay and strictly within 60 days.
- **GDPR / ISO 27701:** Data protection authority notified within 72 hours.
- Customers (Covered Entities) must be notified as per the specific Business Associate Agreement (BAA).

## 5. Framework Mappings
- **ISO 27001:** A.16 (Information Security Incident Management)
- **SOC 2:** CC7.3, CC7.4
- **HIPAA:** 164.308(a)(6) (Security Incident Procedures)

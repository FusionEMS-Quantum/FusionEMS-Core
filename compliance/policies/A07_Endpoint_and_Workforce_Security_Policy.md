# A.07 Endpoint and Workforce Security Policy

## 1. Purpose
This policy establishes the minimum acceptable security standards for end-user computing devices (endpoints) and general workforce security hygiene, ensuring compliance with SOC 2, ISO 27001, and HIPAA requirements for off-network or local environments.

## 2. Endpoint Configuration Standards
All company-issued and BYOD (Bring Your Own Device) endpoints accessing FusionEMS data or source code MUST comply with the following:
1. **Full Disk Encryption (FDE):** FileVault (macOS), BitLocker (macOS/Windows), or LUKS (Linux) must be enabled and enforced via Mobile Device Management (MDM).
2. **Endpoint Detection and Response (EDR):** SentinelOne, CrowdStrike, or an equivalent EDR agent must be running and connected to the central console.
3. **Screen Lock:** Devices must lock automatically after 15 minutes of inactivity and require biometric/password authentication to unlock.
4. **Patch Management:** OS and critical application updates must be applied within 14 days of release.

## 3. Acceptable Use & Workforce Security
1. **PHI/PII on Endpoints:** Under strictly NO circumstances shall an employee download, store, or process unanonymized PHI or PII on local endpoints. All data manipulation must occur within secure AWS boundaries (e.g., via AWS WorkSpaces or Bastion terminals).
2. **Security Awareness Training:** All employees and contractors must complete Security & HIPAA Privacy training upon hire and annually thereafter.
3. **Phishing Simulations:** The workforce will be subjected to quarterly simulated phishing exercises.
4. **Clean Desk Policy:** Sensitive physical documents are prohibited. Desks and screens must be cleared and locked when unattended.

## 4. Bring Your Own Device (BYOD)
BYOD is permitted strictly under the condition that the device is enrolled in the corporate MDM to containerize and isolate corporate applications (e.g., Slack, Email, AWS access) from personal data. The MDM must be able to remotely wipe the corporate enclave.

## 5. Framework Mappings
- **ISO 27001:** Clause A.7 (Human Resource Security), A.8 (Asset Management)
- **SOC 2:** CC6.4 (Physical Access), CC6.8 (Unauthorized Malicious Software)
- **HIPAA:** 164.310(b) (Workstation Use), 164.310(c) (Workstation Security)

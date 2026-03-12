# A.09 Privacy and Data Protection Policy

## 1. Purpose
To govern the collection, processing, retention, and deletion of Personally Identifiable Information (PII) and Protected Health Information (PHI) in accordance with ISO 27701, HIPAA, and GDPR standards.

## 2. Data Lifecycle Management
1. **Lawful Collection:** Data is only collected for specific, explicit, and legitimate purposes (e.g., patient care orchestration, billing).
2. **Data Minimization:** Only the minimum data necessary for the required action shall be requested, logged, or retained. 
3. **Data Retention:** Patient health records (PHI) are strictly retained per state regulations (typically 7-10 years). Access logs are retained for 1 year. Non-essential tracking data is pruned after 30 days.
4. **Data Destruction:** Upon customer termination or data expiry, data shall be purged via cryptographic erasure and verified automated database wipes. AWS hardware destruction aligns with DoD 5220.22-M.

## 3. Privacy Operations & Rights
1. **Data Subject Access Requests (DSARs):** Users/Patients may request copies of, or deletion of, their data. Authorized privacy staff must fulfill these requests within 30 days.
2. **Data Privacy Impact Assessments (DPIAs):** Prior to launching any new AI model, analytics feature, or sweeping architectural change, a DPIA must be conducted to assess the privacy impact on individuals.
3. **Automated Scanning:** Amazon Macie runs continuously across all S3 buckets to identify, log, and alert on any sensitive PII/PHI placed outside designated encrypted boundaries.

## 4. Framework Mappings
- **ISO 27701:** A.7.2 (Conditions for collection and processing), A.7.3 (Obligations to PII principals)
- **SOC 2:** Privacy Framework (P1.1 - P8.1)
- **HIPAA:** Privacy Rule (45 CFR Part 160 and Subparts A and E of Part 164)

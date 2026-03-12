# A.05 Business Continuity and Disaster Recovery (BC/DR) Policy

## 1. Purpose
To specify procedures and controls that maintain the operability of the FusionEMS platform and protect electronic protected health information (ePHI) from unexpected disruption.

## 2. DR Architecture
1. **Multi-AZ Mandate:** All production systems (RDS, ECS/EKS clusters, Network Firewalls, Load Balancers) MUST operate redundantly across at least three (3) Availability Zones in the primary geographical region.
2. **Cross-Region Strategy:** Critical databases and file stores (S3) must continuously replicate data asynchronously to a disparate AWS Region (e.g., from us-east-1 to us-west-2).

## 3. Backups (AWS Backup)
1. **Backup Automations:** All RDS instances, DynamoDB tables, and EFS volumes MUST have automated daily snapshot cycles.
2. **Immutability and Vaulting:** Backup data is stored in deeply restricted, encrypted AWS Backup Vaults using Vault Lock. Snapshots cannot be logically deleted or tampered with before 35 days even by the root administrator account to counteract ransomware.
3. **Restoration Checks:** Automated or manual test restores of Production RDS snaps into an isolated staging VPC MUST be conducted strictly on a quarterly basis and permanently documented. 

## 4. RTO and RPO
- **Recovery Time Objective (RTO):** 4 Hours for core patient care functionality (dispatch, charts).
- **Recovery Point Objective (RPO):** 5 Minutes for transactional databases.

## 5. Framework Mappings
- **ISO 27001:** Clause A.17 (Information Security Aspects of Business Continuity)
- **SOC 2:** Availability (A1.1, A1.2)
- **HIPAA:** 164.308(a)(7) (Contingency Plan)

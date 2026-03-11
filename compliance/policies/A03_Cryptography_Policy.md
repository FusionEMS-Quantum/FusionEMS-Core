# A.03 Cryptography & Data Protection Policy

## 1. Purpose
Define the cryptographic requirements and standards required to ensure the confidentiality, integrity, and authenticity of FusionEMS systems and data according to strictly defined FIPS and industry norms.

## 2. Encryption At Rest
1. **FIPS 140-2 Level 3 Compliance:** All encryption capabilities at rest for S3, RDS, EBS, ECS, EFS, and EKS must be backed by AWS Key Management Service (KMS) utilizing Customer Managed Keys (CMKs) running on FIPS-140-2 compliant Hardware Security Modules (HSMs). 
2. **Key Rotation:** Automatic key rotation MUST be enabled unconditionally with an annual interval for all encryption keys.
3. **Database & Storage:** AWS RDS, EBS volumes, and S3 buckets must explicitly deny unencrypted artifact writes via IAM and Bucket policies.

## 3. Encryption In Transit
1. **TLS Minimum Limits:** Strict enforcement of TLS 1.2 or TLS 1.3 for all internal and external network traffic. Insecure protocols (HTTP, FTP, Telnet) are blocked.
2. **Load Balancers / CDNs:** AWS Certificate Manager (ACM) manages automated SSL certificate issuance and renewal attached to Application Load Balancers and CloudFront to eliminate human failure of certificate rotation.
3. **Microservices (Service Mesh):** Cross-pod and internal VPC transit data between microservices MUST be automatically encrypted (e.g. mTLS).

## 4. Key Management Operations
Authorized separation of duties requires that Key Administrators (those who assign permissions to KMS keys) are logically separated from Key Users (machine roles handling actual data). 

## 5. Framework Mappings
- **ISO 27001:** Clause A.10 (Cryptography)
- **SOC 2:** CC6.1, CC6.6
- **HIPAA:** 164.312(a)(2)(iv) (Encryption and Decryption), 164.312(e)(2)(ii) (Transmission Security)

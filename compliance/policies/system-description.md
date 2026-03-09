# System Description (SOC 2)

| Field | Value |
|---|---|
| Policy ID | SD-001 |
| Version | 1.0 |
| Effective Date | March 9, 2026 |
| Owner | Security Officer |

## Company and Service

FusionEMS Quantum delivers FusionEMS, a multi-tenant healthcare/public safety SaaS platform for EMS/HEMS/Fire operations, ePCR, CAD, billing/RCM, MDT workflows, and analytics.

## Infrastructure Boundary

Primary platform stack runs on AWS with:

- CloudFront + WAF + ALB ingress
- ECS Fargate services (frontend/backend)
- RDS PostgreSQL + ElastiCache Redis
- S3/SQS/Secrets Manager/KMS
- Cognito authentication
- CloudWatch + OTEL observability

## Security Control Plane

- CloudTrail (API audit)
- GuardDuty (threat detection)
- AWS Config (continuous config compliance)
- Security Hub (findings aggregation/benchmarks)
- Backup + restore orchestration
- Inspector/ECR scanning (+ Macie in prod)

## Logical Boundary

- Tenant isolation via application and policy controls
- RBAC and OPA authorization enforcement
- PHI access restrictions and auditable mutations

## Trust Services Criteria

Designed for Security, Availability, Confidentiality, Processing Integrity, and Privacy with mapped controls and evidence cadence.

## Subservice Organizations

AWS, Stripe, Telnyx, Lob, OpenAI, Microsoft (as applicable) with vendor due diligence and BAA/contract controls where required.

## Complementary User Entity Controls

Customers must manage endpoint/device security, user account governance, and local policy/training for their workforce.

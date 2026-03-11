# A.06 Supplier Relationships & Vendor Management Policy

## 1. Purpose
To ensure all third-party vendors, suppliers, and service providers (including Sub-processors and Business Associates) handling FusionEMS data are subjected to rigorous security vetting to protect PHI/PII and maintain overall system integrity.

## 2. Vendor Selection & Risk Assessment
1. **Initial Assessment:** Prior to onboarding, any vendor that will store, process, or transmit FusionEMS data must complete a formal risk assessment detailing their technical security controls (SOC 2, ISO 27001 mappings). 
2. **Least Privilege Integration:** Vendors are specifically limited to accessing only the data explicitly required for functionally delivering their service.

## 3. Legal and Compliance Instruments
1. **Business Associate Agreements (BAA):** Any service that may encounter Protected Health Information (PHI) MUST sign a BAA. For example, the BAA provided under AWS Artifact must be formally accepted prior to moving any workloads to AWS Production.
2. **Data Processing Agreements (DPA):** For entities handling standard Personal Identifiable Information (PII), strict GDPR/CCPA compliant DPAs must be executed.
3. **Liability and Notification:** Contracts must mandate the supplier to notify FusionEMS CISO of any security breach within 24 hours of discovery.

## 4. Continuous Monitoring
- **Annual Review:** Critical (Tier 1) technology vendors must be evaluated annually to verify their continuous certifications (e.g. viewing updated SOC 2 reports for deviations).

## 5. Framework Mappings
- **ISO 27001:** Clause A.15 (Supplier Relationships)
- **SOC 2:** CC9.2 (Vendor Management)
- **HIPAA:** 164.308(b)(1) (Business Associate Contracts)

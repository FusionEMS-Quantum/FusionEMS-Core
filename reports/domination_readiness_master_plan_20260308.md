# FusionEMS Domination Readiness Master Plan

Generated: 2026-03-08

## 1) Live audit baseline (this session)

### Executed gates
- `python scripts/ci_gate_route_matrix.py` → **PASS**
- `make test-fast` → **PASS** (`478 passed, 12 skipped`)
- `make typecheck` → **PASS**
- `make frontend-build` → **PASS**
- `python scripts/verify_frontend_wiring.py` → **PASS** for route wiring (`missing_navigation_targets = 0`)
- `make ci` → **PASS** (lint + backend tests + typecheck + production build)
- `terraform fmt -check -recursive` (under `infra/terraform`) → **PASS**
- `terraform init -backend=false && terraform validate` (dev/staging/prod/dr) → **PASS**
- `checkov -d infra/terraform --config-file checkov.yml` → **FAIL** (`passed=649, failed=81, skipped=0`)

### Toolchain status in this container
- `terraform` installed: `v1.8.5`
- `aws` installed: `aws-cli/1.44.53`
- `checkov` installed: `3.2.508`

### Remaining blockers to claim “100% AWS deployment readiness”
1. **Infrastructure policy gate is red (Checkov)**
  - Current scan reports `81` failed policies (dominant groups include S3 logging/event notification and IAM policy constraints), so infra is not at zero-error policy posture yet.
2. **No authenticated AWS deployment context available in-session**
  - Without AWS credentials/OIDC session, production plan/apply and runtime smoke checks cannot be executed from this container.
3. **UI consistency debt remains (non-blocking for route wiring)**
  - `verify_frontend_wiring.py` reports `button_warnings = 41` (quality debt, not missing-route failures).

---

## 2) Benchmark requirements to beat (non-generic)

## Aladtec parity-plus requirements
From official capability pages (rotational scheduling, compliance, reporting, employee experience):
- 24/7 rotational templates and minimum staffing rules.
- Shift swap/trade/pickup with policy enforcement (seniority, overtime rules).
- Certification/credential expiration tracking and proactive alerts.
- Digital forms with completion tracking and audit readiness.
- Overtime/payroll export controls and budget trend reports.
- Mobile-first schedule and communications.

## Operative IQ parity-plus requirements
From official module pages (inventory, fleet, narcotics, blood):
- Station and field-level inventory with PAR/reorder logic.
- Purchase orders + transfer/issue lifecycle + kit restock workflows.
- Asset records with maintenance schedules and location custody.
- Fleet maintenance work orders, VMRS support, telematics integration.
- Narcotics cradle-to-grave chain-of-custody, discrepancy detection, audit reporting.
- Whole blood lifecycle and temperature logging with long-retention compliance workflows.
- RFID automation for real-time inventory and recovery.

## NEMSIS compliance requirements
From NEMSIS v3 technical resources and v3.5.1 data dictionary/XSD/API pages:
- Full v3.5.1 element and attribute compatibility.
- DEM/EMS/State schema alignment and versioned validation.
- NOT values, custom elements, UUID semantics, state dataset requirements.
- Developer-facing import/export and validation tooling with schema-version awareness.

## NERIS readiness requirements
From USFA/FSRI technical references and data/integration FAQs:
- CAD/RMS ingestion compatibility and API-based secure exchange.
- Near-real-time data flow model.
- Third-party integration readiness (vendor compatibility workflows).
- Strong PII ownership/isolation behavior and secure data transport posture.
- Compatibility lifecycle governance (track version drift windows and partner readiness).

---

## 3) System-by-system completion checklist (file/function level)

## A. Billing / EDI / RCM domination

### A1. Fix hard blocker in EDI import detection
- File: `backend/core_app/billing/edi_service.py`
- Action:
  - Replace direct `find_spec("linuxforhealth.x12.io")` usage with guarded parent-package probing (`linuxforhealth`) + exception-safe availability check.
  - Ensure runtime fallback path always uses manual parser when LFH unavailable.
- Done when:
  - `make test-fast` passes import stage and full suite gate.

### A2. Close typed-model TODO debt in billing command APIs
- File: `backend/core_app/api/billing_command_router.py`
- Action:
  - Replace TODO-backed dynamic payload assumptions with typed models for:
    - claim modifiers
    - billing alert thresholds
    - service level typing
    - payer follow-up typing
- Done when:
  - No TODO markers remain in billing command critical paths.
  - Endpoint contract tests validate strict schemas.

### A3. Build true billing “outperform” layer vs ESO/ImageTrend/Zoll billing modules
- Files:
  - `backend/core_app/services/billing_command_service.py`
  - `frontend/app/billing-command/page.tsx`
  - `frontend/app/founder/revenue/*`
- Action:
  - Add denial root-cause clustering, payer-level overturn probability, and queue-level recommended next action.
  - Add SLA timers per claim stage and auto-escalation logic.
  - Add “cash-at-risk” and “time-to-cash delta” per payer/program.
- Done when:
  - Founder and billing command pages expose deterministic action queues, not dashboard-only metrics.

## B. Scheduling / workforce parity-plus vs Aladtec

### B1. Scheduling fatigue report hardening
- File: `backend/core_app/api/scheduling_router.py`
- Action:
  - Verify fatigue endpoint computes rolling-window violations and policy exceptions from shift assignment data.
  - Add policy test matrix for 24/48/72-hour windows.
- Done when:
  - Endpoint has deterministic outputs and policy tests for union/fatigue constraints.

### B2. Shift trade/pickup fairness engine
- Files:
  - `backend/core_app/staffing/*`
  - `frontend/app/portal/scheduling/*`
- Action:
  - Implement ranked fill logic (seniority, overtime recency, cert match).
  - Add explainability payload per assignment decision.
- Done when:
  - Every schedule fill event has auditable “why this person” metadata.

### B3. Credential-aware scheduling
- Files:
  - `backend/core_app/models/*credential*` (add if missing)
  - `backend/core_app/services/*scheduling*`
- Action:
  - Block staffing assignment on expired/insufficient cert set.
  - Auto-generate training renewal queue.
- Done when:
  - Scheduler rejects non-compliant assignments pre-publish.

## C. Ops readiness parity-plus vs Operative IQ

### C1. KitLink typing and production reliability
- Files:
  - `frontend/app/portal/kitlink/page.tsx`
  - `frontend/app/portal/kitlink/wizard/page.tsx`
  - `frontend/app/portal/kitlink/inspection/page.tsx`
- Action:
  - Remove `any` usage and introduce strict domain types for items, kits, discrepancies, inspections.
  - Add explicit loading/error/retry states per data panel.
- Done when:
  - No `any` in KitLink pages; all API failures visible and recoverable.

### C2. Narcotics and blood custody analytics
- Files:
  - `backend/core_app/models/*`
  - `backend/core_app/api/*compliance*`, `backend/core_app/api/clinical_workflow_router.py`
- Action:
  - Add discrepancy trend detection (per crew, station, medication class).
  - Add blood temperature excursion alerts and retention checks.
- Done when:
  - Audit trail supports DEA/FDA/AABB-style inspections with deterministic report output.

### C3. Fleet maintenance + telematics alignment
- Files:
  - `backend/core_app/fleet/*`
  - `frontend/app/founder/ops/fleet/page.tsx`
- Action:
  - Add maintenance due model with severity + dispatch impact.
  - Add VMRS-compatible tagging and cost-per-mile trend reports.
- Done when:
  - Fleet backlog and mission risk correlation visible in founder ops command.

## D. NEMSIS + NERIS standards domination

### D1. NEMSIS 3.5.1 strict validation profile
- Files:
  - `backend/core_app/api/nemsis_manager_router.py`
  - `backend/core_app/compliance/nemsis_xml_generator.py`
  - `backend/core_app/nemsis/*`
- Action:
  - Enforce versioned dictionary + XSD validation with explicit profile outputs.
  - Publish per-submission explainability: failed element, rule, remediation suggestion.
- Done when:
  - Every failed submission returns machine-readable correction plan.

### D2. NERIS compatibility program implementation
- Files:
  - `backend/core_app/neris/*`
  - `frontend/app/founder/compliance/neris/page.tsx`
  - `frontend/app/portal/neris-onboarding/page.tsx`
- Action:
  - Implement vendor compatibility runbook automation:
    - incident create/update verification
    - station/unit create verification
    - compatibility check workflow state machine
  - Add “compatibility drift” monitor for API/schema updates.
- Done when:
  - Tenant can complete end-to-end NERIS onboarding without manual backend intervention.

## E. Founder command, AI, and visual domination

### E1. Remove mock fallback behavior from patient/founder surfaces
- Files:
  - `frontend/app/portal/patient/documents/page.tsx`
  - `frontend/app/portal/patient/payment-plans/page.tsx`
  - `frontend/app/portal/patient/profile/page.tsx`
  - `frontend/app/portal/patient/receipts/page.tsx`
  - `frontend/app/portal/patient/activity/page.tsx`
- Action:
  - Replace `MOCK_*` fallbacks with explicit degraded-state UX and telemetry events.
- Done when:
  - Zero mock fallback constants in production routes.

### E2. Founder dashboard strict typing and deterministic UX
- Files:
  - `frontend/app/founder/page.tsx`
  - `frontend/app/founder/ops/command/page.tsx`
  - `frontend/app/system-health/page.tsx`
- Action:
  - Remove `any` from core founder data models.
  - Replace console-only fetch catches with surfaced, actionable failures.
- Done when:
  - Founder command can operate without hidden failures.

### E3. Visual system hardening (brand + consistency)
- Inputs: `scripts/verify_frontend_wiring.py` report (41 button warning items)
- Action:
  - Normalize critical CTA components to shared design primitives.
  - Eliminate hardcoded highlight hex values in founder/portal command surfaces.
- Done when:
  - UI lint/check returns 0 token drift + 0 style warning hotspots for command-critical pages.

### E4. AI safety and deterministic fallback
- Files:
  - `backend/core_app/services/ai_platform/tax_advisor_service.py`
  - `frontend/components/founder/copilot/FounderCopilotPanel.tsx`
- Action:
  - Replace stubbed responses with production model adapters behind feature flags.
  - Enforce validation and deterministic fallback payload contracts.
- Done when:
  - AI failure never blocks workflows and never silently degrades without surfaced state.

## F. AWS deployment + zero-error production readiness

### F1. CI gate stack (required for merge)
- Required green gates:
  - `make test-fast`
  - `make typecheck`
  - `make frontend-build`
  - `python scripts/ci_gate_route_matrix.py`
  - `python scripts/verify_frontend_wiring.py`
- Action:
  - Treat any red gate as merge blocker.
- Done when:
  - Main branch protected by these required checks.

### F2. Terraform production hardening validation
- Paths:
  - `infra/terraform/environments/prod/*`
  - `infra/terraform/modules/*`
- Action:
  - Add/verify policy checks for:
    - no wildcard admin rights except bounded break-glass role
    - secrets from Secrets Manager only
    - private data planes only (RDS/Redis)
    - WAF attached to public edges
  - Validate GH OIDC deploy role is least-privilege and auditable.
- Done when:
  - Terraform plan/apply in prod emits zero policy violations in CI security checks.

### F3. Release readiness proof
- Action:
  - Add canary health probes for backend critical paths:
    - auth
    - billing ingestion
    - scheduling mission-critical calls
    - NEMSIS/NERIS submission paths
  - Add rollback trigger policy with objective SLO thresholds.
- Done when:
  - One-click rollback path verified in staging and documented.

---

## 4) Immediate execution queue (next 10 days)

## Day 1-2 (hard blockers)
1. ✅ Verify `linuxforhealth` import handling in `edi_service.py` and confirm backend test pass.
2. ✅ Re-run frontend wiring verification and confirm `missing_navigation_targets = 0`.
3. ✅ Re-run required app gates (`test-fast`, `typecheck`, `frontend-build`, `route_matrix`, `verify_frontend_wiring`, `make ci`).
4. ✅ Install/enable AWS IaC toolchain in execution runner (`terraform`, `aws`, `checkov`) and run infrastructure validation gates (`terraform fmt`, `terraform validate`, `checkov`).

## Day 3-5 (command-surface reliability)
5. Remediate current Checkov policy failures to bring infrastructure security gate to 0 failed checks.
6. Remove `MOCK_*` fallbacks from patient portal pages listed above.
7. Replace silent/console-only catch patterns in founder/system-health/billing command pages.
8. Remove `any` from founder dashboard + kitlink command pages.

## Day 6-10 (competitive differentiation)
9. Implement scheduling fairness explanation payloads (Aladtec-plus target).
10. Implement inventory/narcotics/blood anomaly detection reports (OperativeIQ-plus target).
11. Ship NEMSIS v3.5.1 strict remediation payloads and NERIS compatibility workflow automation.

---

## 5) “Domination level” acceptance criteria

A release is only marked domination-ready when all are true:
1. **All required gates green** (including wiring verification).
2. **No production mocks** on founder/patient/ops command-critical routes.
3. **No hidden error handling** (silent catches removed from command surfaces).
4. **NEMSIS + NERIS flows complete** with explainable validation and compatibility state machine.
5. **Scheduling + inventory + narcotics + blood + fleet** workflows produce auditable event trails and actionable intelligence.
6. **AWS deployment proven** with canary, rollback, and policy-compliant Terraform in prod.

---

## 6) Competitive scorecard tracking (must be measured weekly)

- **Scheduling intelligence score** (Aladtec baseline + fairness explainability + cert enforcement).
- **Ops readiness score** (Operative IQ baseline + anomaly prediction + integrated mission risk).
- **Data interoperability score** (NEMSIS pass rates + NERIS compatibility checks + sync latency).
- **Revenue velocity score** (clean-claim %, denial reversal speed, cash acceleration).
- **Command UX score** (task completion latency, zero hidden failures, accessibility and consistency).

If any score regresses week-over-week, release is blocked until corrected.

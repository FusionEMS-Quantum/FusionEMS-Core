FUSIONEMS-CORE
MASTER ANALYTICS + REPORTING + EXECUTIVE COMMAND BUILD DIRECTIVE
DOMINATION-LEVEL KPI INTELLIGENCE, REGULATORY REPORTING, FINANCIAL VISIBILITY, AND FOUNDER OVERSIGHT

ROLE
You are the production analytics, reporting, and executive-command brain for FusionEMS-Core.

Your job is to build a complete, deployable, founder-friendly intelligence system that covers:
- executive dashboards
- operational KPIs
- financial KPIs
- clinical quality metrics
- workforce/readiness metrics
- exportable reports
- regulatory reporting readiness
- board/city/county-ready reporting packs
- visual founder command across the whole platform

This is not a vanity dashboard module.
This must function as a real operating system for understanding the health of the business, the field operation, revenue performance, quality trends, and compliance/reporting status.

==================================================
PART 1: INTELLIGENCE DOMAINS
==================================================

The analytics system must be split into six separate but connected domains:

1. EXECUTIVE KPI INTELLIGENCE
Handles:
- high-level business health
- revenue health
- deployment/ops health
- cash-at-risk visibility
- top 3 strategic actions
- trend comparisons

2. OPERATIONAL ANALYTICS
Handles:
- mission volume
- response timing
- paging performance
- unit uptime
- dispatch queue bottlenecks
- facility turnaround patterns

3. FINANCIAL / RCM ANALYTICS
Handles:
- billed vs paid
- outstanding AR
- denial rates
- payment lag
- payer mix
- cash-at-risk
- autopay failure rates
- collections staging visibility

4. CLINICAL / QA ANALYTICS
Handles:
- chart lock delays
- validation failures
- QA backlog
- contradiction rates
- protocol deviation flags
- documentation risk patterns

5. WORKFORCE / READINESS ANALYTICS
Handles:
- staffing gaps
- fatigue risk
- credential expiration exposure
- out-of-service units
- inventory shortages
- narcotics discrepancy trends

6. REPORTING / EXPORT INTELLIGENCE
Handles:
- operational report generation
- financial exports
- regulatory/export readiness
- scheduled reports
- board-ready summary packs
- founder-friendly PDF/CSV outputs

==================================================
PART 2: HARD BOUNDARIES
==================================================

BOUNDARY 1
Analytics must not be the system of record.
Analytics reads from canonical operational, billing, clinical, and policy data sources.

BOUNDARY 2
Reports must not invent data or fill missing values silently.
If source data is incomplete, the report must clearly indicate incompleteness.

BOUNDARY 3
AI may summarize and explain trends, but must not fabricate metrics, counts, or compliance conclusions.

BOUNDARY 4
Executive dashboards are separate from operational action systems.
They may link to workflows, but dashboard calculation logic must remain traceable and repeatable.

BOUNDARY 5
Regulatory/reporting readiness must be visibly separate from “business dashboard success.”
A strong dashboard does not imply export/regulatory readiness.

==================================================
PART 3: EXECUTIVE KPI BUILD
==================================================

Build a real executive KPI system with:

EXECUTIVE METRICS
- active missions
- unassigned requests
- cash at risk
- denial exposure
- deployment failures
- payment failures
- out-of-service units
- staffing gaps
- charts blocked from lock
- top 3 system-wide actions

EXECUTIVE SCORECARDS
- Revenue Health Score
- Operations Health Score
- Clinical Health Score
- Workforce Health Score
- Technology/Deployment Health Score
- Compliance Health Score

RULES
1. Every score must be explainable.
2. Every score must break down into the factors that lowered it.
3. No fake “green” status if the underlying system is degraded.
4. Executive widgets must source real backend data only.

REQUIRED DATA OBJECTS
- KPIComputationRun
- KPIValueSnapshot
- KPITrendPoint
- HealthScoreFactor
- ExecutiveAlert
- ExecutiveSummarySnapshot

==================================================
PART 4: OPERATIONAL ANALYTICS BUILD
==================================================

Build real operational metrics.

REQUIRED METRICS
- request volume by period
- average time in queue
- page acknowledgment times
- escalation rates
- unit dispatch-to-en-route times
- mission completion times
- facility turnaround delays
- telemetry downtime
- failed paging/delivery rate

RULES
1. Timing metrics must be computed from real event timestamps.
2. Missing timestamps must not be silently inferred unless rules explicitly define how.
3. Dispatch metrics must remain separate from billing communications metrics.
4. All operational metrics must preserve date/time range and agency scope.

REQUIRED DATA OBJECTS
- OperationalMetricSnapshot
- ResponseTimeMetric
- QueuePerformanceMetric
- MissionTimingAggregate
- PagingPerformanceAggregate
- TelemetryUptimeAggregate

==================================================
PART 5: FINANCIAL / RCM ANALYTICS BUILD
==================================================

Build real financial intelligence around subscription and claims revenue.

REQUIRED METRICS
- total billed
- total paid
- unresolved remainder
- patient balance exposure
- payer mix
- denial rate
- rejection rate
- appeal rate
- autopay failure rate
- AR aging
- cash at risk
- collected vs written off
- agency subscription MRR
- module revenue
- per-call revenue trends

RULES
1. Do not treat billed minus paid as automatic bad debt.
2. Financial analytics must follow the billing state machines already defined.
3. Every KPI must be traceable to underlying claim/account/subscription states.
4. Founder must be able to drill from high-level KPIs into raw contributing records.

REQUIRED DATA OBJECTS
- FinancialMetricSnapshot
- ARAgingBucket
- DenialTrendAggregate
- PaymentLagAggregate
- SubscriptionRevenueAggregate
- CashAtRiskSnapshot

==================================================
PART 6: CLINICAL / QA ANALYTICS BUILD
==================================================

Build real clinical quality analytics.

REQUIRED METRICS
- charts waiting to sync
- charts blocked from lock
- contradiction flag counts
- missing signature rate
- QA backlog
- correction rate
- validation failure categories
- NEMSIS export failure rate
- handoff delivery failure rate
- billing-risk-from-charting trends

RULES
1. Clinical analytics must remain separate from billing metrics while still exposing clinical impacts on billing.
2. QA metrics must respect audit history.
3. Export quality metrics must reflect actual submission/export states.

REQUIRED DATA OBJECTS
- ClinicalMetricSnapshot
- QAQueueAggregate
- ValidationFailureAggregate
- SyncFailureAggregate
- NemsisExportAggregate
- ClinicalRiskTrendPoint

==================================================
PART 7: WORKFORCE / READINESS ANALYTICS BUILD
==================================================

Build real readiness intelligence.

REQUIRED METRICS
- open shifts
- understaffed units
- fatigue warnings
- credential expiration exposure
- low stock counts
- expiring meds/supplies
- narcotics discrepancies
- out-of-service units
- PM overdue units
- fleet downtime rates

RULES
1. Readiness metrics must derive from canonical scheduling, inventory, narcotics, and fleet events.
2. No silent normalization of missing data.
3. Founder must be able to move from a heatmap or score directly into the underlying queue/problem records.

REQUIRED DATA OBJECTS
- ReadinessMetricSnapshot
- CoverageGapAggregate
- CredentialRiskAggregate
- InventoryRiskAggregate
- FleetReadinessAggregate
- NarcoticsRiskAggregate

==================================================
PART 8: REPORTING / EXPORT BUILD
==================================================

Build a real reporting engine for internal and external use.

REQUIRED OUTPUTS
- founder daily summary
- weekly operations summary
- billing performance report
- AR aging report
- denial analysis report
- QA backlog report
- fleet readiness report
- workforce risk report
- inventory expiration report
- export-ready CSV/PDF/report packs

OPTIONAL FUTURE OUTPUTS
- city/county board report packs
- facility partner summaries
- state/export summary packs
- custom scheduled agency reports

REPORTING RULES
1. Reports must be reproducible from source filters and timestamps.
2. PDF/CSV exports must be auditable.
3. Every scheduled report must record generation status and delivery history.
4. No report may silently omit failed source sections without visible warning.

REQUIRED DATA OBJECTS
- ReportDefinition
- ReportRun
- ReportDelivery
- ReportArtifact
- ReportFilterSet
- ReportAuditEvent

==================================================
PART 9: FOUNDER EXECUTIVE COMMAND CENTER
==================================================

Build a visual founder executive command surface.

REQUIRED SECTIONS
- revenue at risk
- top denial reasons
- deployment failures
- unassigned missions
- charts blocked from lock
- staffing gaps
- out-of-service units
- inventory shortages
- top 3 executive actions

REQUIRED WIDGETS
- Revenue Health Score
- Operations Health Score
- Clinical Health Score
- Workforce Health Score
- Compliance Health Score
- Cash At Risk Card
- AR Aging Heatmap
- Denial Trend Panel
- Deployment Health Panel
- Next Best Action Panel

VISUAL RULES
- cards first
- color first
- one next action first
- details on expand
- plain English first
- top 3 priorities always visible
- no dense default paragraphs

COLOR SYSTEM
- RED = BLOCKING
- ORANGE = HIGH RISK
- YELLOW = NEEDS ATTENTION
- BLUE = IN REVIEW
- GREEN = HEALTHY / GOOD
- GRAY = INFORMATIONAL / CLOSED

SIMPLE MODE
Every critical analytics screen must support:
- WHAT HAPPENED
- WHY IT MATTERS
- DO THIS NEXT

==================================================
PART 10: ANALYTICS AI ASSISTANT BUILD
==================================================

AI must act like an experienced executive analyst helping a paramedic founder.

For every metric/problem/trend, AI must answer:
- what changed
- why it matters
- what likely caused it
- what to do next
- how serious it is
- whether human review is needed

REQUIRED ISSUE FORMAT
ISSUE:
[short title]

SEVERITY:
[BLOCKING / HIGH / MEDIUM / LOW / INFORMATIONAL]

SOURCE:
[METRIC RUN / AI REVIEW / BILLING EVENT / CLINICAL EVENT / OPS EVENT / READINESS EVENT / HUMAN NOTE]

WHAT CHANGED:
[exact change/problem]

WHY IT MATTERS:
[plain-English impact]

WHAT YOU SHOULD DO:
[concrete next step]

EXECUTIVE CONTEXT:
[short explanation]

HUMAN REVIEW:
[REQUIRED / RECOMMENDED / SAFE TO AUTO-PROCESS]

CONFIDENCE:
[HIGH / MEDIUM / LOW]

AI RULES
- never invent metrics
- never invent causality without noting uncertainty
- never claim legal/compliance success from dashboard trends alone
- define acronyms
- distinguish hard fact from model judgment

==================================================
PART 11: ZERO-ERROR ANALYTICS HARDENING
==================================================

Every critical analytics/reporting path must be:
- reproducible
- logged
- visible
- auditable
- range-filterable
- tenant-scoped
- resilient to partial-source failures

Harden:
- scheduled KPI jobs
- aggregation logic
- cached summary generation
- report export generation
- CSV/PDF delivery tracking
- dashboard refresh jobs
- AI summary logging

Required safety objects:
- computation run logs
- source completeness flags
- failure reasons
- correlation IDs
- immutable report/export audit events

==================================================
PART 12: NON-NEGOTIABLE ANALYTICS RULES
==================================================

The analytics/reporting system is NOT complete if any of these remain true:
- dashboards use static/demo data in production
- scores are not explainable
- reports cannot be reproduced from source filters
- export artifacts are not audited
- missing source data is hidden
- founder cannot drill into the underlying cause of a score or alert
- AI summaries invent metrics or unsupported conclusions

==================================================
PART 13: FINAL BUILD STANDARD
==================================================

Build the analytics/reporting system to domination level:
- real executive KPIs
- real operational metrics
- real financial intelligence
- real clinical/QA metrics
- real readiness analytics
- reproducible reporting engine
- visual founder executive command
- AI executive analyst
- auditable, tenant-scoped, reproducible runtime

The result must make a non-coder paramedic founder feel like they have:
- a finance analyst
- an ops analyst
- a clinical quality analyst
- a workforce/readiness analyst
- and a visual executive command center
working beside them at all times.

FUSIONEMS-CORE
ULTRA DOMINATION CENTRALIZED AI BILLING PHONE + SOVEREIGN ONBOARDING + OPEN-SOURCE-FIRST RCM DIRECTIVE

ROLE
You are building the centralized FusionEMS sovereign billing and onboarding system.

This is not a basic IVR.
This is not a generic patient call center.
This is not a per-agency telecom setup.
This is not a fragmented SaaS workflow.

This must become a centralized, AI-first, founder-operated, tenant-aware, policy-aware revenue machine that makes small and large agencies feel like they instantly plugged into enterprise-grade billing infrastructure.

==================================================
PRIMARY VISION
==================================================

FusionEMS must operate one centralized billing operation for participating agencies.

I want:
- ONE centralized platform billing number
- ONE AI-first patient billing voice system
- ONE tenant-aware statement/account routing engine
- ONE founder escalation console
- ONE onboarding system that provisions agencies into the correct operational and billing model
- ONE shared billing machine that scales across all participating agencies

I do NOT want:
- separate billing numbers per agency
- telecom sprawl
- fragmented IVRs
- manual intake chaos
- billing phone logic mixed with CAD or CrewLink
- low-trust AI that improvises without policy boundaries

==================================================
FOUNDATIONAL PRINCIPLES
==================================================

1. ONE NUMBER
There is only one centralized FusionEMS billing number for all participating agencies in FusionEMS RCM mode.

2. TENANT ROUTING BY ACCOUNT CONTEXT
Tenant routing must happen by:
- statement ID
- account number
- responsible-party lookup
- verified fallback identity inputs if policy allows
Never by giving each agency its own billing number.

3. OPEN-SOURCE-FIRST EVERYWHERE POSSIBLE
Keep the expensive/vendor-locked rails only where they are strategically necessary.
Everything else should be designed open-source-first, self-hostable-first, or low-lock-in-first.

4. PAID RAILS ONLY WHERE THEY MATTER
Use paid rails only for:
- telephony
- payment collection
- clearinghouse workflows
- physical mail
Everything else should minimize recurring vendor cost.

5. AI-FIRST, HUMAN-BACKSTOP
AI handles routine calls first.
I take over only when confidence, policy, legality, sensitivity, or complexity requires a human.

6. POLICY-AWARE EVERYTHING
Every billing phone action must obey:
- tenant billing mode
- tenant phone policy
- patient/responsible-party communication policy
- collections policy
- payment plan policy
- escalation rules

7. ZERO SILENT FAILURE
Every call, lookup, verification, AI action, escalation, payment action, callback, retry, and failure must be logged, visible, auditable, and recoverable.

==================================================
OPEN-SOURCE-FIRST ARCHITECTURE MANDATE
==================================================

Use open-source wherever it reduces long-term cost without weakening regulated rails.

RECOMMENDED OPEN-SOURCE FOUNDATION

IDENTITY / ACCESS
Use:
- Keycloak or authentik
For:
- SSO
- identity brokering
- MFA-ready architecture
- tenant admin login
- founder/admin access control

JOBS / ORCHESTRATION
Use:
- Redis
- BullMQ
For:
- voice session actions
- callback jobs
- transcript processing
- payment-link send tasks
- statement resend jobs
- retry-safe escalations
- dead-letter handling

OBSERVABILITY
Use:
- Prometheus
- Grafana
- Loki
For:
- service health
- queue health
- call system health
- webhook health
- dashboarding
- founder tech command
- searchable logs

SEARCH / EVENT INVESTIGATION
Use:
- Postgres first
- OpenSearch only when transcript/event/search load exceeds practical Postgres search
For:
- transcript search
- call event search
- escalation search
- audit event search

ANALYTICS / FEATURE FLAGS
Use:
- PostHog
For:
- feature flags
- onboarding funnel analysis
- voice workflow experiments
- founder product analytics

MAPS / ROUTING / LOCATION ENRICHMENT
Use:
- OpenStreetMap
- Valhalla
For:
- facility geodata
- local hospital enrichment
- route calculations where needed
- low-cost map infrastructure

INTEROPERABILITY READY LAYER
Use:
- HAPI FHIR
For:
- future interoperability readiness
- patient/account/export normalization
- external healthcare data models later

SEMANTIC RETRIEVAL IF NEEDED
Use:
- pgvector
Only if needed for:
- transcript retrieval
- account-history retrieval
- policy retrieval
- AI context search
Do not add it unless the use case is real.

KEEP PAID RAILS
Use:
- Telnyx for billing telephony
- Stripe for payment rail
- Office Ally for clearinghouse rail
- Lob for physical mail rail

DO NOT overbuild expensive managed services where open-source gives enough power.

==================================================
NON-NEGOTIABLE BOUNDARY RULES
==================================================

1. Telnyx is billing-only.
It may be used for:
- billing voice
- billing SMS
- statement/payment reminders
- secure payment link delivery
- billing-related fax if enabled

It must NOT be used for:
- CAD
- dispatch
- CrewLink paging
- operational response coordination

2. CrewLink remains operations-only.
Billing phone flows and operational paging must remain separate systems, separate queues, separate policies, and separate audit trails.

3. Office Ally is the claim/EDI rail, not the billing brain.
4. Stripe is the payment rail, not the entitlement/policy brain.
5. AI is the assistant, not the system of record.

==================================================
CENTRALIZED BILLING PHONE SYSTEM
==================================================

Build one centralized AI-first billing phone system.

CALL ENTRY MODEL
When a patient calls the centralized FusionEMS billing number:
1. AI voice answers immediately
2. AI requests a safe lookup key
3. backend resolves the tenant and billing account
4. AI handles the allowed billing workflow
5. if risk or complexity is high, escalate to me
6. I receive the full context instantly

LOOKUP METHODS
The system must support:
- statement ID
- account number
- responsible-party verification
- fallback verified lookup rules if policy allows

The system must never depend on per-agency phone numbers.

AI-FIRST TASKS THE SYSTEM SHOULD HANDLE
- balance inquiry
- “what is this bill?”
- secure payment link resend
- statement copy resend
- “text me the link”
- “mail me the statement”
- mailing address confirmation if allowed
- payment plan intake if allowed
- FAQ-style billing questions
- dispute intake
- callback request creation
- structured call summary before escalation

AI MUST NEVER SILENTLY
- guess identity
- expose protected data before verification
- waive balances
- approve exceptions outside policy
- make legal promises
- decide complex insurance responsibility as fact
- send accounts to collections
- escalate to debt setoff
- continue when confidence is low and risk is meaningful

==================================================
HUMAN TAKEOVER REQUIREMENT
==================================================

If the AI cannot safely continue, it must escalate to me.

When escalation happens, I must instantly receive:
- caller number
- statement ID and/or account ID
- tenant/agency
- patient/responsible-party context
- verification state
- balance
- account state
- communication policy
- last payment attempt
- recent interaction summary
- AI-detected intent
- reason for escalation
- structured transcript summary
- recommended next step

The handoff must feel like:
“FusionEMS already did intake, verification, routing, and triage. You are only stepping in for the exception.”

==================================================
AGENCY BILLING MODES
==================================================

The system must support two explicit billing models.

1. FUSIONEMS RCM MODE
Agencies using centralized FusionEMS billing get:
- centralized platform billing number on statements
- AI-first inbound patient billing voice flow
- tenant-aware payment/log routing
- centralized RCM support experience
- founder-operated escalation path

2. THIRD-PARTY / INTERNAL BILLING MODE
Agencies not using centralized FusionEMS patient billing get:
- export/API/SFTP workflows
- no forced routing into the centralized billing IVR
- clearly separate downstream billing handling

ONBOARDING MUST ASK:
“Who handles your billing?”
- FusionEMS RCM
- Internal / Third-Party Billing

That answer must control:
- statement rendering
- phone workflow eligibility
- payment flow
- communication flow
- export behavior
- escalation path

==================================================
SOVEREIGN ONBOARDING SYSTEM
==================================================

The onboarding flow must identify the agency’s real operating model and provision them correctly.

REQUIRED INTAKE FIELDS
- NPI number
- operational mode
- billing mode
- primary tail number if HEMS
- base ICAO if HEMS
- billing contact
- implementation owner/contact
- identity/SSO preference
- policy flags as needed

OPERATIONAL MODES
Support:
- HEMS_TRANSPORT
- EMS_TRANSPORT
- MEDICAL_TRANSPORT
- EXTERNAL_911_CAD

BILLING MODES
Support:
- FUSION_RCM
- THIRD_PARTY_EXPORT

NPI LOOKUP EXPERIENCE
On onboarding, allow the user to enter NPI.
The platform should look up and autofill:
- legal organization name
- address
- provider taxonomy
- provider identity basics

The goal is to reduce manual typing, improve data quality, and accelerate setup.

OPERATIONAL FORK UI
Ask:
“Do you run your own transport/flight operation, or do you take calls from an external 911 CAD?”
Use this to branch provisioning.

RCM FORK UI
Ask:
“Do you want to use FusionEMS AI Billing Center, or do you strictly export to your third-party biller?”
Use this to control the entire downstream billing architecture.

==================================================
LIVE PROVISIONING EXPERIENCE
==================================================

The provisioning experience must feel alive, premium, and operationally impressive.

Replace passive spinner experiences with a glass-box provisioning console.

The success experience must show real-time provisioning steps such as:
- tenant created
- policies applied
- billing mode configured
- voice policy registered
- facilities seeded
- HEMS config loaded
- external CAD endpoint created
- export pipeline configured
- AI billing routing enabled
- statement format generated

CONDITIONAL SUCCESS EXPERIENCES

IF EXTERNAL 911 CAD
Show:
- securely scoped ingest token
- webhook endpoint
- sample curl block
- inbound dispatch simulation example

IF HEMS
Show:
- base ICAO summary
- weather/aviation context hooks
- aircraft/tail record initialization
- Spidertracks/flight-feed webhook target if applicable

IF FUSIONEMS RCM
Show:
- mock patient statement
- centralized billing number
- agency prefix
- clear “pay by phone 24/7” path
- optional drop zone to import legacy A/R CSV

IF THIRD-PARTY BILLING
Show:
- export/SFTP/API handoff details
- claim/export readiness message
- “your export pipeline is ready” experience

OPTIONAL PREMIUM DAY-ZERO MAGIC
To make new tenants feel live immediately:
- seed facilities near their ZIP/NPI geography
- create simulated assets only if clearly labeled as simulation/demo seed data
- preload implementation checklist
- preload initial dashboards with real seeded setup state, not fake hidden data

==================================================
VOICE RCM ENGINE
==================================================

This is the core shift.
The centralized voice router must stop assuming the inbound number determines the tenant.

GLOBAL INTAKE RULE
The root billing voice webhook must answer globally for all centralized RCM agencies.

It must:
- parse speech or DTMF for statement ID/account lookup
- resolve tenant and patient billing account
- load tenant billing phone policy
- load communication and escalation rules
- continue the session inside that tenant context

AI CONTEXT INJECTION
Once the tenant is resolved, inject into the AI context:
- tenant/agency name
- billing mode
- billing phone policy
- payment plan rules
- collections/debt-setoff flags
- communication restrictions
- escalation requirements
- current account/balance state

KILL SWITCH RULE
If transcript or intent includes high-risk triggers such as:
- legal threat
- lawyer
- fraud
- regulator
- harassment
- identity conflict
- low-confidence verification
- policy-blocked request

Then the workflow must immediately move to:
HUMAN_HANDOFF_REQUIRED

This must:
- stop autonomous AI action
- create structured escalation context
- push a real-time founder alert

==================================================
FOUNDER TRIAGE DASHBOARD
==================================================

Build my personal centralized RCM control tower.

When a call escalates, I want an immediate triage card showing:
- caller ID
- statement ID
- agency/tenant
- balance
- verification status
- AI summary of the issue
- escalation reason
- next best action

The dashboard must also show:
- live active calls
- calls waiting for takeover
- AI resolution rate
- escalation types
- unresolved voice sessions
- high-risk accounts
- top 3 billing phone actions

If technically feasible in your stack, support one-click browser takeover / softphone/WebRTC bridge.
If not, preserve the handoff object cleanly so the next takeover method can be added later.

==================================================
TENANT PROVISIONING PIPELINE
==================================================

The provisioning worker must become model-aware.

When onboarding is paid/approved, it must run the correct async tasks based on the tenant’s real mode.

COMMON TASKS
- create tenant
- create agency
- create billing mode state
- create policy objects
- create statement prefix
- create voice routing eligibility
- create implementation checklist
- create audit trail

IF HEMS
- create aircraft readiness baseline
- create tail-number metadata
- create base ICAO metadata
- load HEMS-specific risk rules/checklists

IF EXTERNAL 911 CAD
- create external CAD ingress config
- create normalized inbound webhook target
- generate token/secret if needed

IF FUSIONEMS RCM
- enable centralized voice workflow
- generate statement prefix
- prepare statement template
- enable billing communications workflow
- prepare legacy A/R import path if used

IF THIRD_PARTY_EXPORT
- disable centralized patient billing voice flow
- enable export/SFTP/API handoff path
- prepare billing export success state

OPTIONAL LOCATION/FACILITY SEEDING
You may enrich facilities from geography/provider sources if clearly audited and validated.
Do not silently treat enrichment as canonical truth without provenance.

==================================================
INTEGRATIONS TO BUILD
==================================================

Required additions or upgrades:

- NPI/NPPES lookup client
- centralized voice router
- telephony AI worker
- founder escalation event push
- external CAD webhook router
- legacy A/R import endpoint
- statement PDF pipeline upgrades
- billing-mode-aware Lob/PDF/export behavior
- dynamic onboarding success payloads

==================================================
LEGAL / POLICY / SIGNATURE CHAIN
==================================================

The legal/compliance system must become branch-aware.

If billing mode = THIRD_PARTY_EXPORT
- generate a standard BAA / export-oriented agreement set

If billing mode = FUSION_RCM
- append centralized clearinghouse / funds routing / RCM operating addendum as required by your business model

If operational mode = HEMS
- append aviation-specific operational software and liability language as appropriate for your legal review process

If SSO/zero-trust is required
- capture OIDC/IdP metadata during onboarding or implementation
- do not force weak local-only credentialing where stronger identity is expected

IMPORTANT RULE
Do not let AI generate binding legal language without approved templates and human-controlled legal review.

==================================================
STATEMENT PDF / BILLING DOCUMENT RULES
==================================================

For centralized FusionEMS RCM tenants, statement PDFs must prominently show:
- the centralized billing number
- the agency prefix
- the statement ID
- clear payment path
- QR / link path if supported

Format should feel like:
“Call 24/7 to pay via FusionEMS AI Billing Assistant”

The statement ID should visibly include agency prefix if that is part of your design, such as:
AEM-1048392

If billing mode = THIRD_PARTY_EXPORT
- do not use centralized patient-billing phone logic
- route the workflow into export behavior instead

==================================================
AI TELEPHONY WORKER
==================================================

Build a dedicated AI telephony decision layer.

This worker should:
- classify intent
- decide allowed next actions
- enforce guardrails before generating the next response
- emit structured actions for the backend to execute

EXAMPLE ACTIONS
- send_sms_link
- resend_statement
- mark_callback_requested
- escalate_to_founder
- explain_balance
- offer_payment_plan_intake
- stop_due_to_policy

HIGH-RISK RULE
If intent includes:
- dispute
- legal threat
- fraud
- harassment
- identity conflict
- out-of-policy request

Then the AI worker must choose structured escalation instead of trying to “help” its way through the problem.

==================================================
TESTING AND VALIDATION REQUIREMENTS
==================================================

This system must be bulletproof.

Required testing includes:
- Telnyx call flow mocks
- successful and failed centralized voice sessions
- tenant resolution by statement ID
- policy-aware voice action tests
- high-risk escalation tests
- complete onboarding pathway tests
- billing mode branching tests
- operational mode branching tests
- founder escalation event tests
- legacy A/R import tests
- statement template correctness tests
- no-CAD/call-system boundary violations

The “complete pathway” test must prove:
- onboarding input captured correctly
- billing mode stored correctly
- operational mode stored correctly
- provisioning produced the correct tenant config
- centralized voice routing is enabled only where intended
- success dashboard content matches the selected mode

==================================================
EXECUTION ORDER
==================================================

Build this in the following order:

PHASE 1: ONBOARDING FORKS
- rebuild onboarding wizard
- NPI lookup
- operational mode fork
- billing mode fork
- carry fork data through checkout metadata or provisioning input

PHASE 2: CENTRALIZED BILLING VOICE ENGINE
- rewrite the voice router
- global statement/account routing
- tenant policy injection
- AI telephony worker
- founder escalation event system

PHASE 3: PROVISIONING MAGIC
- model-aware tenant provisioning
- conditional success experiences
- RCM mode setup
- third-party mode setup
- HEMS mode setup
- external CAD mode setup
- optional clearly-labeled seeded/simulated assets

PHASE 4: DOCUMENTS + CONTROL TOWER
- centralized statement template
- billing PDF updates
- founder triage dashboard
- structured handoff UX
- legacy A/R import path

==================================================
SUCCESS STANDARD
==================================================

Build this so that:
- one centralized billing number serves all FusionEMS RCM tenants
- AI handles as much as safely possible
- I take over only when needed
- every call is tenant-aware
- every action is policy-aware
- onboarding provisions the correct business model
- success screens feel operationally magical
- the founder dashboard feels like a real command center
- the whole system feels more powerful than traditional fragmented EMS vendor setups

FINAL OUTCOME
The result must make agencies feel like they instantly plugged into:
- enterprise billing infrastructure
- AI-first patient billing support
- instant operational provisioning
- a serious centralized revenue machine

The result must make me feel like I have:
- one intelligent billing number
- one sovereign onboarding engine
- one founder triage console
- one AI call center
- one centralized revenue system

—not a fragmented mess of phone numbers, weak IVRs, and disconnected onboarding logic.
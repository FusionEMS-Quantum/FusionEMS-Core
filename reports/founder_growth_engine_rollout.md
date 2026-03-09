# Founder Growth Engine + Command Center Rollout (Real-Status)

## Scope delivered

This rollout activates real founder growth operations through existing production-backed data stores and connector infrastructure.

### New backend APIs (all founder-only)

- `GET /api/v1/founder/integration-command/growth-summary`
  - Real aggregates from `conversion_events`, `proposals`, `tenant_subscriptions`, `lead_scores`
  - Includes pipeline and conversion metrics, stage/tier/score distributions, and integration health

- `GET /api/v1/founder/integration-command/growth-setup-wizard`
  - Real connection/health model from connector installs + webhook deliveries + secret materializations
  - Returns required/optional services, token state, permission state, retry state, activity timestamps
  - Computes `autopilot_ready` + explicit `blocked_items`

- `POST /api/v1/founder/integration-command/launch-orchestrator/start`
  - Starts a real orchestrator run and writes event record to `platform_events`
  - Optionally queues real connector sync jobs for active/validated installs
  - Blocks autopilot runs when required setup prerequisites are not met

## Frontend control surface

Updated `frontend/app/founder/integration-command/page.tsx` now includes:

- Real Growth Engine runtime metrics panel
- Visual setup wizard service cards with required/optional status
- Launch orchestrator controls (autopilot / approval-first / draft-only)
- Live run status and queued sync job counts
- 15-second real-time refresh polling for status/telemetry

## Real-status rules

- No placeholder values are emitted by the new APIs.
- Queue counts represent actual persisted queue records.
- Connection status is based on persisted install state + secret materialization + webhook/sync telemetry.
- Autopilot readiness is blocked if required services are not sufficiently connected.

## Required services for autopilot readiness

- LinkedIn
- X
- Facebook
- Instagram
- Microsoft 365 Outlook
- Booking/Scheduling
- Domain + DNS
- Analytics
- Lead Store/CRM Pipeline

Optional:

- YouTube
- Demo render provider

## Verification checklist

1. Connect required services in integration command center.
2. Confirm setup wizard shows `autopilot_ready=true`.
3. Start launch orchestrator in `approval-first` mode.
4. Verify:
   - run status is `started`
   - sync jobs are queued
   - run event exists in `platform_events`
5. Switch to `autopilot` only after all blocked items are resolved.

## Test evidence in this change

- Backend tests:
  - `tests/test_founder_command_domain_service.py`
  - `tests/test_founder_integration_command_router.py`
- Frontend gate:
  - `npm run typecheck`

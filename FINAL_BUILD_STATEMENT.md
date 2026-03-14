# FusionEMS Quantum: Centralized Go-Live Build Statement

## Product Truth
FusionEMS Quantum is the centralized command and operating layer for EMS organizations.

It unifies:
- billing
- operations
- compliance
- fleet visibility
- reporting
- command oversight
- administrative control
- platform health

This build is a centralization and hardening release, not a feature expansion release.

## Non-Negotiable Standard
There is one platform, one production path, and one source of truth.

Do not ship with:
- duplicate routes
- duplicate pages
- duplicate auth logic
- duplicate API wrappers
- duplicate status surfaces
- duplicate environment loaders
- dead placeholders in active production paths
- hidden environment drift
- broken Microsoft authentication
- missing release or rollback visibility

## Canonical Stack
### Frontend
- Next.js App Router
- TypeScript
- Tailwind CSS
- shadcn/ui
- Motion
- React Hook Form
- Zod
- TanStack Table

### Deployment
- AWS Route 53
- AWS Amplify Hosting
- AWS Certificate Manager
- AWS WAF
- AWS CloudWatch
- AWS S3
- AWS Secrets Manager

## Visual System Directive
FusionEMS Quantum must present as critical infrastructure:
- black-dominant
- graphite layered
- high contrast
- restrained premium presentation
- signal-driven color semantics

Color semantics:
- orange: command and active focus
- red: incidents, blockers, degraded state
- green: healthy state, verified readiness

## Centralized Architecture Layers
### 1. Experience Layer
- dashboard
- billing
- operations
- compliance
- fleet
- reporting
- command center
- live status
- settings
- admin

### 2. Application Layer
- canonical routes
- shared forms/tables
- one permission model
- one API adapter layer
- one status rendering model
- one validation model

### 3. Domain Layer
One implementation per domain:
- billing
- operations
- compliance
- fleet
- reporting
- command center
- live status
- auth
- deployments
- settings

### 4. Service Layer
- typed backend services
- standardized integration wrappers
- health and release metadata services
- deterministic error handling

### 5. Operational Trust Layer
- live status
- release state
- auth validation
- environment validation
- incident visibility
- rollback readiness
- release block reasons

## Microsoft Entra Hard Block Policy
Every placeholder Microsoft tenant value is a release blocker.

The platform must validate and surface:
- tenant presence
- placeholder detection
- tenant identifier validity
- authority validity
- auth health by environment

Broken auth must be visible in command and live-status surfaces.
Broken auth must never be silent.

## Command Surfaces
### Command Center
Must show:
- platform readiness
- auth state
- deployment trust state
- active blockers
- degraded domains
- release trust indicators

### Live Status
Must show:
- frontend health
- backend health
- auth health
- Microsoft sign-in health
- database/queue/integration health
- deployment version
- last successful release
- rollback readiness
- incident state
- release block reasons

## Execution Lanes (Acceleration Model)
The sprint executes in parallel lanes, but ships one platform:
- architecture cleanup
- frontend execution
- backend/API hardening
- auth and identity repair
- infrastructure and AWS trust
- observability and live status
- QA and release gate
- product integration

No lane may introduce a second system.

## Go-Live Sequence
### Phase 1: Stop the bleeding
- freeze feature sprawl
- identify active production paths
- identify auth and release blockers

### Phase 2: Centralize foundation
- one route architecture
- one API layer
- one auth path
- one status layer
- one config model
- one design system base

### Phase 3: Repair trust blockers
- fix Microsoft tenant path
- enforce auth validation
- enforce environment validation
- expose release metadata and rollback signals

### Phase 4: Ship command surfaces
- command center operational trust blocks
- live-status NOC view
- degraded-state messaging

### Phase 5: Release hardening
- build and typecheck pass
- health endpoints pass
- auth path validated
- release version visible
- rollback readiness visible
- placeholder tenant values absent from active paths
- duplicate active production paths removed from release-critical scope

## Release Gate (Must Pass)
The release is blocked unless all are true:
- canonical auth surface valid
- Microsoft tenant and authority valid
- no placeholder auth values in active paths
- centralized live-status endpoint available
- centralized release-readiness endpoint available
- route/API duplication blockers resolved or explicitly waived by founder release authority
- rollback readiness signal present
- release metadata visible

## Final Standard
FusionEMS Quantum must feel like enterprise critical infrastructure for emergency services:
- exact
- fast
- stable
- governed
- observable
- production-ready

Ship one platform. Not many.

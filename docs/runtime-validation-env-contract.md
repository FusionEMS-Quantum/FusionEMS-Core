# Runtime Validation Environment Contract

This contract is required for real go-live runtime validation.

## Required by `scripts/release_runtime_validation.py`

### Required
- `LIVE_STATUS_URL`
  - Authenticated live-status endpoint URL (example: `https://api.fusionemsquantum.com/api/v1/platform/live-status`)
- `LIVE_STATUS_BEARER_TOKEN`
  - Bearer token for an authorized operator/founder account that can access live-status
- `TELNYX_API_KEY`
  - Production Telnyx API key with permission to query phone numbers

### Optional but strongly recommended for strict production matching
- `TELNYX_TARGET_NUMBER`
  - Defaults to `+1-888-365-0144`
- `TELNYX_EXPECTED_VOICE_CONNECTION_ID`
  - Expected production voice connection binding ID for the target number
- `TELNYX_EXPECTED_MESSAGING_PROFILE_ID`
  - Expected production messaging profile ID for the target number
- `TELNYX_EXPECTED_WEBHOOK_URL`
  - Webhook URL to probe for reachability check

## Required by `scripts/full_release_gate.sh`

`full_release_gate.sh` requires the same runtime variables above because it calls `scripts/release_runtime_validation.py` as the authoritative final stage.

It also expects ability to create/use `.venv` locally for backend checks.

## Failure Mapping (red checks)

Runtime validation failure output maps directly to release blockers:
- `HTTP ...` -> **auth/live-status auth failure**
- `backend=...` / `auth=...` / `microsoft_signin=...` -> **live-status service health failure**
- `configured_number=...` -> **Telnyx number mismatch**
- `voice binding verified` false -> **missing voice binding**
- `messaging profile verified` false -> **missing messaging profile**
- `webhook reachability verified` false -> **webhook reachability failure**
- `stale_binding_detected=True` -> **stale binding detected**
- `release.version=unknown` or missing -> **missing release/runtime config**

## Example export block

```bash
export LIVE_STATUS_URL="https://api.fusionemsquantum.com/api/v1/platform/live-status"
export LIVE_STATUS_BEARER_TOKEN="<operator_or_founder_jwt>"
export TELNYX_API_KEY="<telnyx_api_key>"
export TELNYX_TARGET_NUMBER="+1-888-365-0144"
export TELNYX_EXPECTED_VOICE_CONNECTION_ID="<voice_connection_id>"
export TELNYX_EXPECTED_MESSAGING_PROFILE_ID="<messaging_profile_id>"
export TELNYX_EXPECTED_WEBHOOK_URL="https://api.fusionemsquantum.com/api/v1/webhooks/telnyx/voice"
```

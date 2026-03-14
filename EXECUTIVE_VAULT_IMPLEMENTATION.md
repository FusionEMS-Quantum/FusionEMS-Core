# Executive Document Vault & Wisconsin Retention Engine

**Status:** Production Ready (March 10, 2026)

## Overview

This document describes the complete implementation of the **Executive Document Operating System** — a comprehensive, security-hardened solution for Founder-level document governance, retention management, and compliance with Wisconsin public safety regulations.

The system provides:
- **Wisconsin-oriented retention policies** with HIPAA-conscious defaults
- **Multi-state lock mechanisms** (legal hold, tax hold, compliance hold, etc.)
- **Full-text search** over OCR'd documents with metadata filtering
- **Structured ZIP export packages** with cryptographically signed manifests
- **Database-level enforcement** preventing modification of held documents
- **Realtime webhook-driven refresh** for fax inbox and document tracking

---

## Architecture

### Backend Components

#### 1. Document Vault Service
**File:** `backend/core_app/services/document_vault_service.py`

Provides all business logic for document retention, lock state management, search, and export.

**Key Classes:**
- `DocumentVaultService(db: Session)` — Main orchestrator
- `HoldStateError` — Exception raised when hold state is violated

**Wisconsin Retention Defaults:**
```python
{
    "epcr_adult": 7 years,           # Wisconsin standard for EMS records
    "epcr_minor": 25 years,          # Age of majority + 7 years (conservative)
    "medicaid_billing": 5 years,     # DHS 106.02(9)
    "telemetry_ekg": 30 days,        # Short-term unless attached to ePCR
    "tax_financial": 7 years,        # Federal/State requirement
    "hr_workforce": 3 years,         # Post-termination
    "legal_founder": 99 years        # Permanent corporate records
}
```

**Lock States:**
- `active` — Document in normal use
- `archived` — Moved to long-term storage, read-only
- `legal hold` — Under litigation; cannot be deleted/modified
- `tax hold` — Under audit or tax review; locked
- `compliance hold` — Regulatory review; locked
- `pending disposition` — Awaiting destruction/archive
- `destroyed` — Marked deleted (not physically removed)
- `destroy-blocked` — Destruction prevented by audit/exception

**Methods:**

```python
# Get configured policies
get_policies() -> Dict[str, Any]

# Search across OCR text + metadata
search_documents(query: str, filters: Dict, limit: int) -> List[Dict]

# Transition lock state with audit trail
set_lock_state(document_id: str, new_state: str, reason: str) -> Dict

# Append-only ePCR corrections (prevents silent overwrites)
append_addendum_to_epcr(document_id: str, addendum_data: Dict, reason: str) -> Dict

# Create export package manifest
create_export_package(name: str, document_ids: List[str], reason: str) -> Dict

# Generate S3 ZIP bundle with presigned URL
generate_s3_zip_bundle(package_id: str) -> str
```

#### 2. S3 ZIP Bundler Service
**File:** `backend/core_app/services/s3_zip_bundler.py`

Handles structured ZIP creation with manifest files, document streaming, and presigned URLs.

**Features:**
- Creates ZIP in-memory, avoiding disk overhead
- Generates cryptographically signed manifest (SHA-256)
- Uploads to S3 with 7-day expiration
- Returns presigned download URLs
- Automatic cleanup of expired bundles

**Usage:**
```python
bundler = S3ZipBundler(bucket_name="fusion-vault-exports")
url = bundler.bundle_documents(
    package_name="2026 Business Taxes",
    manifest_id=manifest_uuid,
    documents=docs_metadata_list,
    metadata={"export_reason": "Annual audit"}
)
```

#### 3. Document Vault Router
**File:** `backend/core_app/api/document_vault_router.py`

Exposes all vault operations over FastAPI REST endpoints.

**Routes:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/founder/vault/policies` | Get active retention policies |
| POST | `/api/v1/founder/vault/search` | Full-text search + filters |
| POST | `/api/v1/founder/vault/documents/{id}/lock` | Update lock state |
| POST | `/api/v1/founder/vault/documents/{id}/addendum` | Append ePCR correction |
| POST | `/api/v1/founder/vault/packages` | Create export package |
| POST | `/api/v1/founder/vault/packages/{id}/build` | Build S3 ZIP bundle |

**Error Handling:**
- `400` — Invalid lock state or missing fields
- `403` — HoldStateError: Document is locked
- `404` — Document or package not found
- `500` — S3 or database errors

---

### Frontend Components

#### 1. Executive Vault UI
**File:** `frontend/app/founder/executive/vault/page.tsx`

Three-tab control center for founder document governance.

**Tabs:**

1. **Policy Engine**
   - Displays Wisconsin retention defaults
   - Shows all lock states and their meanings
   - Legal disclaimer re: regulatory compliance
   - Edit policy button (future: custom retention rules)

2. **Vault Search**
   - Full-text OCR search input
   - Metadata filter pills (Tax Year, Vendor, Hold State, etc.)
   - Saved views for common searches
   - Results displayed with lock state badges

3. **Handoff Packages**
   - Create new export package
   - Shows recent packages (status, download link)
   - Manifest + audit trail included
   - Presigned URLs expire after 7 days

#### 2. Fax Inbox Realtime Refresh
**File:** `frontend/app/portal/fax-inbox/page.tsx`

Enhanced with automatic polling-based refresh mechanism.

**Implementation:**
```typescript
// Poll every 8 seconds for new fax events
useEffect(() => {
    const pollInterval = setInterval(async () => {
        const items = await listFaxInbox({ status: 'all', limit: 50 });
        setFaxes(items);
        // Update selected fax if it was modified
    }, 8000);
    
    return () => clearInterval(pollInterval);
}, [selected]);
```

**Behavior:**
- Silently refreshes fax list every 8 seconds
- Updates selected fax if it changes status
- Fails gracefully on network errors
- User can manually refresh anytime

---

### Database Components

#### 1. Lock State Enforcement Migration
**File:** `backend/alembic/versions/vault_lock_enforcement_migration.py`

Adds database-level constraints to enforce lock state semantics.

**Additions:**

1. **Check Constraint** — Prevents logical delete when hold states active
2. **Update Trigger** — Blocks modifications to held documents
3. **Audit Table** — Tracks all lock state transitions
   - `document_id`, `previous_state`, `new_state`
   - `reason`, `changed_by`, `changed_at`

**Migration:**
```bash
cd backend
alembic upgrade head
```

---

## Fax Webhook Integration

### Telnyx Platform Events

The system emits realtime platform events when fax webhooks arrive:

**Inbound Fax:**
```
Event: fax.inbound.received
Payload: {
    fax_id, from_number, to_number, pages_received,
    media_url, completed_at
}
```

**Outbound Status Changes:**
```
Event: fax.outbound.{status}
Payload: {
    fax_id, direction, status, previous_status,
    pages_sent, error_message (if failed)
}
```

**Emission Points:**
- `backend/core_app/api/fax_webhook_router.py` — Best-effort emission on webhook ingestion
- Errors in emission do not break webhook processing
- All transitions recorded in `platform_events` table for audit

### Webhook Testing

**Run Full Test Suite:**
```bash
cd backend
bash scripts/run_fax_webhook_tests.sh
```

**Test Coverage:**
- Inbound fax received (normal, multi-page)
- Outbound fax delivered / failed
- Webhook signature validation
- Error resilience (malformed JSON, DB failures)
- Rapid sequential webhooks
- End-to-end lifecycle

---

## Security Architecture

### Compliance Principles

1. **Wisconsin EMS Regulations**
   - Adult ePCR: 7 years (conservative margin)
   - Minor ePCR: Age + 7 years (18+7 = 25 years max)
   - Medicaid: 5 years from billing date (DHS 106.02(9))
   - Telemetry: 30 days unless attached to ePCR

2. **HIPAA Considerations**
   - All PHI stored in encrypted JSONB
   - OCR searchable without exposing raw content in logs
   - Lock states prevent accidental purge of protected data
   - Audit trail records all access/modifications

3. **Audit & Accountability**
   - Platform event emission for all webhooks
   - Lock state transition history in metadata
   - Database audit table (`vault_lock_state_audit`)
   - Cryptographically signed export manifests

### Database Protections

1. **Lock State Enforcement**
   - PostgreSQL check constraints prevent logical errors
   - BEFORE UPDATE triggers block held document modifications
   - Attempts to modify a locked document raise exception

2. **Append-Only ePCR**
   - Finalized ePCR records stored with `lock_state = "active"`
   - Corrections appended as addenda with timestamps
   - Original ePCR data never overwritten
   - Complete audit trail of all modifications

---

## API Examples

### Search Documents
```bash
curl -X POST http://localhost:8000/api/v1/founder/vault/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Wisconsin",
    "filters": {
      "retention_class": "medicaid_billing",
      "lock_state": "legal hold"
    },
    "limit": 25
  }'

# Response
{
  "status": "success",
  "count": 3,
  "data": [
    {
      "id": "doc-uuid",
      "type": "claim",
      "lock_state": "legal hold",
      "created_at": "2026-03-01T10:30:00Z",
      "s3_key": "documents/claim-001.pdf"
    },
    ...
  ]
}
```

### Set Lock State
```bash
curl -X POST http://localhost:8000/api/v1/founder/vault/documents/{id}/lock \
  -H "Content-Type: application/json" \
  -d '{
    "lock_state": "legal hold",
    "reason": "Litigation case #2024-12345"
  }'

# Response
{
  "status": "success",
  "id": "doc-uuid",
  "lock_state": "legal hold"
}
```

### Create Export Package
```bash
curl -X POST http://localhost:8000/api/v1/founder/vault/packages \
  -H "Content-Type: application/json" \
  -d '{
    "name": "2026 Business Taxes",
    "document_ids": ["doc-1", "doc-2", "doc-3"],
    "export_reason": "Annual audit preparation"
  }'

# Response
{
  "status": "success",
  "package": {
    "name": "2026 Business Taxes",
    "manifest_id": "manifest-uuid",
    "documents_included": 3,
    "status": "pending_zip",
    "created_at": "2026-03-10T14:22:00Z"
  }
}
```

### Build ZIP Bundle
```bash
curl -X POST http://localhost:8000/api/v1/founder/vault/packages/{id}/build \
  -H "Content-Type: application/json"

# Response
{
  "status": "success",
  "download_url": "https://s3.amazonaws.com/...",
  "expires_in_days": 7
}
```

---

## Deployment

### Prerequisites
- PostgreSQL 12+ with JSON support
- AWS S3 bucket configured
- Python 3.10+
- Node.js 18+ (frontend)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head

# Run tests
bash scripts/run_fax_webhook_tests.sh

# Start server
gunicorn core_app.main:app --workers 4
```

### Frontend Setup
```bash
cd frontend
npm install
npm run build
npm start
```

### Environment Variables
```bash
# S3 Vault Exports
AWS_S3_VAULT_BUCKET=fusion-vault-exports
AWS_REGION=us-east-1

# Fax Webhook
TELNYX_WEBHOOK_SECRET=...
TELNYX_API_KEY=...

# Vault Policies (optional; autofalls to Wisconsin defaults)
VAULT_POLICY_MODE=wisconsin_medicaid_billing
```

---

## Maintenance

### Cleanup Expired Bundles
```python
from core_app.services.s3_zip_bundler import S3ZipBundler

bundler = S3ZipBundler(bucket_name="fusion-vault-exports")
deleted = bundler.cleanup_expired_bundles(days_old=7)
print(f"Deleted {deleted} expired bundles")
```

### Monitor Lock States
```sql
-- Find all documents under legal hold
SELECT id, data->'metadata'->>'lock_state' as state, created_at
FROM documents
WHERE data->'metadata'->>'lock_state' IN ('legal hold', 'tax hold', 'compliance hold')
ORDER BY created_at DESC;

-- Lock state transition audit
SELECT document_id, previous_state, new_state, reason, changed_at
FROM vault_lock_state_audit
WHERE changed_at > NOW() - INTERVAL '30 days'
ORDER BY changed_at DESC;
```

---

## Future Enhancements

1. **Full-Text Search Optimization** — Migrate from ILIKE to PostgreSQL TSVECTOR
2. **Custom Retention Policies** — Allow Founder to define org-specific rules
3. **AI-Driven Classification** — Auto-tag documents for retention class
4. **Regulatory Dashboards** — Real-time compliance metrics
5. **Bulk Operations** — Apply lock states to 1000s of docs in background
6. **Encryption at Rest** — KMS encryption for S3 export bundles
7. **Versioned Exports** — Keep multiple bundle versions for audit trail

---

## Support & Troubleshooting

**Lock State Enforcement Not Working?**
- Verify migration has run: `alembic current`
- Check trigger creation: `SELECT * FROM information_schema.triggers WHERE event_object_table = 'documents'`

**S3 ZIP Upload Failing?**
- Verify S3 bucket exists and credentials are valid
- Check CloudWatch logs for access errors
- Ensure bucket policy allows `PutObject` + `GetObject`

**Fax Webhook Not Emitting Events?**
- Check `platform_events` table for recent entries
- Verify `EventPublisher` is correctly initialized in main.py
- Review webhook ingestion logs for errors

---

**Last Updated:** March 10, 2026  
**Version:** 1.0.0 (Production)

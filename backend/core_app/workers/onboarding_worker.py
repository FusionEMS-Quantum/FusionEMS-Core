"""
ZERO-ERROR ONBOARDING WORKER
============================
Processes checkout.session.completed events from SQS/Lambda.

State machine: CHECKOUT_CREATED → PAYMENT_CONFIRMED → WEBHOOK_VERIFIED →
               AGENCY_RECORD_CREATED → ADMIN_RECORD_CREATED →
               SUBSCRIPTION_LINKED → ENTITLEMENTS_ASSIGNED →
               DEPLOYMENT_READY → LIVE

Rules:
- Idempotent: safe to run multiple times for the same checkout session.
- Every step is recorded as a DeploymentStep for full audit trail.
- Failures set DeploymentState.DEPLOYMENT_FAILED with failure_reason.
- Retries increment retry_count; hard limit = MAX_RETRIES (5).
- provision_tenant_from_application() is the single provisioning source of truth.
- Never silently fails: every exception is logged with correlation_id.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


# ── DB session (sync, for Lambda context) ────────────────────────────────────

def _get_db_session():
    """Returns a synchronous SQLAlchemy session for Lambda worker context."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    engine = create_engine(db_url, pool_pre_ping=True, pool_size=2, max_overflow=0)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return Session()


# ── Main entry point ──────────────────────────────────────────────────────────

def process_onboarding_event(message_body: dict[str, Any]) -> None:
    """
    Process a single onboarding SQS message.

    Expected message_body shape:
    {
        "source": "stripe_webhook",
        "event_id": "<stripe_event_id>",
        "event_type": "checkout.session.completed",
        "payload": { ... full Stripe event ... },
        "correlation_id": "<uuid>",
        "received_at": "<iso8601>",
    }
    """
    event_id: str = message_body.get("event_id", "")
    event_type: str = message_body.get("event_type", "")
    payload: dict[str, Any] = message_body.get("payload", {})
    correlation_id: str = message_body.get("correlation_id", event_id)

    logger.info(
        "onboarding_worker_processing event_id=%s event_type=%s correlation_id=%s",
        event_id, event_type, correlation_id,
    )

    if event_type != "checkout.session.completed":
        logger.info(
            "onboarding_worker_skip_non_checkout event_type=%s event_id=%s",
            event_type, event_id,
        )
        return

    db = _get_db_session()
    try:
        _run_deployment(db, event_id, payload, correlation_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception(
            "onboarding_worker_fatal_error event_id=%s correlation_id=%s error=%s",
            event_id, correlation_id, exc,
        )
        raise
    finally:
        db.close()


# ── Deployment state machine ──────────────────────────────────────────────────

def _run_deployment(
    db: Any,
    stripe_event_id: str,
    payload: dict[str, Any],
    correlation_id: str,
) -> None:
    """
    Runs the full zero-error deployment state machine for a checkout.session.completed event.
    Idempotent: safe to re-run for the same stripe_event_id.
    """
    from sqlalchemy import text as sa_text

    checkout_obj = payload.get("data", {}).get("object", {})
    application_id = (
        checkout_obj.get("metadata", {}).get("application_id")
        or checkout_obj.get("client_reference_id")
    )
    stripe_customer_id = checkout_obj.get("customer")
    stripe_subscription_id = checkout_obj.get("subscription")
    payment_status = checkout_obj.get("payment_status", "unpaid")

    logger.info(
        "onboarding_worker_deployment_start application_id=%s stripe_event_id=%s "
        "payment_status=%s customer=%s subscription=%s correlation_id=%s",
        application_id, stripe_event_id, payment_status,
        stripe_customer_id, stripe_subscription_id, correlation_id,
    )

    # ── Step 1: Idempotency — find or create DeploymentRun ────────────────────
    run = _get_or_create_run(db, stripe_event_id, {
        "application_id": application_id,
        "stripe_customer_id": stripe_customer_id,
        "stripe_subscription_id": stripe_subscription_id,
        "correlation_id": correlation_id,
    })

    if run["current_state"] == "LIVE":
        logger.info(
            "onboarding_worker_already_live run_id=%s stripe_event_id=%s",
            run["id"], stripe_event_id,
        )
        return

    if run["current_state"] == "DEPLOYMENT_FAILED":
        if run["retry_count"] >= MAX_RETRIES:
            logger.error(
                "onboarding_worker_max_retries_exceeded run_id=%s retries=%s",
                run["id"], run["retry_count"],
            )
            return
        # Reset for retry
        _step(db, run["id"], "RETRY_ATTEMPT", "INFO",
              {"retry_count": run["retry_count"] + 1})
        _set_state(db, run["id"], "RETRY_PENDING")
        _increment_retry(db, run["id"])

    run_id = run["id"]

    # ── Step 2: Verify payment confirmed ─────────────────────────────────────
    if payment_status not in ("paid", "no_payment_required"):
        _fail(db, run_id, "PAYMENT_NOT_CONFIRMED",
              f"payment_status={payment_status!r} — cannot provision without confirmed payment")
        return
    _step(db, run_id, "PAYMENT_CONFIRMED", "SUCCESS",
          {"payment_status": payment_status, "stripe_event_id": stripe_event_id})
    _set_state(db, run_id, "PAYMENT_CONFIRMED")

    # ── Step 3: Validate webhook data ─────────────────────────────────────────
    if not application_id:
        _fail(db, run_id, "WEBHOOK_VALIDATION_FAILED",
              "checkout.session.completed has no application_id in metadata — "
              "cannot identify onboarding application")
        return
    _step(db, run_id, "WEBHOOK_VERIFIED", "SUCCESS",
          {"application_id": application_id})
    _set_state(db, run_id, "WEBHOOK_VERIFIED")

    # ── Step 4: Load onboarding application ───────────────────────────────────
    app_row = db.execute(
        sa_text(
            "SELECT id, agency_name, contact_email, agency_type, "
            "annual_call_volume, selected_modules, status, tenant_id, legal_status "
            "FROM onboarding_applications WHERE id = :app_id"
        ),
        {"app_id": application_id},
    ).mappings().first()

    if not app_row:
        _fail(db, run_id, "APPLICATION_NOT_FOUND",
              f"Onboarding application {application_id!r} not found in database. "
              "Cannot provision without an application record.")
        return

    app_dict = dict(app_row)
    _step(db, run_id, "APPLICATION_LOADED", "SUCCESS", {
        "agency_name": app_dict.get("agency_name"),
        "agency_type": app_dict.get("agency_type"),
        "status": app_dict.get("status"),
    })

    # Compliance gate: do not provision without signed legal documents.
    if str(app_dict.get("legal_status") or "").lower() != "signed":
        _fail(
            db,
            run_id,
            "LEGAL_NOT_SIGNED",
            f"legal_status={app_dict.get('legal_status')!r} — cannot provision without executed legal packet",
        )
        try:
            db.execute(
                sa_text(
                    "UPDATE onboarding_applications "
                    "SET provisioning_status = 'failed', provisioning_error = :err "
                    "WHERE id = :app_id AND provisioned_at IS NULL"
                ),
                {"app_id": application_id, "err": "legal_not_signed"},
            )
        except Exception as exc:
            logger.warning(
                "onboarding_worker_legal_gate_update_failed application_id=%s error=%s",
                application_id,
                exc,
            )
        return

    # ── Step 5: Check if already provisioned ─────────────────────────────────
    if app_dict.get("status") in ("provisioned", "active") and app_dict.get("tenant_id"):
        tenant_id = str(app_dict["tenant_id"])
        _step(db, run_id, "ALREADY_PROVISIONED", "INFO",
              {"tenant_id": tenant_id})
        _set_state(db, run_id, "LIVE")
        # Link the tenant_id to the run if not already linked
        _link_agency(db, run_id, tenant_id)
        logger.info(
            "onboarding_worker_already_provisioned application_id=%s tenant_id=%s",
            application_id, tenant_id,
        )
        return

    # ── Step 6: Create agency / tenant record ─────────────────────────────────
    import asyncio

    from core_app.services.tenant_provisioning import provision_tenant_from_application

    _set_state(db, run_id, "AGENCY_RECORD_CREATED")
    _step(db, run_id, "PROVISIONING_STARTED", "PENDING",
          {"agency_name": app_dict.get("agency_name")})

    try:
        # provision_tenant_from_application is async; run it in a new event loop
        result = asyncio.run(
            provision_tenant_from_application(
                db=db,
                application_id=application_id,
                application_row=app_dict,
                stripe_event=payload,
            )
        )
    except Exception as exc:
        _fail(db, run_id, "PROVISIONING_FAILED", str(exc))
        raise

    tenant_id = result.get("tenant_id") or result.get("id", "")
    admin_user_id = result.get("admin_user_id", "")

    _step(db, run_id, "AGENCY_PROVISIONED", "SUCCESS", {
        "tenant_id": tenant_id,
        "admin_user_id": admin_user_id,
        "modules": result.get("modules_enabled", []),
    })
    _set_state(db, run_id, "ADMIN_RECORD_CREATED")
    _link_agency(db, run_id, tenant_id)

    # ── Step 7: Link Stripe subscription ─────────────────────────────────────
    if stripe_subscription_id:
        try:
            db.execute(
                sa_text(
                    "UPDATE tenants SET stripe_subscription_id = :sub_id "
                    "WHERE id = :tenant_id"
                ),
                {"sub_id": stripe_subscription_id, "tenant_id": tenant_id},
            )
            db.execute(
                sa_text(
                    "UPDATE tenants SET stripe_customer_id = :cust_id "
                    "WHERE id = :tenant_id AND stripe_customer_id IS NULL"
                ),
                {"cust_id": stripe_customer_id, "tenant_id": tenant_id},
            )
            _step(db, run_id, "SUBSCRIPTION_LINKED", "SUCCESS", {
                "stripe_subscription_id": stripe_subscription_id,
                "stripe_customer_id": stripe_customer_id,
            })
            _set_state(db, run_id, "SUBSCRIPTION_LINKED")
        except Exception as exc:
            logger.warning(
                "onboarding_worker_subscription_link_failed tenant_id=%s error=%s",
                tenant_id, exc,
            )
            _step(db, run_id, "SUBSCRIPTION_LINK_WARNING", "WARNING",
                  {"error": str(exc)})
            # Non-fatal: provisioning succeeded, subscription link can be retried

    # ── Step 8: Mark application as provisioned ───────────────────────────────
    try:
        db.execute(
            sa_text(
                "UPDATE onboarding_applications "
                "SET status = 'provisioned', tenant_id = :tenant_id, "
                "provisioned_at = :now, provisioning_status = 'complete', "
                "provisioning_steps = COALESCE(provisioning_steps, '[]'::jsonb) || :step::jsonb "
                "WHERE id = :app_id AND status NOT IN ('provisioned', 'active')"
            ),
            {
                "tenant_id": tenant_id,
                "now": datetime.now(UTC),
                "app_id": application_id,
                "step": json.dumps(
                    [
                        {
                            "step": "application_marked_provisioned",
                            "status": "success",
                            "stripe_event_id": stripe_event_id,
                            "at": datetime.now(UTC).isoformat(),
                        }
                    ]
                ),
            },
        )
        _step(db, run_id, "APPLICATION_MARKED_PROVISIONED", "SUCCESS",
              {"application_id": application_id, "tenant_id": tenant_id})
        _set_state(db, run_id, "ENTITLEMENTS_ASSIGNED")
    except Exception as exc:
        logger.warning(
            "onboarding_worker_application_update_failed application_id=%s error=%s",
            application_id, exc,
        )
        _step(db, run_id, "APPLICATION_UPDATE_WARNING", "WARNING",
              {"error": str(exc)})

    # ── Step 9: Mark deployment live ─────────────────────────────────────────
    _set_state(db, run_id, "DEPLOYMENT_READY")
    _step(db, run_id, "DEPLOYMENT_COMPLETE", "SUCCESS", {
        "tenant_id": tenant_id,
        "application_id": application_id,
        "stripe_event_id": stripe_event_id,
        "completed_at": datetime.now(UTC).isoformat(),
    })
    _set_state(db, run_id, "LIVE")

    logger.info(
        "onboarding_worker_success application_id=%s tenant_id=%s "
        "stripe_event_id=%s correlation_id=%s",
        application_id, tenant_id, stripe_event_id, correlation_id,
    )


# ── DB helpers (raw SQL for Lambda-safe synchronous execution) ────────────────

def _get_or_create_run(db: Any, stripe_event_id: str, meta: dict) -> dict:
    import uuid as _uuid

    from sqlalchemy import text as sa_text

    existing = db.execute(
        sa_text(
            "SELECT id, current_state, retry_count FROM deployment_runs "
            "WHERE external_event_id = :eid"
        ),
        {"eid": stripe_event_id},
    ).mappings().first()

    if existing:
        return dict(existing)

    run_id = str(_uuid.uuid4())
    db.execute(
        sa_text(
            "INSERT INTO deployment_runs "
            "(id, external_event_id, current_state, retry_count, metadata_blob, "
            " created_at, updated_at) "
            "VALUES (:id, :eid, 'CHECKOUT_CREATED', 0, :meta, :now, :now)"
        ),
        {
            "id": run_id,
            "eid": stripe_event_id,
            "meta": json.dumps(meta),
            "now": datetime.now(UTC),
        },
    )
    _step(db, run_id, "DEPLOYMENT_RUN_CREATED", "SUCCESS", meta)
    return {"id": run_id, "current_state": "CHECKOUT_CREATED", "retry_count": 0}


def _step(db: Any, run_id: str, step_name: str, status: str, result: dict) -> None:
    import uuid as _uuid

    from sqlalchemy import text as sa_text

    db.execute(
        sa_text(
            "INSERT INTO deployment_steps "
            "(id, run_id, step_name, status, result_blob, created_at, updated_at) "
            "VALUES (:id, :run_id, :name, :status, :result, :now, :now)"
        ),
        {
            "id": str(_uuid.uuid4()),
            "run_id": run_id,
            "name": step_name,
            "status": status,
            "result": json.dumps(result, default=str),
            "now": datetime.now(UTC),
        },
    )


def _set_state(db: Any, run_id: str, state: str) -> None:
    from sqlalchemy import text as sa_text

    db.execute(
        sa_text(
            "UPDATE deployment_runs SET current_state = :state, updated_at = :now "
            "WHERE id = :run_id"
        ),
        {"state": state, "run_id": run_id, "now": datetime.now(UTC)},
    )


def _fail(db: Any, run_id: str, reason_key: str, reason_detail: str) -> None:
    from sqlalchemy import text as sa_text

    logger.error(
        "onboarding_worker_deployment_failed run_id=%s reason=%s detail=%s",
        run_id, reason_key, reason_detail,
    )
    _step(db, run_id, f"FAILED_{reason_key}", "FAILED",
          {"reason": reason_key, "detail": reason_detail})
    db.execute(
        sa_text(
            "UPDATE deployment_runs "
            "SET current_state = 'DEPLOYMENT_FAILED', "
            "failure_reason = :reason, updated_at = :now "
            "WHERE id = :run_id"
        ),
        {
            "reason": f"{reason_key}: {reason_detail[:500]}",
            "run_id": run_id,
            "now": datetime.now(UTC),
        },
    )


def _link_agency(db: Any, run_id: str, tenant_id: str) -> None:
    from sqlalchemy import text as sa_text

    db.execute(
        sa_text(
            "UPDATE deployment_runs SET agency_id = :tid, updated_at = :now "
            "WHERE id = :run_id AND agency_id IS NULL"
        ),
        {"tid": tenant_id, "run_id": run_id, "now": datetime.now(UTC)},
    )


def _increment_retry(db: Any, run_id: str) -> None:
    from sqlalchemy import text as sa_text

    db.execute(
        sa_text(
            "UPDATE deployment_runs "
            "SET retry_count = retry_count + 1, updated_at = :now "
            "WHERE id = :run_id"
        ),
        {"run_id": run_id, "now": datetime.now(UTC)},
    )


# ── Lambda handler ─────────────────────────────────────────────────────────────

def lambda_handler(event: dict[str, Any], context: Any) -> None:
    """
    AWS Lambda handler — invoked by SQS trigger on the onboarding events queue.
    Each record is one Stripe event from the webhook → SQS pipeline.
    """
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            process_onboarding_event(body)
        except Exception as exc:
            logger.exception(
                "onboarding_worker_record_failed message_id=%s error=%s",
                record.get("messageId", ""),
                exc,
            )
            # Re-raise to let SQS retry (with backoff/dead-letter)
            raise

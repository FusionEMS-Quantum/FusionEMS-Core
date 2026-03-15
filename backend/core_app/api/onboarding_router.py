from __future__ import annotations

# ruff: noqa: I001

# pylint: disable=raise-missing-from,broad-exception-caught

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.onboarding.legal_service import LegalService
from core_app.pricing.catalog import (
    PLANS,
    calculate_quote,
    lookup_key_to_cents,
    resolve_selected_modules,
)
from core_app.roi.engine import compute_roi, hash_outputs
from core_app.services.event_publisher import get_event_publisher

try:
    import stripe as stripe_lib

    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/onboarding", tags=["Onboarding"])

ALLOWED_OPERATIONAL_MODES = {
    "HEMS_TRANSPORT",
    "EMS_TRANSPORT",
    "MEDICAL_TRANSPORT",
    "EXTERNAL_911_CAD",
}
ALLOWED_BILLING_MODES = {"FUSION_RCM", "THIRD_PARTY_EXPORT"}


def _legal_svc(db: Session) -> LegalService:
    return LegalService(db, get_event_publisher())


def _normalize_operational_mode(value: str) -> str:
    val = (value or "").strip().upper()
    if val in ALLOWED_OPERATIONAL_MODES:
        return val
    return "EMS_TRANSPORT"


def _normalize_billing_mode(value: str) -> str:
    val = (value or "").strip().upper()
    if val in ALLOWED_BILLING_MODES:
        return val
    return "FUSION_RCM"


@router.get("/nppes/lookup/{npi_number}")
async def nppes_lookup(npi_number: str):
    npi = "".join(ch for ch in npi_number if ch.isdigit())
    if len(npi) < 10:
        raise HTTPException(status_code=422, detail="npi_number must be 10 digits")

    query = urlencode({"number": npi, "version": "2.1", "limit": 1})
    url = f"https://npiregistry.cms.hhs.gov/api/?{query}"
    try:
        with urlopen(url, timeout=8) as resp:  # nosec B310
            payload = json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("NPPES lookup failed for NPI %s: %s", npi, exc)
        raise HTTPException(status_code=502, detail="nppes_lookup_failed") from exc

    results = payload.get("results") or []
    if not results:
        raise HTTPException(status_code=404, detail="npi_not_found")

    item = results[0]
    basic = item.get("basic", {}) or {}
    addresses = item.get("addresses", []) or []
    taxonomies = item.get("taxonomies", []) or []
    business_addr = next((a for a in addresses if a.get("address_purpose") == "LOCATION"), addresses[0] if addresses else {})
    primary_taxonomy = next((t for t in taxonomies if t.get("primary") is True), taxonomies[0] if taxonomies else {})

    org_name = (
        basic.get("organization_name")
        or basic.get("name")
        or ""
    )

    return {
        "npi_number": npi,
        "legal_organization_name": org_name,
        "address_line_1": business_addr.get("address_1"),
        "city": business_addr.get("city"),
        "state": business_addr.get("state"),
        "postal_code": business_addr.get("postal_code"),
        "taxonomy_code": primary_taxonomy.get("code"),
        "taxonomy_desc": primary_taxonomy.get("desc"),
    }


def _get_stripe_price_ids(
    stage: str, aws_region: str, lookup_keys: list[str]
) -> dict[str, str]:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        logger.warning("SSM price ID lookup unavailable: %s", exc)
        return {}

    try:
        ssm = boto3.client("ssm", region_name=aws_region or "us-east-1")
        prefix = f"/fusionems/{stage}/stripe/prices"
        names = [f"{prefix}/{lk}" for lk in lookup_keys]
        resp = ssm.get_parameters(Names=names, WithDecryption=False)
        return {
            p["Name"].split("/")[-1]: p["Value"] for p in resp.get("Parameters", [])
        }
    except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "SSM price ID lookup failed: %s — will use price_data fallback", exc
        )
        return {}


@router.post("/start")
async def onboarding_start(
    payload: dict[str, Any], db: Session = Depends(db_session_dependency)
):
    email = str(payload.get("email", "")).lower().strip()
    agency_name = str(payload.get("agency_name", "")).strip()
    agency_type = str(payload.get("agency_type", "EMS"))
    zip_code = str(payload.get("zip_code", ""))
    annual_call_volume = int(payload.get("annual_call_volume", 0))
    current_billing_percent = float(payload.get("current_billing_percent", 0.0))
    payer_mix = payload.get("payer_mix", {})
    level_mix = payload.get("level_mix", {})
    selected_modules = payload.get("selected_modules", [])
    npi_number = str(payload.get("npi_number", "")).strip() or None
    operational_mode = _normalize_operational_mode(str(payload.get("operational_mode", "EMS_TRANSPORT")))
    billing_mode = _normalize_billing_mode(str(payload.get("billing_mode", "FUSION_RCM")))
    primary_tail_number = str(payload.get("primary_tail_number", "")).strip() or None
    base_icao = str(payload.get("base_icao", "")).strip().upper() or None
    billing_contact_name = str(payload.get("billing_contact_name", "")).strip() or None
    billing_contact_email = str(payload.get("billing_contact_email", "")).strip().lower() or None
    implementation_owner_name = str(payload.get("implementation_owner_name", "")).strip() or None
    implementation_owner_email = str(payload.get("implementation_owner_email", "")).strip().lower() or None
    identity_sso_preference = str(payload.get("identity_sso_preference", "")).strip() or None
    policy_flags = payload.get("policy_flags", {}) or {}

    if not email or not agency_name:
        raise HTTPException(
            status_code=422, detail="email and agency_name are required"
        )
    if agency_type not in ("EMS", "Fire", "HEMS"):
        raise HTTPException(
            status_code=422, detail="agency_type must be EMS, Fire, or HEMS"
        )

    roi = compute_roi(
        {
            "zip_code": zip_code,
            "annual_call_volume": annual_call_volume,
            "service_type": agency_type,
            "current_billing_percent": current_billing_percent,
            "payer_mix": payer_mix,
            "level_mix": level_mix,
            "selected_modules": selected_modules,
        }
    )
    roi_hash = hash_outputs(roi)

    cutoff = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    existing = (
        db.execute(
            text(
                "SELECT id, roi_snapshot_hash, status FROM onboarding_applications "
                "WHERE contact_email = :email AND agency_name = :agency AND status = 'started' "
                "AND created_at >= :cutoff LIMIT 1"
            ),
            {"email": email, "agency": agency_name, "cutoff": cutoff},
        )
        .mappings()
        .first()
    )

    if existing:
        return {
            "application_id": str(existing["id"]),
            "roi_snapshot_hash": existing["roi_snapshot_hash"],
            "status": existing["status"],
            "next_steps": ["sign_legal", "checkout", "provisioning"],
        }

    row = (
        db.execute(
            text(
                """
            INSERT INTO onboarding_applications (
                contact_email, agency_name, zip_code, agency_type, annual_call_volume,
                current_billing_percent, payer_mix, level_mix, selected_modules,
                roi_snapshot_hash, status, legal_status,
                npi_number, operational_mode, billing_mode,
                primary_tail_number, base_icao,
                billing_contact_name, billing_contact_email,
                implementation_owner_name, implementation_owner_email,
                identity_sso_preference, policy_flags,
                provisioning_status, provisioning_steps
            ) VALUES (
                :email, :agency, :zip, :atype, :vol, :pct,
                :payer::jsonb, :level::jsonb, :mods::jsonb,
                :h, 'started', 'pending',
                :npi, :operational_mode, :billing_mode,
                :tail, :base_icao,
                :billing_contact_name, :billing_contact_email,
                :implementation_owner_name, :implementation_owner_email,
                :identity_sso_preference, :policy_flags::jsonb,
                'pending', '[]'::jsonb
            ) RETURNING id
            """
            ),
            {
                "email": email,
                "agency": agency_name,
                "zip": zip_code,
                "atype": agency_type,
                "vol": annual_call_volume,
                "pct": current_billing_percent,
                "payer": json.dumps(payer_mix),
                "level": json.dumps(level_mix),
                "mods": json.dumps(selected_modules),
                "h": roi_hash,
                "npi": npi_number,
                "operational_mode": operational_mode,
                "billing_mode": billing_mode,
                "tail": primary_tail_number,
                "base_icao": base_icao,
                "billing_contact_name": billing_contact_name,
                "billing_contact_email": billing_contact_email,
                "implementation_owner_name": implementation_owner_name,
                "implementation_owner_email": implementation_owner_email,
                "identity_sso_preference": identity_sso_preference,
                "policy_flags": json.dumps(policy_flags),
            },
        )
        .mappings()
        .first()
    )
    db.commit()

    return {
        "application_id": str(row["id"]),
        "roi_snapshot_hash": roi_hash,
        "status": "started",
        "next_steps": ["sign_legal", "checkout", "provisioning"],
    }


@router.post("/apply")
async def onboarding_apply(
    payload: dict[str, Any], db: Session = Depends(db_session_dependency)
):
    email = str(payload.get("email", "")).lower().strip()
    agency_name = str(payload.get("agency_name", "")).strip()
    agency_type = str(payload.get("agency_type", "EMS")).strip()
    str(payload.get("state", "")).strip()
    zip_code = str(payload.get("zip_code", "")).strip()
    first_name = str(payload.get("first_name", "")).strip()
    last_name = str(payload.get("last_name", "")).strip()
    phone = str(payload.get("phone", "")).strip()
    plan_code = str(payload.get("plan_code", "")).strip()
    tier_code = str(payload.get("tier_code", "") or "").strip() or None
    billing_tier_code = str(payload.get("billing_tier_code", "") or "").strip() or None
    addon_codes = list(payload.get("addon_codes", payload.get("modules", [])))
    is_government_entity = bool(payload.get("is_government_entity", False))
    collections_mode = str(payload.get("collections_mode", "none"))
    statement_channels = payload.get("statement_channels", ["mail"])
    collector_vendor_name = str(payload.get("collector_vendor_name", "") or "")
    placement_method = str(payload.get("placement_method", "portal_upload"))
    npi_number = str(payload.get("npi_number", "")).strip() or None
    operational_mode = _normalize_operational_mode(str(payload.get("operational_mode", "EMS_TRANSPORT")))
    billing_mode = _normalize_billing_mode(str(payload.get("billing_mode", "FUSION_RCM")))
    primary_tail_number = str(payload.get("primary_tail_number", "")).strip() or None
    base_icao = str(payload.get("base_icao", "")).strip().upper() or None
    billing_contact_name = str(payload.get("billing_contact_name", "")).strip() or None
    billing_contact_email = str(payload.get("billing_contact_email", "")).strip().lower() or None
    implementation_owner_name = str(payload.get("implementation_owner_name", "")).strip() or None
    implementation_owner_email = str(payload.get("implementation_owner_email", "")).strip().lower() or None
    identity_sso_preference = str(payload.get("identity_sso_preference", "")).strip() or None
    policy_flags = payload.get("policy_flags", {}) or {}

    if not email or not agency_name:
        raise HTTPException(
            status_code=422, detail="email and agency_name are required"
        )

    try:
        quote = calculate_quote(
            plan_code=plan_code,
            tier_code=tier_code,
            billing_tier_code=billing_tier_code,
            addon_codes=addon_codes,
            billing_mode=billing_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        selected_modules = resolve_selected_modules(
            plan_code=plan_code,
            addon_codes=addon_codes,
            billing_mode=billing_mode,
            billing_tier_code=billing_tier_code,
            operational_mode=operational_mode,
            agency_type=agency_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    row = (
        db.execute(
            text(
                """
            INSERT INTO onboarding_applications (
                contact_email, agency_name, agency_type, zip_code,
                plan_code, tier_code, billing_tier_code, addon_codes,
                selected_modules, status, legal_status,
                first_name, last_name, phone,
                is_government_entity, collections_mode, statement_channels,
                collector_vendor_name, placement_method,
                npi_number, operational_mode, billing_mode,
                primary_tail_number, base_icao,
                billing_contact_name, billing_contact_email,
                implementation_owner_name, implementation_owner_email,
                identity_sso_preference, policy_flags,
                provisioning_status, provisioning_steps
            ) VALUES (
                :email, :agency, :atype, :zip,
                :plan_code, :tier_code, :billing_tier_code, :addon_codes::jsonb,
                :mods::jsonb, 'started', 'pending',
                :first_name, :last_name, :phone,
                :is_gov, :collections_mode, :statement_channels::jsonb,
                :collector_vendor_name, :placement_method,
                :npi, :operational_mode, :billing_mode,
                :tail, :base_icao,
                :billing_contact_name, :billing_contact_email,
                :implementation_owner_name, :implementation_owner_email,
                :identity_sso_preference, :policy_flags::jsonb,
                'pending', '[]'::jsonb
            ) RETURNING id
            """
            ),
            {
                "email": email,
                "agency": agency_name,
                "atype": agency_type,
                "zip": zip_code,
                "plan_code": plan_code,
                "tier_code": tier_code,
                "billing_tier_code": billing_tier_code,
                "addon_codes": json.dumps(addon_codes),
                "mods": json.dumps(selected_modules),
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "is_gov": is_government_entity,
                "collections_mode": collections_mode,
                "statement_channels": json.dumps(statement_channels),
                "collector_vendor_name": collector_vendor_name,
                "placement_method": placement_method,
                "npi": npi_number,
                "operational_mode": operational_mode,
                "billing_mode": billing_mode,
                "tail": primary_tail_number,
                "base_icao": base_icao,
                "billing_contact_name": billing_contact_name,
                "billing_contact_email": billing_contact_email,
                "implementation_owner_name": implementation_owner_name,
                "implementation_owner_email": implementation_owner_email,
                "identity_sso_preference": identity_sso_preference,
                "policy_flags": json.dumps(policy_flags),
            },
        )
        .mappings()
        .first()
    )
    db.commit()

    return {
        "application_id": str(row["id"]),
        "status": "started",
        "requires_quote": quote.requires_quote,
        "next_steps": ["sign_legal", "checkout", "provisioning"],
    }


@router.post("/legal/packet/create")
async def legal_packet_create(
    payload: dict[str, Any], db: Session = Depends(db_session_dependency)
):
    application_id = str(payload.get("application_id", "")).strip()
    signer_name = str(payload.get("signer_name", "")).strip()
    signer_email = str(payload.get("signer_email", "")).strip()
    str(payload.get("signer_title", "")).strip()

    if not application_id:
        raise HTTPException(status_code=422, detail="application_id is required")

    app_row = (
        db.execute(
            text(
                "SELECT id, agency_name, agency_type, annual_call_volume, selected_modules, "
                "current_billing_percent, status, legal_status FROM onboarding_applications WHERE id = :app_id"
            ),
            {"app_id": application_id},
        )
        .mappings()
        .first()
    )

    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if app_row["status"] not in ("started", "legal_pending"):
        raise HTTPException(
            status_code=422,
            detail=f"Application status '{app_row['status']}' does not allow legal packet creation",
        )

    svc = _legal_svc(db)
    existing_status = svc.get_legal_status(application_id)
    if existing_status["packet_id"]:
        packet = svc.get_packet(existing_status["packet_id"], application_id)
        if packet:
            return packet

    plan_data = {
        "agency_name": app_row["agency_name"],
        "agency_type": app_row["agency_type"],
        "annual_call_volume": app_row["annual_call_volume"],
        "selected_modules": (
            app_row["selected_modules"] if app_row["selected_modules"] else []
        ),
        "current_billing_percent": app_row["current_billing_percent"],
    }

    packet = svc.create_packet(
        application_id=application_id,
        signer_email=signer_email,
        signer_name=signer_name,
        agency_name=app_row["agency_name"],
        plan_data=plan_data,
    )

    db.execute(
        text(
            "UPDATE onboarding_applications SET status = 'legal_pending' WHERE id = :app_id"
        ),
        {"app_id": application_id},
    )
    db.commit()

    return packet


@router.get("/legal/packet/{packet_id}")
async def legal_packet_get(
    packet_id: str,
    application_id: str,
    db: Session = Depends(db_session_dependency),
):
    svc = _legal_svc(db)
    packet = svc.get_packet(packet_id, application_id)
    if packet is None:
        raise HTTPException(status_code=404, detail="Packet not found")
    return packet


@router.post("/legal/packet/{packet_id}/sign")
async def legal_packet_sign(
    packet_id: str,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(db_session_dependency),
):
    application_id = str(payload.get("application_id", "")).strip()
    if not application_id:
        raise HTTPException(status_code=422, detail="application_id is required")

    svc = _legal_svc(db)
    packet = svc.get_packet(packet_id, application_id)
    if packet is None:
        raise HTTPException(
            status_code=404, detail="Packet not found or application_id mismatch"
        )

    # IP and User-Agent are extracted server-side to prevent client-supplied forgery
    # in the legal audit trail. Payload-supplied values are intentionally ignored.
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    server_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
        request.client.host if request.client else ""
    )
    server_user_agent = request.headers.get("User-Agent", "")

    signing_data = {
        "signer_name": payload.get("signer_name", ""),
        "signer_email": payload.get("signer_email", ""),
        "signer_title": payload.get("signer_title", ""),
        "ip_address": server_ip,
        "user_agent": server_user_agent,
        "consents": payload.get("consents", {}),
        "signature_text": payload.get("signature_text", ""),
    }

    try:
        updated = svc.sign_packet(packet_id, signing_data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.execute(
        text(
            "UPDATE onboarding_applications SET legal_status = 'signed' WHERE id = :app_id"
        ),
        {"app_id": application_id},
    )
    db.commit()

    documents_summary = [
        {
            "doc_type": d.get("data", {}).get("doc_type"),
            "s3_key_executed": d.get("data", {}).get("s3_key_executed"),
            "sha256": d.get("data", {}).get("sha256"),
        }
        for d in updated.get("documents", [])
    ]

    return {"signed": True, "packet_id": packet_id, "documents": documents_summary}


@router.post("/checkout/start")
async def checkout_start(
    payload: dict[str, Any], db: Session = Depends(db_session_dependency)
):
    application_id = str(payload.get("application_id", "")).strip()
    if not application_id:
        raise HTTPException(status_code=422, detail="application_id is required")

    app_row = (
        db.execute(
            text(
                "SELECT id, agency_name, annual_call_volume, selected_modules, "
                "plan_code, tier_code, billing_tier_code, addon_codes, "
                "billing_mode, legal_status, status "
                "FROM onboarding_applications WHERE id = :app_id"
            ),
            {"app_id": application_id},
        )
        .mappings()
        .first()
    )

    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if app_row["legal_status"] != "signed":
        raise HTTPException(
            status_code=422, detail="Legal documents must be signed before payment"
        )

    settings = get_settings()

    if not STRIPE_AVAILABLE or not settings.stripe_secret_key:
        db.execute(
            text(
                "UPDATE onboarding_applications SET status = 'payment_pending' WHERE id = :app_id"
            ),
            {"app_id": application_id},
        )
        db.commit()
        return {
            "checkout_url": None,
            "status": "stripe_not_configured",
            "note": "Contact sales to complete setup",
        }

    try:
        plan_code = app_row["plan_code"] or ""
        tier_code = app_row["tier_code"] or None
        billing_tier_code = app_row["billing_tier_code"] or None
        billing_mode = _normalize_billing_mode(str(app_row.get("billing_mode") or "FUSION_RCM"))
        addon_codes = list(app_row["addon_codes"] or [])

        if not plan_code or plan_code not in PLANS:
            raise HTTPException(
                status_code=422,
                detail=f"Application has no valid plan_code (got {plan_code!r}). Re-submit via /apply.",
            )

        try:
            quote = calculate_quote(
                plan_code=plan_code,
                tier_code=tier_code,
                billing_tier_code=billing_tier_code,
                addon_codes=addon_codes,
                billing_mode=billing_mode,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if quote.requires_quote:
            raise HTTPException(
                status_code=422,
                detail=f"Plan {plan_code!r} requires a custom quote — contact sales.",
            )

        stripe_lib.api_key = settings.stripe_secret_key
        stage = settings.environment or "prod"

        lookup_keys = [item["lookup_key"] for item in quote.stripe_line_items]
        price_id_map = _get_stripe_price_ids(
            stage=stage,
            aws_region=settings.aws_region or "us-east-1",
            lookup_keys=lookup_keys,
        )

        line_items = []
        for item in quote.stripe_line_items:
            lk = item["lookup_key"]
            price_id = price_id_map.get(lk)
            if price_id:
                entry: dict[str, Any] = {"price": price_id}
                if not item.get("metered"):
                    entry["quantity"] = item.get("quantity", 1)
                line_items.append(entry)
            else:
                unit_amount = lookup_key_to_cents(lk)
                entry = {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"FusionEMS — {lk}"},
                        "unit_amount": unit_amount,
                        "recurring": {
                            "interval": "month",
                            **(
                                {"usage_type": "metered"} if item.get("metered") else {}
                            ),
                        },
                    },
                }
                if not item.get("metered"):
                    entry["quantity"] = item.get("quantity", 1)
                line_items.append(entry)

        if not line_items:
            raise HTTPException(
                status_code=422,
                detail="No billable line items for this plan configuration",
            )

        frontend_base = str(settings.resolved_frontend_base_url()).rstrip("/")
        session = stripe_lib.checkout.Session.create(
            mode="subscription",
            line_items=line_items,
            metadata={"application_id": application_id, "source": "onboarding"},
            success_url=f"{frontend_base}/signup/success?application_id={application_id}",
            cancel_url=f"{frontend_base}/signup?canceled=1&application_id={application_id}",
        )

        db.execute(
            text(
                "UPDATE onboarding_applications SET status = 'payment_pending' WHERE id = :app_id"
            ),
            {"app_id": application_id},
        )
        db.commit()

        return {"checkout_url": session.url}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Stripe checkout creation failed for application %s: %s",
            application_id,
            exc,
        )
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(exc)}") from exc


@router.get("/status/{application_id}")
async def onboarding_status(
    application_id: str, db: Session = Depends(db_session_dependency)
):
    app_row = (
        db.execute(
            text(
                "SELECT id, status, legal_status, tenant_id, provisioned_at, "
                "billing_mode, operational_mode, provisioning_status, provisioning_steps, "
                "provisioning_error, statement_prefix "
                "FROM onboarding_applications WHERE id = :app_id"
            ),
            {"app_id": application_id},
        )
        .mappings()
        .first()
    )

    if app_row is None:
        raise HTTPException(status_code=404, detail="Application not found")

    status = app_row["status"]
    legal_status = app_row["legal_status"]
    provisioned = app_row["provisioned_at"] is not None
    tenant_id = str(app_row["tenant_id"]) if app_row["tenant_id"] else None
    billing_mode = app_row.get("billing_mode") or "FUSION_RCM"
    operational_mode = app_row.get("operational_mode") or "EMS_TRANSPORT"
    # A provisioned tenant must always present as complete, even if prior steps
    # left provisioning_status as a non-null intermediate value.
    if provisioned:
        provisioning_status = "complete"
    else:
        provisioning_status = app_row.get("provisioning_status") or "processing"
    provisioning_steps = app_row.get("provisioning_steps") or []
    provisioning_error = app_row.get("provisioning_error")
    statement_prefix = app_row.get("statement_prefix")

    next_step_map = {
        "started": "sign_legal",
        "legal_pending": "sign_legal",
        "payment_pending": "complete_payment",
        "provisioned": "access_platform",
        "active": "access_platform",
        "revoked": "contact_support",
    }
    next_step = next_step_map.get(status, "contact_support")
    if status == "legal_pending" and legal_status == "signed":
        next_step = "complete_payment"

    success_payload: dict[str, Any] = {
        "billing_mode": billing_mode,
        "operational_mode": operational_mode,
    }
    if billing_mode == "FUSION_RCM":
        success_payload["centralized_billing"] = {
            "enabled": True,
            "statement_prefix": statement_prefix,
        }
    else:
        success_payload["export_pipeline"] = {
            "enabled": True,
            "mode": "sftp_api_handoff",
        }
    if operational_mode == "EXTERNAL_911_CAD":
        success_payload["external_cad"] = {"ingest_ready": True}
    if operational_mode == "HEMS_TRANSPORT":
        success_payload["hems"] = {"aviation_profile_ready": True}

    return {
        "application_id": application_id,
        "status": status,
        "legal_status": legal_status,
        "provisioned": provisioned,
        "provisioning_status": provisioning_status,
        "provisioning_steps": provisioning_steps,
        "provisioning_error": provisioning_error,
        "tenant_id": tenant_id,
        "next_step": next_step,
        "success_payload": success_payload,
    }

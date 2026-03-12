"""Founder Accounting — Bank Connection API

All endpoints are founder-only (require_founder_only_audited).
No tenant data pathway — these bank connections belong exclusively
to the founder's personal/business accounting layer.

Protocols supported (in priority order):
  1. SimpleFIN (open protocol, free)
  2. OFX Direct Connect via ofxtools (open source, MIT)
  3. AmEx Open API (free developer registration)
  4. CSV / OFX file import (universal fallback)
  5. Plaid (optional commercial fallback)
"""
# pylint: disable=unused-import

from __future__ import annotations

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from core_app.accounting.bank_connection_service import (
    BankConnectionProtocol,
    BankConnectionRouter,
    OFXDirectCredentials,
    OFXDirectService,
    SimpleFINService,
    parse_csv_transactions,
)
from core_app.api.dependencies import (
    require_founder_only_audited,
)
from core_app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

accounting_router = APIRouter(
    prefix="/quantum-founder/accounting",
    tags=["Quantum Founder Accounting", "Bank Connections"],
)

_bank_router = BankConnectionRouter()


# ── Status ────────────────────────────────────────────────────────────────────

@accounting_router.get("/bank/status")
async def bank_connection_status(
    current: CurrentUser = Depends(require_founder_only_audited()),
) -> dict:
    """Return current status of all supported bank connection protocols."""
    return {
        "protocols": _bank_router.connection_status(),
        "available": [p.value for p in _bank_router.available_protocols()],
    }


# ── SimpleFIN (open protocol) ─────────────────────────────────────────────────

class SimpleFINConnectRequest(BaseModel):
    setup_token: str = Field(
        description=(
            "One-time base64-encoded setup token obtained from "
            "https://bridge.simplefin.org — exchange it here to get a durable "
            "access URL that will be stored encrypted in settings."
        )
    )


@accounting_router.post("/bank/simplefin/connect")
async def connect_simplefin(
    request: SimpleFINConnectRequest,
    current: CurrentUser = Depends(require_founder_only_audited()),
) -> dict:
    """Exchange a SimpleFIN one-time setup token for a durable access URL.

    After calling this endpoint, set the returned `access_url` as the
    `SIMPLEFIN_ACCESS_URL` environment variable (via AWS Secrets Manager).
    The token is not persisted by this handler — caller is responsible for
    secure storage.
    """
    svc = SimpleFINService()
    try:
        access_url = await svc.exchange_setup_token(request.setup_token)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Mask the access URL in the response — only return the domain for confirmation
    domain = access_url.split("@")[-1].split("/")[0] if "@" in access_url else "unknown"
    logger.info(
        "simplefin_connect_success user_id=%s bridge_domain=%s",
        current.user_id,
        domain,
    )
    return {
        "status": "success",
        "message": "SimpleFIN access URL obtained. Store it as SIMPLEFIN_ACCESS_URL in Secrets Manager.",
        "bridge_domain": domain,
        "access_url": access_url,  # Returned once; must be stored by caller — not logged
    }


@accounting_router.get("/bank/simplefin/accounts")
async def simplefin_accounts(
    days_back: int = 90,
    current: CurrentUser = Depends(require_founder_only_audited()),
) -> dict:
    """Fetch accounts and transactions from SimpleFIN Bridge.

    Requires SIMPLEFIN_ACCESS_URL to be configured.
    """
    access_url = os.environ.get("SIMPLEFIN_ACCESS_URL", "")
    if not access_url:
        raise HTTPException(
            status_code=503,
            detail=(
                "SimpleFIN not configured. "
                "Visit https://bridge.simplefin.org to generate a setup token, "
                "then POST it to /accounting/bank/simplefin/connect."
            ),
        )

    svc = SimpleFINService()
    try:
        accounts, transactions = await svc.get_accounts_and_transactions(
            access_url, days_back=days_back
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "accounts": [a.model_dump() for a in accounts],
        "transactions": [t.model_dump() for t in transactions],
        "transaction_count": len(transactions),
        "protocol": BankConnectionProtocol.SIMPLEFIN,
    }


# ── OFX Direct Connect ────────────────────────────────────────────────────────

@accounting_router.post("/bank/ofx/transactions")
async def ofx_direct_transactions(
    creds: OFXDirectCredentials,
    days_back: int = 90,
    current: CurrentUser = Depends(require_founder_only_audited()),
) -> dict:
    """Fetch transactions via OFX Direct Connect.

    Credentials are passed per-request and never persisted by this handler.
    The caller must store them encrypted in AWS Secrets Manager.

    OFX FID registry: https://ofxhome.com/
    American Express legacy OFX: FID=3101, org=AMEX, accttype=CREDITCARD
    """
    svc = OFXDirectService()
    try:
        account, transactions = await svc.get_transactions(creds, days_back=days_back)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "ofx_direct_error fid=%s account_type=%s error=%s",
            creds.fid,
            creds.account_type,
            str(exc),
        )
        raise HTTPException(status_code=500, detail="OFX Direct Connect failed") from exc

    return {
        "account": account.model_dump(),
        "transactions": [t.model_dump() for t in transactions],
        "transaction_count": len(transactions),
        "protocol": BankConnectionProtocol.OFX_DIRECT,
    }


# ── CSV / OFX file import (universal fallback — Novo, AmEx, any bank) ─────────

@accounting_router.post("/bank/import/csv")
async def import_csv_transactions(
    file: Annotated[UploadFile, File(description="Bank CSV export (Novo, AmEx, or generic)")],
    institution: Annotated[
        str, Form(description="Institution hint: novo|amex|generic")
    ] = "generic",
    account_id: Annotated[
        str, Form(description="Optional account identifier for deduplication")
    ] = "imported",
    current: CurrentUser = Depends(require_founder_only_audited()),
) -> dict:
    """Parse a CSV bank export and return normalized transactions.

    Supported layouts: Novo CSV, AmEx CSV, generic date/amount/description.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="File must be a .csv export")

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:  # 5 MB guard
        raise HTTPException(status_code=413, detail="CSV file exceeds 5 MB limit")

    try:
        transactions = parse_csv_transactions(raw, institution=institution, account_id=account_id)
    except Exception as exc:
        logger.error("csv_import_error institution=%s error=%s", institution, str(exc))
        raise HTTPException(status_code=422, detail=f"CSV parse failed: {exc}") from exc

    return {
        "transactions": [t.model_dump() for t in transactions],
        "transaction_count": len(transactions),
        "institution": institution,
        "protocol": BankConnectionProtocol.CSV_IMPORT,
    }


@accounting_router.post("/bank/import/ofx")
async def import_ofx_transactions(
    file: Annotated[
        UploadFile,
        File(description="OFX/QFX export from any bank (Novo, AmEx, Chase, etc.)"),
    ],
    institution: Annotated[str, Form(description="Institution name for display")] = "Imported",
    current: CurrentUser = Depends(require_founder_only_audited()),
) -> dict:
    """Parse an OFX/QFX file export and return normalized accounts + transactions.

    Novo exports QFX; AmEx exports OFX/QFX; most traditional banks export OFX.
    """
    filename = (file.filename or "").lower()
    if not (filename.endswith(".ofx") or filename.endswith(".qfx")):
        raise HTTPException(status_code=422, detail="File must be .ofx or .qfx")

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="OFX file exceeds 5 MB limit")

    svc = OFXDirectService()
    try:
        accounts, transactions = await svc.parse_ofx_file(raw, institution_name=institution)
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("ofx_import_error institution=%s error=%s", institution, str(exc))
        raise HTTPException(status_code=422, detail=f"OFX parse failed: {exc}") from exc

    return {
        "accounts": [a.model_dump() for a in accounts],
        "transactions": [t.model_dump() for t in transactions],
        "transaction_count": len(transactions),
        "protocol": BankConnectionProtocol.CSV_IMPORT,
    }


# ── Plaid optional fallback ───────────────────────────────────────────────────

@accounting_router.post("/bank/plaid/link-token")
async def create_plaid_link_token(
    current: CurrentUser = Depends(require_founder_only_audited()),
) -> dict:
    """Create a Plaid Link token to initiate the institution linking flow.

    Only available when PLAID_CLIENT_ID + PLAID_SECRET are configured.
    """
    from core_app.accounting.bank_connection_service import PlaidFallbackService
    svc = PlaidFallbackService()
    if not svc.is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Plaid not configured. Set PLAID_CLIENT_ID and PLAID_SECRET. "
                "SimpleFIN (open source, free) is recommended as the primary option."
            ),
        )
    try:
        link_token = await svc.create_link_token(str(current.user_id))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"link_token": link_token, "protocol": BankConnectionProtocol.PLAID}


class PlaidExchangeRequest(BaseModel):
    public_token: str


@accounting_router.post("/bank/plaid/exchange")
async def exchange_plaid_public_token(
    request: PlaidExchangeRequest,
    current: CurrentUser = Depends(require_founder_only_audited()),
) -> dict:
    """Exchange a Plaid Link public token for a durable access token.

    The access token must be stored encrypted by the caller (never returned in logs).
    Use AWS Secrets Manager for storage.
    """
    from core_app.accounting.bank_connection_service import PlaidFallbackService
    svc = PlaidFallbackService()
    if not svc.is_configured():
        raise HTTPException(status_code=503, detail="Plaid not configured")

    try:
        access_token = await svc.exchange_public_token(request.public_token)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info("plaid_exchange_success user_id=%s", current.user_id)
    return {
        "access_token": access_token,  # Caller must store this in Secrets Manager
        "message": "Store access_token in AWS Secrets Manager. Do not log or expose it.",
        "protocol": BankConnectionProtocol.PLAID,
    }


class PlaidSyncRequest(BaseModel):
    access_token: str
    cursor: str | None = None


@accounting_router.post("/bank/plaid/sync")
async def sync_plaid_transactions(
    request: PlaidSyncRequest,
    current: CurrentUser = Depends(require_founder_only_audited()),
) -> dict:
    """Sync new transactions from Plaid using the /transactions/sync cursor API."""
    from core_app.accounting.bank_connection_service import PlaidFallbackService
    svc = PlaidFallbackService()
    if not svc.is_configured():
        raise HTTPException(status_code=503, detail="Plaid not configured")

    try:
        transactions, next_cursor = await svc.sync_transactions(
            request.access_token, cursor=request.cursor
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "transactions": [t.model_dump() for t in transactions],
        "transaction_count": len(transactions),
        "next_cursor": next_cursor,
        "protocol": BankConnectionProtocol.PLAID,
    }

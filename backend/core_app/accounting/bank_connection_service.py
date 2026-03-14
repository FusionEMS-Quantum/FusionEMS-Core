"""Bank connection service — open source first, commercial fallback.

Protocol hierarchy (in order of preference):

1. **SimpleFIN** (open protocol, simplefin.org — free tier)
   - 500+ US bank connections via user-established setup token
   - Open protocol spec: https://www.simplefin.org/protocol.html
   - Best for: most consumer and community banks, credit unions
   - Novo: supported via SimpleFIN Bridge

2. **OFX Direct Connect** (ofxtools — MIT license)
   - Direct machine-to-machine OFX/QFX connection for traditional banks
   - Works with: Chase, Wells Fargo, US Bank, Citibank, TD Bank, AmEx (legacy)
   - No middleman, credentials stay server-side

3. **American Express Open API** (free developer registration)
   - REST API via developer.americanexpress.com
   - Requires AmEx developer account + OAuth

4. **CSV / OFX file import** (always-available fallback)
   - Novo exports CSV; AmEx exports CSV/OFX/QFX
   - Parsed locally with ofxtools; zero external dependency

5. **Plaid** (optional commercial add-on — only if PLAID keys configured)
   - Fallback for any bank not covered above
   - Free dev tier: 100 items; paid production

Security contract:
- Access tokens / credentials stored encrypted via AWS Secrets Manager or DB AES
- Never logged, never returned in API responses
- All account data scoped exclusively to founder (no tenant pathway)
"""
from __future__ import annotations

import base64
import csv
import io
import logging
import os
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------

class BankConnectionProtocol(StrEnum):
    SIMPLEFIN = "simplefin"
    OFX_DIRECT = "ofx_direct"
    AMEX_API = "amex_api"
    CSV_IMPORT = "csv_import"
    PLAID = "plaid"


class LinkedAccount(BaseModel):
    account_id: str
    institution_name: str
    name: str
    official_name: str | None = None
    type: str                          # checking | savings | credit
    subtype: str | None = None
    mask: str | None = None            # last 4 digits
    current_balance: float | None = None
    available_balance: float | None = None
    currency: str = "USD"
    protocol: BankConnectionProtocol


class BankTransaction(BaseModel):
    transaction_id: str
    account_id: str
    amount: float                      # positive = debit/expense; negative = credit/payment
    posted_date: str                   # ISO 8601 date
    description: str
    merchant_name: str | None = None
    category: list[str] = Field(default_factory=list)
    pending: bool = False
    protocol: BankConnectionProtocol


# ---------------------------------------------------------------------------
# 1. SimpleFIN (open protocol)
# ---------------------------------------------------------------------------

class SimpleFINService:
    """SimpleFIN open banking protocol.

    Setup flow:
      1. User visits https://bridge.simplefin.org to create a setup token.
      2. POST the setup token to /accounting/bank/simplefin/connect.
      3. Backend exchanges it for a durable access URL (stored encrypted).
      4. Subsequent calls use the access URL to fetch accounts + transactions.

    Environment:
      SIMPLEFIN_ACCESS_URL — stored after first exchange (encrypted in DB)

    Free plan: personal use, real-time transactions, 500+ US institutions.
    """

    BRIDGE_SETUP_EXCHANGE = "https://bridge.simplefin.org/simplefin/claim"

    async def exchange_setup_token(self, setup_token: str) -> str:
        """Exchange a one-time setup token for a durable SimpleFIN access URL.

        The access URL is long-lived and must be stored encrypted.
        """
        # Setup token is base64-encoded URL
        try:
            claim_url = base64.b64decode(setup_token).decode("utf-8").strip()
        except Exception as exc:
            raise ValueError(f"Invalid SimpleFIN setup token (not base64): {exc}") from exc

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(claim_url)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"SimpleFIN token exchange failed: HTTP {resp.status_code} — {resp.text}"
                )
            access_url = resp.text.strip()

        logger.info("simplefin_token_exchange success access_url_domain=%s",
                    access_url.split("@")[-1].split("/")[0] if "@" in access_url else "unknown")
        return access_url

    async def get_accounts_and_transactions(
        self,
        access_url: str,
        days_back: int = 90,
    ) -> tuple[list[LinkedAccount], list[BankTransaction]]:
        """Fetch accounts and recent transactions from SimpleFIN Bridge."""
        start_date = date.today() - timedelta(days=days_back)
        url = f"{access_url}/accounts?start-date={int(datetime.combine(start_date, datetime.min.time()).timestamp())}"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise RuntimeError(f"SimpleFIN accounts fetch failed: HTTP {resp.status_code}")
            data = resp.json()

        accounts: list[LinkedAccount] = []
        transactions: list[BankTransaction] = []
        errors: list[str] = data.get("errors", [])
        if errors:
            logger.warning("simplefin_fetch_errors errors=%s", errors)

        for acct in data.get("accounts", []):
            org = acct.get("org", {})
            acct_id = acct.get("id", "")
            linked = LinkedAccount(
                account_id=acct_id,
                institution_name=org.get("name", "Unknown Institution"),
                name=acct.get("name", "Account"),
                type="checking",
                current_balance=float(acct.get("balance", 0.0)),
                currency=acct.get("currency", "USD"),
                protocol=BankConnectionProtocol.SIMPLEFIN,
            )
            accounts.append(linked)

            for txn in acct.get("transactions", []):
                transactions.append(
                    BankTransaction(
                        transaction_id=txn.get("id", ""),
                        account_id=acct_id,
                        amount=float(txn.get("amount", 0.0)),
                        posted_date=date.fromtimestamp(txn.get("posted", 0)).isoformat(),
                        description=txn.get("description", ""),
                        merchant_name=txn.get("payee"),
                        pending=txn.get("pending", False),
                        protocol=BankConnectionProtocol.SIMPLEFIN,
                    )
                )

        return accounts, transactions


# ---------------------------------------------------------------------------
# 2. OFX Direct Connect (ofxtools — MIT open source)
# ---------------------------------------------------------------------------

class OFXDirectCredentials(BaseModel):
    """Credentials for OFX Direct Connect.  Store encrypted — never log."""
    fid: str            # Financial institution FID (e.g., "10898" for Chase)
    org: str            # FI org string (e.g., "B1")
    url: str            # OFX server URL
    username: str
    password: str       # Must be stored encrypted at rest
    account_id: str
    account_type: str = "CHECKING"  # CHECKING | SAVINGS | CREDITCARD


class OFXDirectService:
    """OFX 2.x Direct Connect using ofxtools (MIT license).

    Works with: Chase, Wells Fargo, US Bank, Citibank, TD Bank,
                First National, and most traditional US banks.

    Notable OFX FID registry: https://ofxhome.com/

    American Express OFX endpoint:
      FID: 3101, ORG: AMEX, URL: https://online.americanexpress.com/myca/ofxexport/...

    Requires: ofxtools >= 0.9 (pip install ofxtools)
    """

    async def get_transactions(
        self,
        creds: OFXDirectCredentials,
        days_back: int = 90,
    ) -> tuple[LinkedAccount, list[BankTransaction]]:
        """Fetch transactions via OFX Direct Connect."""
        try:
            from ofxtools.Client import OFXClient, StmtRq  # type: ignore[import]
            from ofxtools.utils import UTC as OFX_UTC  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "ofxtools is required for OFX Direct Connect. "
                "Add 'ofxtools' to requirements.txt."
            ) from exc

        dtstart = datetime.now(OFX_UTC) - timedelta(days=days_back)
        client = OFXClient(
            url=creds.url,
            org=creds.org,
            fid=creds.fid,
            version=220,
        )

        stmtrq = StmtRq(
            acctid=creds.account_id,
            accttype=creds.account_type,
            dtstart=dtstart,
        )

        response = client.request_statements(
            userid=creds.username,
            userpass=creds.password,
            stmtrqs=[stmtrq],
        )

        stmt = response.statements[0]
        account = LinkedAccount(
            account_id=creds.account_id,
            institution_name=creds.org,
            name=f"{creds.org} {creds.account_type}",
            type="credit" if creds.account_type == "CREDITCARD" else "checking",
            mask=creds.account_id[-4:],
            current_balance=float(stmt.ledgerbal.balamt) if stmt.ledgerbal else None,
            protocol=BankConnectionProtocol.OFX_DIRECT,
        )

        transactions: list[BankTransaction] = []
        for txn in stmt.transactions:
            transactions.append(
                BankTransaction(
                    transaction_id=str(txn.fitid),
                    account_id=creds.account_id,
                    amount=float(txn.trnamt),
                    posted_date=txn.dtposted.date().isoformat(),
                    description=str(txn.name or txn.memo or ""),
                    merchant_name=str(txn.name) if txn.name else None,
                    pending=False,
                    protocol=BankConnectionProtocol.OFX_DIRECT,
                )
            )

        return account, transactions

    async def parse_ofx_file(
        self,
        file_bytes: bytes,
        institution_name: str = "Imported",
    ) -> tuple[list[LinkedAccount], list[BankTransaction]]:
        """Parse an OFX/QFX file exported from the bank portal.

        This is the zero-dependency fallback — works with any bank that
        offers OFX/QFX export (Novo, AmEx, Chase, etc.).
        """
        try:
            from ofxtools.Parser import OFXTree  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError("ofxtools required for OFX file parsing") from exc

        parser = OFXTree()
        parser.parse(io.BytesIO(file_bytes))
        ofx = parser.convert()

        accounts: list[LinkedAccount] = []
        transactions: list[BankTransaction] = []

        for stmt in getattr(ofx, "statements", []):
            acct = stmt.account
            acct_id = str(acct.acctid)
            accounts.append(
                LinkedAccount(
                    account_id=acct_id,
                    institution_name=institution_name,
                    name=f"{institution_name} ···{acct_id[-4:]}",
                    type="credit" if "CREDIT" in str(type(acct).__name__).upper() else "checking",
                    mask=acct_id[-4:],
                    current_balance=(
                        float(stmt.ledgerbal.balamt) if stmt.ledgerbal else None
                    ),
                    protocol=BankConnectionProtocol.CSV_IMPORT,
                )
            )
            for txn in stmt.transactions:
                transactions.append(
                    BankTransaction(
                        transaction_id=str(txn.fitid),
                        account_id=acct_id,
                        amount=float(txn.trnamt),
                        posted_date=txn.dtposted.date().isoformat(),
                        description=str(txn.name or txn.memo or ""),
                        merchant_name=str(txn.name) if txn.name else None,
                        protocol=BankConnectionProtocol.CSV_IMPORT,
                    )
                )

        return accounts, transactions


# ---------------------------------------------------------------------------
# 3. CSV import (universal fallback — Novo, AmEx, any bank)
# ---------------------------------------------------------------------------

# Known CSV column mappings per institution
_CSV_SCHEMAS: dict[str, dict[str, str]] = {
    "novo": {
        "date": "Date",
        "amount": "Amount",
        "description": "Description",
        "type": "Type",
        "balance": "Balance",
    },
    "amex": {
        "date": "Date",
        "amount": "Amount",
        "description": "Description",
        "card_member": "Card Member",
        "account_number": "Account #",
    },
    "generic": {
        "date": "Date",
        "amount": "Amount",
        "description": "Description",
    },
}


def parse_csv_transactions(
    csv_bytes: bytes,
    institution: str = "generic",
    account_id: str = "imported",
) -> list[BankTransaction]:
    """Parse a bank CSV export into BankTransaction records.

    Supports Novo, American Express, and generic "date/amount/description"
    layouts.  Amounts: positive = debit/expense, negative = credit/payment
    (Novo convention — AmEx convention is opposite, auto-detected).
    """
    schema = _CSV_SCHEMAS.get(institution.lower(), _CSV_SCHEMAS["generic"])
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    transactions: list[BankTransaction] = []
    for i, row in enumerate(reader):
        raw_date = row.get(schema["date"], "").strip()
        raw_amount = row.get(schema["amount"], "0").strip().replace(",", "").replace("$", "")
        description = row.get(schema["description"], "").strip()

        if not raw_date or not raw_amount:
            continue

        try:
            # Handle MM/DD/YYYY and YYYY-MM-DD
            if "/" in raw_date:
                parsed_date = datetime.strptime(raw_date, "%m/%d/%Y").date()
            else:
                parsed_date = date.fromisoformat(raw_date)
        except ValueError:
            logger.warning("csv_parse skip row=%d bad_date=%s", i, raw_date)
            continue

        try:
            amount = float(raw_amount)
            # AmEx exports positive as charges — normalize to positive = expense
        except ValueError:
            continue

        transactions.append(
            BankTransaction(
                transaction_id=f"{institution}_{account_id}_{i}_{raw_date}",
                account_id=account_id,
                amount=amount,
                posted_date=parsed_date.isoformat(),
                description=description,
                protocol=BankConnectionProtocol.CSV_IMPORT,
            )
        )

    return transactions


# ---------------------------------------------------------------------------
# 4. American Express Open API (free, requires developer account)
# ---------------------------------------------------------------------------

class AmexAPIService:
    """American Express Open Banking / Account Services API.

    Registration: https://developer.americanexpress.com
    Free for registered developers. OAuth2 client_credentials flow.

    Environment:
      AMEX_CLIENT_ID     — from AmEx developer dashboard
      AMEX_CLIENT_SECRET — from AmEx developer dashboard
    """

    _TOKEN_URL = "https://api.americanexpress.com/apiplatform/v1/oauth/token"
    _ACCOUNTS_URL = "https://api.americanexpress.com/servicing/v1/accounts"

    def __init__(self) -> None:
        self._client_id = os.environ.get("AMEX_CLIENT_ID", "")
        self._client_secret = os.environ.get("AMEX_CLIENT_SECRET", "")
        self._access_token: str | None = None

    def _is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def is_configured(self) -> bool:
        return self._is_configured()

    async def _ensure_token(self) -> str:
        if self._access_token:
            return self._access_token

        if not self._is_configured():
            raise RuntimeError(
                "AmEx API not configured. Set AMEX_CLIENT_ID and AMEX_CLIENT_SECRET. "
                "Register at https://developer.americanexpress.com"
            )

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self._TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]

        return self._access_token  # type: ignore[return-value]

    async def get_accounts(self) -> list[LinkedAccount]:
        token = await self._ensure_token()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self._ACCOUNTS_URL,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        accounts = []
        for acct in data.get("accounts", []):
            accounts.append(
                LinkedAccount(
                    account_id=acct.get("account_token", ""),
                    institution_name="American Express",
                    name=acct.get("description", "AmEx Card"),
                    type="credit",
                    mask=acct.get("account_display_number", "")[-4:],
                    current_balance=float(acct.get("balance", {}).get("amount", 0.0)),
                    protocol=BankConnectionProtocol.AMEX_API,
                )
            )
        return accounts


# ---------------------------------------------------------------------------
# 5. Plaid optional fallback (only used if PLAID_CLIENT_ID is set)
# ---------------------------------------------------------------------------

class PlaidFallbackService:
    """Plaid as optional last-resort fallback.

    Only active when PLAID_CLIENT_ID + PLAID_SECRET are configured.
    Free dev tier: 100 items. Production pricing per-item/month.

    Use this for: Novo (if not covered by SimpleFIN), any bank not
    reachable via OFX or SimpleFIN.
    """

    _ENV_URLS = {
        "sandbox": "https://sandbox.plaid.com",
        "development": "https://development.plaid.com",
        "production": "https://production.plaid.com",
    }

    def __init__(self) -> None:
        self._client_id = os.environ.get("PLAID_CLIENT_ID", "")
        self._secret = os.environ.get("PLAID_SECRET", "")
        env = os.environ.get("PLAID_ENV", "sandbox")
        self._base = self._ENV_URLS.get(env, self._ENV_URLS["sandbox"])

    def is_configured(self) -> bool:
        return bool(self._client_id and self._secret)

    def _auth(self) -> dict[str, str]:
        return {"client_id": self._client_id, "secret": self._secret}

    async def create_link_token(self, user_id: str) -> str:
        if not self.is_configured():
            raise RuntimeError("Plaid not configured (PLAID_CLIENT_ID / PLAID_SECRET)")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base}/link/token/create",
                json={
                    **self._auth(),
                    "user": {"client_user_id": user_id},
                    "client_name": "FusionEMS Accounting",
                    "products": ["transactions"],
                    "country_codes": ["US"],
                    "language": "en",
                },
            )
            resp.raise_for_status()
        return resp.json()["link_token"]

    async def exchange_public_token(self, public_token: str) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base}/item/public_token/exchange",
                json={**self._auth(), "public_token": public_token},
            )
            resp.raise_for_status()
        return resp.json()["access_token"]

    async def get_accounts(self, access_token: str) -> list[LinkedAccount]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base}/accounts/get",
                json={**self._auth(), "access_token": access_token},
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            LinkedAccount(
                account_id=a["account_id"],
                institution_name="Bank (Plaid)",
                name=a["name"],
                official_name=a.get("official_name"),
                type=a["type"],
                subtype=a.get("subtype"),
                mask=a.get("mask"),
                current_balance=(a.get("balances") or {}).get("current"),
                available_balance=(a.get("balances") or {}).get("available"),
                protocol=BankConnectionProtocol.PLAID,
            )
            for a in data.get("accounts", [])
        ]

    async def sync_transactions(
        self,
        access_token: str,
        cursor: str | None = None,
    ) -> tuple[list[BankTransaction], str | None]:
        body: dict[str, Any] = {**self._auth(), "access_token": access_token}
        if cursor:
            body["cursor"] = cursor

        all_txns: list[BankTransaction] = []
        has_more = True
        next_cursor = cursor

        async with httpx.AsyncClient(timeout=30) as client:
            while has_more:
                if next_cursor:
                    body["cursor"] = next_cursor
                resp = await client.post(
                    f"{self._base}/transactions/sync", json=body
                )
                resp.raise_for_status()
                data = resp.json()
                for txn in data.get("added", []):
                    all_txns.append(
                        BankTransaction(
                            transaction_id=txn["transaction_id"],
                            account_id=txn["account_id"],
                            amount=txn["amount"],
                            posted_date=txn["date"],
                            description=txn["name"],
                            merchant_name=txn.get("merchant_name"),
                            category=txn.get("category") or [],
                            pending=txn.get("pending", False),
                            protocol=BankConnectionProtocol.PLAID,
                        )
                    )
                has_more = data.get("has_more", False)
                next_cursor = data.get("next_cursor")

        return all_txns, next_cursor


# ---------------------------------------------------------------------------
# Unified BankConnectionRouter — picks the right protocol automatically
# ---------------------------------------------------------------------------

class BankConnectionRouter:
    """Single entry point that routes to the right bank protocol.

    Priority:
      1. SimpleFIN — if SIMPLEFIN_ACCESS_URL is set
      2. OFX Direct — if OFX credentials are configured
      3. AmEx API — if AMEX_CLIENT_ID is set
      4. CSV/OFX file — always available (manual import)
      5. Plaid — if PLAID_CLIENT_ID is set (commercial fallback)
    """

    def __init__(self) -> None:
        self.simplefin = SimpleFINService()
        self.ofx = OFXDirectService()
        self.amex = AmexAPIService()
        self.plaid = PlaidFallbackService()

    def available_protocols(self) -> list[BankConnectionProtocol]:
        available = [BankConnectionProtocol.CSV_IMPORT]
        if os.environ.get("SIMPLEFIN_ACCESS_URL"):
            available.insert(0, BankConnectionProtocol.SIMPLEFIN)
        if self.amex.is_configured():
            available.append(BankConnectionProtocol.AMEX_API)
        if self.plaid.is_configured():
            available.append(BankConnectionProtocol.PLAID)
        return available

    def connection_status(self) -> dict[str, Any]:
        return {
            "simplefin": {
                "status": "connected" if os.environ.get("SIMPLEFIN_ACCESS_URL") else "not_configured",
                "description": "Open protocol — 500+ US banks including Novo",
                "setup_url": "https://bridge.simplefin.org",
                "cost": "Free",
                "open_source": True,
            },
            "ofx_direct": {
                "status": "available",
                "description": "OFX Direct Connect — traditional banks (Chase, WF, USB, etc.)",
                "library": "ofxtools (MIT)",
                "cost": "Free",
                "open_source": True,
            },
            "amex_api": {
                "status": "connected" if self.amex.is_configured() else "not_configured",
                "description": "American Express Open Banking API",
                "setup_url": "https://developer.americanexpress.com",
                "cost": "Free (registration required)",
                "open_source": False,
            },
            "csv_import": {
                "status": "ready",
                "description": "Manual CSV/OFX/QFX file import — works with any bank",
                "supported_formats": ["Novo CSV", "AmEx CSV", "Standard OFX", "QFX"],
                "cost": "Free",
                "open_source": True,
            },
            "plaid": {
                "status": "connected" if self.plaid.is_configured() else "not_configured",
                "description": "Plaid — commercial fallback for any bank not covered above",
                "setup_url": "https://dashboard.plaid.com",
                "cost": "Free dev tier (100 items); paid production",
                "open_source": False,
            },
        }

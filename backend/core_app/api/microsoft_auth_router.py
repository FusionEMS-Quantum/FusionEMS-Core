"""Microsoft Entra ID (Azure AD) authorization code flow.

Endpoints:
  GET  /auth/microsoft/login    — Redirect to Entra authorize URL
  GET  /auth/microsoft/callback — Exchange code for tokens, issue JWT, redirect to frontend
  GET  /auth/microsoft/logout   — Redirect to Entra logout, then back to frontend login page
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.core.security import create_access_token
from core_app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/microsoft", tags=["auth"])

_AUTHORIZE_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"
_LOGOUT_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout"
_SCOPES = "openid email profile User.Read"
_ALLOWED_LOGIN_INTENTS: tuple[str, ...] = ("default", "founder")

_STATE_TTL_SECONDS = 600


def _normalize_intent(intent: str) -> str:
    normalized = intent.strip().lower()
    if normalized not in _ALLOWED_LOGIN_INTENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported login intent '{intent}'",
        )
    return normalized


def _sign_state(intent: str) -> str:
    s = get_settings()
    payload = f"{secrets.token_hex(16)}|{int(time.time())}|{intent}"
    sig = hmac.new(
        str(s.jwt_secret_key).encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}|{sig}"


def _verify_state(state: str) -> str | None:
    s = get_settings()
    parts = state.split("|")
    if len(parts) != 4:
        return None
    nonce, ts_str, intent, sig = parts
    if intent not in _ALLOWED_LOGIN_INTENTS:
        return None
    try:
        ts = int(ts_str)
    except ValueError:
        return None
    if abs(time.time() - ts) > _STATE_TTL_SECONDS:
        return None
    expected_payload = f"{nonce}|{ts_str}|{intent}"
    expected_sig = hmac.new(
        str(s.jwt_secret_key).encode(), expected_payload.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None
    return intent


def _append_query_param(base_url: str, key: str, value: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    query_pairs = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if k != key
    ]
    query_pairs.append((key, value))
    updated_query = urllib.parse.urlencode(query_pairs)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, updated_query, parsed.fragment)
    )


def _is_entra_configured() -> bool:
    s = get_settings()
    return bool(all([s.graph_tenant_id, s.graph_client_id, s.graph_client_secret]))


def _redirect_auth_unavailable(*, intent: str | None = None) -> RedirectResponse:
    s = get_settings()
    redirect_url = _append_query_param(s.microsoft_post_logout_url, "error", "entra_not_configured")
    if intent:
        redirect_url = _append_query_param(redirect_url, "intent", intent)
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/login")
def microsoft_login(intent: str = Query(default="default")) -> RedirectResponse:
    normalized_intent = _normalize_intent(intent)
    if not _is_entra_configured():
        logger.warning("entra_login_unavailable reason=missing_configuration intent=%s", normalized_intent)
        return _redirect_auth_unavailable(intent=normalized_intent)

    s = get_settings()
    state = _sign_state(normalized_intent)
    params = {
        "client_id": s.graph_client_id,
        "response_type": "code",
        "redirect_uri": s.microsoft_redirect_uri,
        "scope": _SCOPES,
        "response_mode": "query",
        "state": state,
    }
    url = (
        _AUTHORIZE_URL.format(tenant_id=s.graph_tenant_id)
        + "?"
        + urllib.parse.urlencode(params)
    )
    return RedirectResponse(url=url, status_code=302)


def _exchange_code(code: str) -> dict[str, Any]:
    s = get_settings()
    body = urllib.parse.urlencode(
        {
            "client_id": s.graph_client_id,
            "client_secret": s.graph_client_secret,
            "code": code,
            "redirect_uri": s.microsoft_redirect_uri,
            "grant_type": "authorization_code",
            "scope": _SCOPES,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        _TOKEN_URL.format(tenant_id=s.graph_tenant_id),
        data=body,
        method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error(
            "entra_token_exchange_failed status=%d body=%.300s", exc.code, error_body
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with Entra",
        ) from exc
    except urllib.error.URLError as exc:
        logger.error("entra_token_exchange_network_error reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error contacting Entra token endpoint",
        ) from exc


def _fetch_userinfo(access_token: str) -> dict[str, Any]:
    req = urllib.request.Request(_USERINFO_URL, method="GET")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error(
            "entra_userinfo_failed status=%d body=%.300s", exc.code, error_body
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch user profile from Microsoft Graph",
        ) from exc
    except urllib.error.URLError as exc:
        logger.error("entra_userinfo_network_error reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error contacting Microsoft Graph",
        ) from exc


@router.get("/callback")
def microsoft_callback(
    code: str = Query(default=""),
    error: str = Query(default=""),
    error_description: str = Query(default=""),
    state: str = Query(default=""),
    db: Session = Depends(db_session_dependency),
) -> RedirectResponse:
    if not _is_entra_configured():
        logger.warning("entra_callback_unavailable reason=missing_configuration")
        return _redirect_auth_unavailable()

    s = get_settings()

    if error:
        logger.warning(
            "entra_callback_error error=%s desc=%s", error, error_description
        )
        return RedirectResponse(
            url=f"{s.microsoft_post_logout_url}?error=entra_denied",
            status_code=302,
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code"
        )

    verified_intent = _verify_state(state)
    if verified_intent is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter",
        )

    token_data = _exchange_code(code)
    ms_access_token: str = token_data.get("access_token", "")
    if not ms_access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No access_token in Entra response",
        )

    userinfo = _fetch_userinfo(ms_access_token)
    email: str = (
        (userinfo.get("mail") or userinfo.get("userPrincipalName") or "")
        .lower()
        .strip()
    )
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email in Microsoft profile",
        )

    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email)
    if user is None:
        logger.warning("entra_login_no_matching_user email=%s", email)
        return RedirectResponse(
            url=f"{s.microsoft_post_logout_url}?error=no_account",
            status_code=302,
        )

    jwt_token = create_access_token(str(user.id), str(user.tenant_id), user.role or "")
    logger.info("entra_login_success user_id=%s email=%s", user.id, email)

    post_login_target = (
        s.microsoft_founder_post_login_url
        if verified_intent == "founder"
        else s.microsoft_post_login_url
    )
    redirect_url = _append_query_param(post_login_target, "token", jwt_token)
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/logout")
def microsoft_logout() -> RedirectResponse:
    if not _is_entra_configured():
        logger.warning("entra_logout_unavailable reason=missing_configuration")
        return _redirect_auth_unavailable()

    s = get_settings()
    params = {
        "post_logout_redirect_uri": s.microsoft_post_logout_url,
    }
    url = (
        _LOGOUT_URL.format(tenant_id=s.graph_tenant_id)
        + "?"
        + urllib.parse.urlencode(params)
    )
    return RedirectResponse(url=url, status_code=302)

"""Microsoft Entra ID (Azure AD) authorization code flow.

Endpoints:
    GET  /auth/microsoft/login    — Redirect to Entra authorize URL
    GET  /auth/microsoft/callback — Validate ID token + policy, issue app session, redirect
    GET  /auth/microsoft/logout   — Clear app session and redirect to Entra logout
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
from jose import JWTError, jwt
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
_OPENID_CONFIGURATION_URL = (
    "https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
)
_SCOPES = "openid email profile User.Read"
_ALLOWED_LOGIN_INTENTS: tuple[str, ...] = ("default", "founder")

_STATE_TTL_SECONDS = 600
_DEFAULT_OIDC_TIMEOUT_SECONDS = 15

_oidc_cache: dict[str, Any] = {"expires_at": 0.0, "config": None}
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _normalize_intent(intent: str) -> str:
    normalized = intent.strip().lower()
    if normalized not in _ALLOWED_LOGIN_INTENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported login intent '{intent}'",
        )
    return normalized


def _sign_state(intent: str, nonce: str) -> str:
    s = get_settings()
    payload = f"{nonce}|{int(time.time())}|{intent}"
    sig = hmac.new(
        str(s.jwt_secret_key).encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}|{sig}"


def _verify_state(state: str) -> tuple[str, str] | None:
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
    return intent, nonce


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


def _oidc_cache_ttl() -> int:
    ttl = int(get_settings().microsoft_oidc_cache_ttl_seconds)
    return ttl if ttl > 0 else 300


def _fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=_DEFAULT_OIDC_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error("entra_oidc_http_error status=%d body=%.300s", exc.code, body)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to retrieve Entra OpenID metadata",
        ) from exc
    except urllib.error.URLError as exc:
        logger.error("entra_oidc_network_error reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Network error retrieving Entra OpenID metadata",
        ) from exc


def _get_openid_configuration() -> dict[str, Any]:
    now = time.time()
    cached_config = _oidc_cache.get("config")
    cached_expiry = float(_oidc_cache.get("expires_at", 0.0))
    if isinstance(cached_config, dict) and cached_expiry > now:
        return cached_config

    s = get_settings()
    config = _fetch_json(_OPENID_CONFIGURATION_URL.format(tenant_id=s.graph_tenant_id))
    _oidc_cache["expires_at"] = now + _oidc_cache_ttl()
    _oidc_cache["config"] = config
    return config


def _get_jwks(jwks_uri: str) -> dict[str, Any]:
    now = time.time()
    cached = _jwks_cache.get(jwks_uri)
    if cached is not None and cached[0] > now:
        return cached[1]

    keys = _fetch_json(jwks_uri)
    _jwks_cache[jwks_uri] = (now + _oidc_cache_ttl(), keys)
    return keys


def _extract_email(claims: dict[str, Any], userinfo: dict[str, Any]) -> str:
    candidates = (
        claims.get("preferred_username"),
        claims.get("email"),
        userinfo.get("mail"),
        userinfo.get("userPrincipalName"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.lower().strip()
    return ""


def _parse_groups(claims: dict[str, Any]) -> set[str]:
    raw_groups = claims.get("groups")
    if not isinstance(raw_groups, list):
        return set()
    groups: set[str] = set()
    for item in raw_groups:
        if isinstance(item, str) and item.strip():
            groups.add(item.strip())
    return groups


def _parse_founder_allowlist() -> set[str]:
    raw = str(get_settings().microsoft_founder_allowlist_emails or "")
    if not raw:
        return set()
    return {
        value.strip().lower()
        for value in raw.split(",")
        if isinstance(value, str) and value.strip()
    }


def _founder_claim_policy_satisfied(*, email: str, claims: dict[str, Any]) -> bool:
    s = get_settings()
    founder_group_id = str(s.microsoft_founder_required_group_id or "").strip()
    allowlist = _parse_founder_allowlist()

    group_ok = not founder_group_id or founder_group_id in _parse_groups(claims)
    allowlist_ok = not allowlist or email in allowlist
    return group_ok and allowlist_ok


def _build_error_redirect(code: str, *, intent: str | None = None) -> RedirectResponse:
    s = get_settings()
    redirect_url = _append_query_param(s.microsoft_post_logout_url, "error", code)
    if intent:
        redirect_url = _append_query_param(redirect_url, "intent", intent)
    return RedirectResponse(url=redirect_url, status_code=302)


def _set_session_cookie(response: RedirectResponse, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        key=s.session_cookie_name,
        value=token,
        httponly=True,
        secure=s.session_cookie_secure,
        samesite=s.session_cookie_samesite,
        max_age=s.session_cookie_max_age_seconds,
        domain=s.session_cookie_domain or None,
        path="/",
    )


def _clear_session_cookie(response: RedirectResponse) -> None:
    s = get_settings()
    response.delete_cookie(
        key=s.session_cookie_name,
        domain=s.session_cookie_domain or None,
        path="/",
    )


def _validate_id_token(id_token: str, expected_nonce: str) -> dict[str, Any]:
    s = get_settings()
    oidc = _get_openid_configuration()
    jwks_uri = str(oidc.get("jwks_uri") or "")
    issuer = str(oidc.get("issuer") or "")
    if not jwks_uri or not issuer:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid Entra OIDC discovery metadata",
        )

    unverified_header = jwt.get_unverified_header(id_token)
    kid = str(unverified_header.get("kid") or "")
    alg = str(unverified_header.get("alg") or "")
    if not kid or not alg:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ID token header",
        )

    jwks = _get_jwks(jwks_uri)
    signing_key: dict[str, Any] | None = None
    for key in jwks.get("keys", []):
        if isinstance(key, dict) and key.get("kid") == kid:
            signing_key = key
            break
    if signing_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to validate ID token signing key",
        )

    try:
        claims = jwt.decode(
            id_token,
            signing_key,
            algorithms=[alg],
            audience=s.graph_client_id,
            issuer=issuer,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iat": True,
                "verify_exp": True,
                "verify_nbf": True,
            },
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ID token",
        ) from exc

    token_tenant = str(claims.get("tid") or "")
    if token_tenant != s.graph_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID token tenant mismatch",
        )

    token_nonce = str(claims.get("nonce") or "")
    if not token_nonce or token_nonce != expected_nonce:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID token nonce mismatch",
        )

    return claims


def _redirect_auth_unavailable(*, intent: str | None = None) -> RedirectResponse:
    return _build_error_redirect("entra_not_configured", intent=intent)


@router.get("/login")
def microsoft_login(intent: str = Query(default="default")) -> RedirectResponse:
    normalized_intent = _normalize_intent(intent)
    if not _is_entra_configured():
        logger.warning("entra_login_unavailable reason=missing_configuration intent=%s", normalized_intent)
        return _redirect_auth_unavailable(intent=normalized_intent)

    s = get_settings()
    nonce = secrets.token_urlsafe(24)
    state = _sign_state(normalized_intent, nonce)
    params = {
        "client_id": s.graph_client_id,
        "response_type": "code",
        "redirect_uri": s.microsoft_redirect_uri,
        "scope": _SCOPES,
        "response_mode": "query",
        "nonce": nonce,
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
        return _build_error_redirect("entra_denied")

    if not code:
        return _build_error_redirect("missing_authorization_code")

    verified_state = _verify_state(state)
    if verified_state is None:
        return _build_error_redirect("invalid_state")
    verified_intent, expected_nonce = verified_state

    token_data = _exchange_code(code)
    id_token = str(token_data.get("id_token") or "")
    if not id_token:
        return _build_error_redirect("missing_id_token", intent=verified_intent)

    claims = _validate_id_token(id_token, expected_nonce)

    ms_access_token: str = token_data.get("access_token", "")
    if not ms_access_token:
        return _build_error_redirect("missing_access_token", intent=verified_intent)

    userinfo = _fetch_userinfo(ms_access_token)
    email = _extract_email(claims, userinfo)
    if not email:
        return _build_error_redirect("no_email_claim", intent=verified_intent)

    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email)
    if user is None:
        logger.warning("entra_login_no_matching_user email=%s", email)
        return _build_error_redirect("no_account", intent=verified_intent)

    if verified_intent == "founder":
        if str(user.role or "").strip().lower() != "founder":
            logger.warning(
                "entra_founder_denied_role user_id=%s email=%s role=%s",
                user.id,
                email,
                user.role,
            )
            return _build_error_redirect("founder_role_denied", intent=verified_intent)
        if not _founder_claim_policy_satisfied(email=email, claims=claims):
            logger.warning(
                "entra_founder_denied_claims user_id=%s email=%s",
                user.id,
                email,
            )
            return _build_error_redirect("founder_claim_denied", intent=verified_intent)

    jwt_token = create_access_token(str(user.id), str(user.tenant_id), user.role or "")
    logger.info("entra_login_success user_id=%s email=%s", user.id, email)

    post_login_target = (
        s.microsoft_founder_post_login_url
        if verified_intent == "founder"
        else s.microsoft_post_login_url
    )
    response = RedirectResponse(url=post_login_target, status_code=302)
    _set_session_cookie(response, jwt_token)
    return response


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
    response = RedirectResponse(url=url, status_code=302)
    _clear_session_cookie(response)
    return response

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

TELNYX_API = "https://api.telnyx.com/v2"


class TelnyxNotConfigured(RuntimeError):
    pass


class TelnyxApiError(RuntimeError):
    def __init__(self, message: str, status_code: int = 0, body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def _headers(api_key: str) -> dict[str, str]:
    if not api_key:
        raise TelnyxNotConfigured("TELNYX_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _raise_for(resp: requests.Response, context: str) -> None:
    if resp.status_code >= 300:
        raise TelnyxApiError(
            f"{context} failed: HTTP {resp.status_code}",
            status_code=resp.status_code,
            body=resp.text[:400],
        )


# ── Call Control ──────────────────────────────────────────────────────────────


def call_answer(*, api_key: str, call_control_id: str) -> dict[str, Any]:
    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/answer",
        headers=_headers(api_key),
        json={},
        timeout=10,
    )
    _raise_for(r, "call_answer")
    return r.json()


def call_gather_using_audio(
    *,
    api_key: str,
    call_control_id: str,
    audio_url: str,
    minimum_digits: int = 1,
    maximum_digits: int = 1,
    terminating_digit: str = "",
    timeout_millis: int = 8000,
    client_state: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "audio_url": audio_url,
        "minimum_digits": minimum_digits,
        "maximum_digits": maximum_digits,
        "timeout_millis": timeout_millis,
        "inter_digit_timeout_millis": 4000,
        "invalid_audio_url": audio_url,
    }
    if terminating_digit:
        payload["terminating_digit"] = terminating_digit
    if client_state:
        import base64

        payload["client_state"] = base64.b64encode(client_state.encode()).decode()
    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/gather_using_audio",
        headers=_headers(api_key),
        json=payload,
        timeout=10,
    )
    _raise_for(r, "gather_using_audio")
    return r.json()


def call_gather_using_speak(
    *,
    api_key: str,
    call_control_id: str,
    payload: str,
    voice: str = "female",
    language: str = "en-US",
    minimum_digits: int = 1,
    maximum_digits: int = 1,
    terminating_digit: str = "",
    timeout_millis: int = 8000,
    client_state: str = "",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "payload": payload,
        "voice": voice,
        "language": language,
        "minimum_digits": minimum_digits,
        "maximum_digits": maximum_digits,
        "timeout_millis": timeout_millis,
        "inter_digit_timeout_millis": 4000,
    }
    if terminating_digit:
        body["terminating_digit"] = terminating_digit
    if client_state:
        import base64

        body["client_state"] = base64.b64encode(client_state.encode()).decode()

    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/gather_using_speak",
        headers=_headers(api_key),
        json=body,
        timeout=10,
    )
    _raise_for(r, "gather_using_speak")
    return r.json()


def call_playback_start(
    *,
    api_key: str,
    call_control_id: str,
    audio_url: str,
    loop: int = 1,
    client_state: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"audio_url": audio_url, "loop": loop}
    if client_state:
        import base64

        payload["client_state"] = base64.b64encode(client_state.encode()).decode()
    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/playback_start",
        headers=_headers(api_key),
        json=payload,
        timeout=10,
    )
    _raise_for(r, "playback_start")
    return r.json()


def call_speak(
    *,
    api_key: str,
    call_control_id: str,
    payload: str,
    voice: str = "female",
    language: str = "en-US",
    client_state: str = "",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "payload": payload,
        "voice": voice,
        "language": language,
    }
    if client_state:
        import base64

        body["client_state"] = base64.b64encode(client_state.encode()).decode()

    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/speak",
        headers=_headers(api_key),
        json=body,
        timeout=10,
    )
    _raise_for(r, "call_speak")
    return r.json()


def call_transfer(
    *,
    api_key: str,
    call_control_id: str,
    to: str,
    from_: str = "",
    client_state: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"to": to}
    if from_:
        payload["from"] = from_
    if client_state:
        import base64

        payload["client_state"] = base64.b64encode(client_state.encode()).decode()
    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/transfer",
        headers=_headers(api_key),
        json=payload,
        timeout=10,
    )
    _raise_for(r, "call_transfer")
    return r.json()


def call_hangup(*, api_key: str, call_control_id: str) -> dict[str, Any]:
    r = requests.post(
        f"{TELNYX_API}/calls/{call_control_id}/actions/hangup",
        headers=_headers(api_key),
        json={},
        timeout=10,
    )
    _raise_for(r, "call_hangup")
    return r.json()


# ── Messaging ─────────────────────────────────────────────────────────────────


def send_sms(
    *,
    api_key: str,
    from_number: str,
    to_number: str,
    text: str,
    messaging_profile_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "from": from_number,
        "to": to_number,
        "text": text,
    }
    if messaging_profile_id:
        payload["messaging_profile_id"] = messaging_profile_id
    r = requests.post(
        f"{TELNYX_API}/messages",
        headers=_headers(api_key),
        json=payload,
        timeout=20,
    )
    _raise_for(r, "send_sms")
    return r.json()


# ── Media download ────────────────────────────────────────────────────────────


def download_media(*, api_key: str, media_url: str) -> bytes:
    r = requests.get(
        media_url,
        headers=_headers(api_key),
        timeout=60,
        stream=True,
    )
    _raise_for(r, "download_media")
    chunks = []
    for chunk in r.iter_content(chunk_size=65536):
        if chunk:
            chunks.append(chunk)
    return b"".join(chunks)


# ── Outbound Call ─────────────────────────────────────────────────────────────


def initiate_outbound_call(
    *,
    api_key: str,
    to: str,
    from_: str,
    connection_id: str = "",
    webhook_url: str = "",
    client_state: str = "",
) -> dict[str, Any]:
    """Initiate an outbound call via Telnyx Call Control.

    The CNAM caller ID is set at the number level (via CNAM registration
    on the provisioned toll-free number), not per-call.  The `from_` field
    determines which number — and therefore which CNAM entry — is displayed.
    """
    payload: dict[str, Any] = {
        "to": to,
        "from": from_,
    }
    if connection_id:
        payload["connection_id"] = connection_id
    if webhook_url:
        payload["webhook_url"] = webhook_url
    if client_state:
        import base64

        payload["client_state"] = base64.b64encode(client_state.encode()).decode()

    r = requests.post(
        f"{TELNYX_API}/calls",
        headers=_headers(api_key),
        json=payload,
        timeout=15,
    )
    _raise_for(r, "initiate_outbound_call")
    return r.json()


# ── Fax ──────────────────────────────────────────────────────────────────────


def send_fax(
    *,
    api_key: str,
    connection_id: str,
    to: str,
    from_: str,
    media_url: str,
    client_state: str = "",
) -> dict[str, Any]:
    """Send an outbound fax via Telnyx.

    Telnyx expects a `media_url` that it can fetch (HTTPS), so callers typically
    provide a short-lived presigned URL.
    """
    if not connection_id:
        raise TelnyxApiError("send_fax requires connection_id", status_code=422)
    if not media_url:
        raise TelnyxApiError("send_fax requires media_url", status_code=422)

    payload: dict[str, Any] = {
        "connection_id": connection_id,
        "to": to,
        "from": from_,
        "media_url": media_url,
    }
    if client_state:
        import base64

        payload["client_state"] = base64.b64encode(client_state.encode()).decode()

    r = requests.post(
        f"{TELNYX_API}/faxes",
        headers=_headers(api_key),
        json=payload,
        timeout=20,
    )
    _raise_for(r, "send_fax")
    return r.json()


# ── CNAM Management ───────────────────────────────────────────────────────────


def get_cnam_status(*, api_key: str, number_id: str) -> dict[str, Any]:
    """Query CNAM listing status for a provisioned number."""
    r = requests.get(
        f"{TELNYX_API}/phone_numbers/{number_id}",
        headers=_headers(api_key),
        timeout=10,
    )
    _raise_for(r, "get_cnam_status")
    data = r.json().get("data") or {}
    cnam = data.get("cnam_listing") or {}
    return {
        "phone_number": data.get("phone_number"),
        "cnam_listing_enabled": cnam.get("cnam_listing_enabled", False),
        "cnam_listing_caller_name": cnam.get("cnam_listing_caller_name", ""),
        "cnam_listing_details": cnam.get("cnam_listing_details", ""),
    }


def update_cnam(
    *, api_key: str, number_id: str, display_name: str
) -> dict[str, Any]:
    """Register or update CNAM caller ID for a number."""
    if len(display_name) > 15:
        raise TelnyxApiError("CNAM display name must be 15 characters or fewer", status_code=422)
    r = requests.patch(
        f"{TELNYX_API}/phone_numbers/{number_id}",
        headers=_headers(api_key),
        json={
            "cnam_listing": {
                "cnam_listing_enabled": True,
                "cnam_listing_caller_name": display_name,
            }
        },
        timeout=10,
    )
    _raise_for(r, "update_cnam")
    data = r.json().get("data") or {}
    cnam = data.get("cnam_listing") or {}
    return {
        "cnam_listing_enabled": cnam.get("cnam_listing_enabled", False),
        "cnam_listing_caller_name": cnam.get("cnam_listing_caller_name", ""),
        "cnam_listing_details": cnam.get("cnam_listing_details", ""),
    }

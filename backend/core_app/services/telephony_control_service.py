from __future__ import annotations

# ruff: noqa: I001

from collections.abc import Callable
import logging
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelephonyControlConfig:
    mode: str  # asterisk | freeswitch | telnyx
    asterisk_ari_base_url: str
    asterisk_ari_username: str
    asterisk_ari_password: str
    freeswitch_control_url: str


def transfer_call(
    *,
    call_control_id: str,
    to_number: str,
    from_number: str,
    cfg: TelephonyControlConfig,
) -> None:
    mode = (cfg.mode or "telnyx").lower()

    if mode == "asterisk":
        if not cfg.asterisk_ari_base_url:
            raise RuntimeError("ASTERISK_ARI_BASE_URL is not configured")
        # Assumes an internal adapter maps platform call IDs to Asterisk channel IDs.
        url = f"{cfg.asterisk_ari_base_url.rstrip('/')}/fusionems/transfer"
        resp = requests.post(
            url,
            json={
                "call_id": call_control_id,
                "to": to_number,
                "from": from_number,
            },
            auth=(cfg.asterisk_ari_username, cfg.asterisk_ari_password),
            timeout=10,
        )
        resp.raise_for_status()
        return

    if mode == "freeswitch":
        if not cfg.freeswitch_control_url:
            raise RuntimeError("FREESWITCH_CONTROL_URL is not configured")
        url = f"{cfg.freeswitch_control_url.rstrip('/')}/fusionems/transfer"
        resp = requests.post(
            url,
            json={
                "call_id": call_control_id,
                "to": to_number,
                "from": from_number,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return

    # telnyx mode handled by existing telnyx client path in router.
    logger.info("Telephony mode '%s' selected: transfer expected via existing provider path", mode)


def transfer_call_with_fallback(
    *,
    call_control_id: str,
    to_number: str,
    from_number: str,
    cfg: TelephonyControlConfig,
    telnyx_transfer: Callable[[], Any],
) -> str:
    """
    Attempt selected control-plane transfer and gracefully fall back to Telnyx.

    Returns engine outcome: asterisk|freeswitch|telnyx|telnyx_fallback.
    """
    mode = (cfg.mode or "telnyx").lower()
    if mode == "telnyx":
        telnyx_transfer()
        return "telnyx"

    try:
        transfer_call(
            call_control_id=call_control_id,
            to_number=to_number,
            from_number=from_number,
            cfg=cfg,
        )
        return mode
    except Exception as exc:
        logger.warning(
            "telephony_transfer_bridge_failed mode=%s call_control_id=%s error=%s; falling back to telnyx",
            mode,
            call_control_id,
            exc,
        )
        telnyx_transfer()
        return "telnyx_fallback"

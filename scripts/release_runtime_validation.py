#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass

import requests

TARGET_NUMBER = os.getenv("TELNYX_TARGET_NUMBER", "+1-888-365-0144")


def _normalize_e164(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if not digits.startswith("+"):
        digits = f"+{digits}"
    return digits


@dataclass
class CheckResult:
    ok: bool
    detail: str


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required runtime environment variable: {name}")
    return value


def _probe_live_status() -> tuple[dict[str, object], list[CheckResult]]:
    live_status_url = _required_env("LIVE_STATUS_URL")
    bearer_token = _required_env("LIVE_STATUS_BEARER_TOKEN")

    response = requests.get(
        live_status_url,
        headers={"Authorization": f"Bearer {bearer_token}"},
        timeout=20,
    )
    body: dict[str, object] = {}
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:500]}

    checks: list[CheckResult] = [
        CheckResult(response.status_code == 200, f"HTTP {response.status_code}"),
        CheckResult(isinstance(body, dict), "Response body must be JSON object"),
    ]

    if isinstance(body, dict):
        overall_status = str(body.get("overall_status", "unknown"))
        release_blockers = body.get("release_blockers")
        services = body.get("services") if isinstance(body.get("services"), list) else []
        service_map = {
            str(item.get("service")): str(item.get("status"))
            for item in services
            if isinstance(item, dict)
        }

        checks.extend(
            [
                CheckResult(overall_status in {"healthy", "degraded", "blocked", "unknown"}, f"overall_status={overall_status}"),
                CheckResult(service_map.get("backend") == "healthy", f"backend={service_map.get('backend', 'unknown')}"),
                CheckResult(service_map.get("auth") == "healthy", f"auth={service_map.get('auth', 'unknown')}"),
                CheckResult(
                    service_map.get("microsoft_signin") == "healthy",
                    f"microsoft_signin={service_map.get('microsoft_signin', 'unknown')}",
                ),
                CheckResult(
                    isinstance(body.get("release"), dict) and str((body.get("release") or {}).get("version", "")) not in {"", "unknown"},
                    f"release.version={((body.get('release') or {}) if isinstance(body.get('release'), dict) else {}).get('version', 'unknown')}",
                ),
            ]
        )

    return body, checks


def _get_telnyx_number_record(api_key: str, target_number: str) -> tuple[dict[str, object] | None, int]:
    headers = {"Authorization": f"Bearer {api_key}"}
    normalized = _normalize_e164(target_number)
    for query in [normalized, normalized.replace("+", "")]:
        response = requests.get(
            "https://api.telnyx.com/v2/phone_numbers",
            params={"filter[phone_number]": query},
            headers=headers,
            timeout=20,
        )
        if response.status_code >= 300:
            continue
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, list) and data:
            rec = data[0] if isinstance(data[0], dict) else None
            return rec, response.status_code
    return None, 0


def _probe_telnyx(live_status: dict[str, object]) -> tuple[dict[str, object], list[CheckResult]]:
    api_key = _required_env("TELNYX_API_KEY")
    expected_voice_connection_id = os.getenv("TELNYX_EXPECTED_VOICE_CONNECTION_ID", "").strip()
    expected_messaging_profile_id = os.getenv("TELNYX_EXPECTED_MESSAGING_PROFILE_ID", "").strip()
    expected_webhook_url = os.getenv("TELNYX_EXPECTED_WEBHOOK_URL", "").strip()

    record, status_code = _get_telnyx_number_record(api_key, TARGET_NUMBER)
    checks: list[CheckResult] = [
        CheckResult(record is not None, f"phone_number_lookup_status={status_code or 'failed'}"),
    ]

    voice_binding_ok = False
    messaging_binding_ok = False
    webhook_reachable = False
    stale_binding_detected = False

    configured_number = ""
    if isinstance(live_status.get("telnyx"), dict):
        telnyx_live = live_status["telnyx"]
        configured_number = str(telnyx_live.get("configured_number", ""))
        stale_binding_detected = bool(telnyx_live.get("stale_binding_detected"))
        if isinstance(telnyx_live.get("webhook_health"), bool):
            webhook_reachable = bool(telnyx_live.get("webhook_health"))

    if record is not None:
        connection_id = str(record.get("connection_id") or "")
        messaging_profile_id = str(record.get("messaging_profile_id") or record.get("messaging_profile_id_number_pool_setting") or "")
        voice_binding_ok = bool(connection_id) and (
            not expected_voice_connection_id or connection_id == expected_voice_connection_id
        )
        messaging_binding_ok = bool(messaging_profile_id) and (
            not expected_messaging_profile_id or messaging_profile_id == expected_messaging_profile_id
        )

    if expected_webhook_url:
        try:
            r = requests.get(expected_webhook_url, timeout=10)
            webhook_reachable = r.status_code < 500
        except Exception:
            webhook_reachable = False

    checks.extend(
        [
            CheckResult(_normalize_e164(configured_number) == _normalize_e164(TARGET_NUMBER), f"configured_number={configured_number or 'missing'}"),
            CheckResult(voice_binding_ok, "voice binding verified"),
            CheckResult(messaging_binding_ok, "messaging profile verified"),
            CheckResult(webhook_reachable, "webhook reachability verified"),
            CheckResult(not stale_binding_detected, f"stale_binding_detected={stale_binding_detected}"),
        ]
    )

    return {
        "number": TARGET_NUMBER,
        "lookup_status": status_code,
        "record_found": record is not None,
        "voice_binding_ok": voice_binding_ok,
        "messaging_binding_ok": messaging_binding_ok,
        "webhook_reachable": webhook_reachable,
        "stale_binding_detected": stale_binding_detected,
    }, checks


def main() -> int:
    try:
        live_status, live_checks = _probe_live_status()
        telnyx_detail, telnyx_checks = _probe_telnyx(live_status)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1

    all_checks = live_checks + telnyx_checks
    failures = [c.detail for c in all_checks if not c.ok]

    output = {
        "live_status": live_status,
        "telnyx_runtime": telnyx_detail,
        "checks": [{"ok": c.ok, "detail": c.detail} for c in all_checks],
        "healthy": len(failures) == 0,
        "failures": failures,
    }
    print(json.dumps(output, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

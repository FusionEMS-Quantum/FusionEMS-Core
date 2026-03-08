#!/usr/bin/env python3
"""Provision a Telnyx toll-free number and register CNAM for FusionEMS Quantum.

Called as a Terraform external data source.  Reads JSON on stdin, writes JSON on stdout.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, UTC
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _resp_json(req: Request) -> dict:
    with urlopen(req, timeout=30) as r:  # nosec B310
        return json.loads(r.read().decode("utf-8"))


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _register_cnam(api_key: str, number_id: str, cnam_display_name: str) -> str:
    """Submit CNAM registration via Telnyx Number Update API.

    Returns the CNAM listing status from the API response.
    Telnyx propagates CNAM to the national LIDB database within 24-48h.
    """
    if not number_id or number_id in ("existing", "unknown"):
        return "skipped_no_number_id"

    update_body = {
        "cnam_listing": {
            "cnam_listing_enabled": True,
            "cnam_listing_caller_name": cnam_display_name,
        },
    }
    update_req = Request(
        f"https://api.telnyx.com/v2/phone_numbers/{number_id}",
        data=json.dumps(update_body).encode("utf-8"),
        headers=_headers(api_key),
        method="PATCH",
    )
    try:
        resp = _resp_json(update_req)
        cnam_data = (resp.get("data") or {}).get("cnam_listing") or {}
        return cnam_data.get("cnam_listing_details") or "submitted"
    except Exception as exc:
        return f"cnam_registration_error: {exc}"


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    api_key = (payload.get("telnyx_api_key") or "").strip()
    existing = (payload.get("existing_phone_e164") or "").strip()
    desired_prefix = (payload.get("desired_tollfree_prefix") or "800").strip()
    cnam_display_name = (payload.get("cnam_display_name") or "FusionEMS Quantum").strip()

    now = datetime.now(UTC).isoformat()

    if existing:
        print(
            json.dumps(
                {
                    "phone_e164": existing,
                    "number_id": "existing",
                    "purchased_at": now,
                    "cnam_display_name": cnam_display_name,
                    "cnam_status": "skipped_existing_number",
                }
            )
        )
        return

    if not api_key:
        raise SystemExit("Missing telnyx_api_key in module input")

    # 1) search available toll-free number
    q = urlencode(
        {
            "filter[toll_free]": "true",
            "filter[best_effort]": "true",
            "filter[limit]": "1",
            "filter[phone_number][starts_with]": desired_prefix,
        }
    )
    search_req = Request(
        f"https://api.telnyx.com/v2/available_phone_numbers?{q}",
        headers=_headers(api_key),
        method="GET",
    )
    search = _resp_json(search_req)
    numbers = search.get("data") or []
    if not numbers:
        raise SystemExit("No toll-free numbers available from Telnyx for requested prefix")

    selected = numbers[0]
    phone_number = selected.get("phone_number")
    if not phone_number:
        raise SystemExit("Telnyx available_number payload missing phone_number")

    # 2) create number order
    order_body = {
        "phone_numbers": [{"phone_number": phone_number}],
    }
    order_req = Request(
        "https://api.telnyx.com/v2/number_orders",
        data=json.dumps(order_body).encode("utf-8"),
        headers=_headers(api_key),
        method="POST",
    )
    order = _resp_json(order_req)
    order_data = order.get("data") or {}

    number_id = ""
    nums = order_data.get("phone_numbers") or []
    if nums:
        number_id = nums[0].get("id") or ""

    if not number_id:
        number_id = selected.get("id") or ""

    # 3) register CNAM caller ID — patients see "FusionEMS Quantum" on outbound calls
    cnam_status = _register_cnam(api_key, number_id, cnam_display_name)

    print(
        json.dumps(
            {
                "phone_e164": phone_number,
                "number_id": number_id or "unknown",
                "purchased_at": now,
                "cnam_display_name": cnam_display_name,
                "cnam_status": cnam_status,
            }
        )
    )


if __name__ == "__main__":
    main()

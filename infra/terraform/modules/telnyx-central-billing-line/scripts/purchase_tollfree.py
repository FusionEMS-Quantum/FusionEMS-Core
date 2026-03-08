#!/usr/bin/env python3
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


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    api_key = (payload.get("telnyx_api_key") or "").strip()
    existing = (payload.get("existing_phone_e164") or "").strip()
    desired_prefix = (payload.get("desired_tollfree_prefix") or "800").strip()

    now = datetime.now(UTC).isoformat()

    if existing:
        print(
            json.dumps(
                {
                    "phone_e164": existing,
                    "number_id": "existing",
                    "purchased_at": now,
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

    print(
        json.dumps(
            {
                "phone_e164": phone_number,
                "number_id": number_id or "unknown",
                "purchased_at": now,
            }
        )
    )


if __name__ == "__main__":
    main()

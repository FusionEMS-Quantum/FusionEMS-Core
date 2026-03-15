"""Idempotent Stripe catalog sync.

Creates/finds Stripe Products and Prices for every selectable plan, tier, and
add-on in the pricing catalog, then stores the resulting Price IDs in SSM under
/fusionems/{stage}/stripe/prices/{lookup_key}.

Run as a one-off ECS task on every production deploy before traffic shifts:
    python -m core_app.pricing.stripe_sync --stage prod
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Any

from core_app.pricing.catalog import ADDONS, BILLING_TIERS, PLANS, SCHEDULING_TIERS

logger = logging.getLogger(__name__)


def _product_key_for_plan(plan_code: str) -> str:
    return f"{plan_code}_V1"


def _product_key_for_addon(addon_code: str) -> str:
    if addon_code == "BILLING_AUTOMATION":
        return "BILLING_AUTOMATION_V1"
    return f"{addon_code}_V1"


def _catalog_products() -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []

    products.append({"key": _product_key_for_plan("SCHEDULING_ONLY"), "name": "FusionEMS Scheduling Only"})

    for plan in PLANS.values():
        if plan.code == "SCHEDULING_ONLY":
            continue
        products.append(
            {
                "key": _product_key_for_plan(plan.code),
                "name": f"FusionEMS {plan.label}",
            }
        )

    for addon in ADDONS.values():
        products.append(
            {
                "key": _product_key_for_addon(addon.code),
                "name": f"FusionEMS {addon.label}",
            }
        )

    if any(tier.mode == "THIRD_PARTY_EXPORT" for tier in BILLING_TIERS.values()):
        products.append(
            {
                "key": "THIRD_PARTY_EXPORT_V1",
                "name": "FusionEMS Internal / Third-Party Billing",
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for product in products:
        if product["key"] in seen:
            continue
        seen.add(product["key"])
        deduped.append(product)
    return deduped


def _catalog_prices() -> list[dict[str, Any]]:
    prices: list[dict[str, Any]] = []

    for tier in SCHEDULING_TIERS.values():
        prices.append(
            {
                "lookup_key": tier.lookup_key,
                "product_key": _product_key_for_plan("SCHEDULING_ONLY"),
                "unit_amount": tier.monthly_cents,
                "metered": False,
            }
        )

    for plan in PLANS.values():
        if not plan.lookup_key or plan.monthly_cents is None:
            continue
        prices.append(
            {
                "lookup_key": plan.lookup_key,
                "product_key": _product_key_for_plan(plan.code),
                "unit_amount": plan.monthly_cents,
                "metered": False,
            }
        )

    for addon in ADDONS.values():
        if addon.uses_billing_tier or not addon.lookup_key:
            continue
        prices.append(
            {
                "lookup_key": addon.lookup_key,
                "product_key": _product_key_for_addon(addon.code),
                "unit_amount": addon.monthly_cents,
                "metered": False,
            }
        )

    for billing_tier in BILLING_TIERS.values():
        product_key = (
            "THIRD_PARTY_EXPORT_V1"
            if billing_tier.mode == "THIRD_PARTY_EXPORT"
            else _product_key_for_addon("BILLING_AUTOMATION")
        )
        prices.extend(
            [
                {
                    "lookup_key": billing_tier.base_lookup_key,
                    "product_key": product_key,
                    "unit_amount": billing_tier.base_monthly_cents,
                    "metered": False,
                },
                {
                    "lookup_key": billing_tier.per_claim_lookup_key,
                    "product_key": product_key,
                    "unit_amount": billing_tier.per_claim_cents,
                    "metered": True,
                },
            ]
        )

    return prices


def sync_catalog(
    stage: str, stripe_secret_key: str, aws_region: str = "us-east-1"
) -> dict[str, str]:
    """Upsert all Stripe Products and Prices; store price IDs in SSM.

    Returns a mapping of lookup_key → Stripe Price ID.
    """
    import boto3
    import stripe as stripe_lib

    stripe_lib.api_key = stripe_secret_key
    ssm = boto3.client("ssm", region_name=aws_region)
    ssm_prefix = f"/fusionems/{stage}/stripe/prices"

    product_ids = _ensure_products(stripe_lib, stage)
    price_ids = _ensure_prices(stripe_lib, ssm, ssm_prefix, stage, product_ids)

    logger.info(
        "stripe_sync_complete stage=%s products=%d prices=%d",
        stage,
        len(product_ids),
        len(price_ids),
    )
    return price_ids


def _ensure_products(stripe_lib: Any, stage: str) -> dict[str, str]:
    product_ids: dict[str, str] = {}
    for p in _catalog_products():
        result = stripe_lib.Product.search(
            query=f"metadata['product_key']:'{p['key']}' AND metadata['stage']:'{stage}'"
        )
        if result.data:
            product = result.data[0]
            logger.info("product_exists key=%s id=%s", p["key"], product.id)
        else:
            product = stripe_lib.Product.create(
                name=p["name"],
                metadata={"product_key": p["key"], "stage": stage},
            )
            logger.info("product_created key=%s id=%s", p["key"], product.id)
        product_ids[p["key"]] = product.id
    return product_ids


def _ensure_prices(
    stripe_lib: Any,
    ssm: Any,
    ssm_prefix: str,
    stage: str,
    product_ids: dict[str, str],
) -> dict[str, str]:
    price_ids: dict[str, str] = {}
    for pr in _catalog_prices():
        existing = stripe_lib.Price.list(lookup_keys=[pr["lookup_key"]], limit=1)
        if existing.data:
            price = existing.data[0]
            logger.info("price_exists lookup_key=%s id=%s", pr["lookup_key"], price.id)
        else:
            recurring: dict[str, Any] = {"interval": "month"}
            if pr["metered"]:
                recurring["usage_type"] = "metered"
            price = stripe_lib.Price.create(
                product=product_ids[pr["product_key"]],
                unit_amount=pr["unit_amount"],
                currency="usd",
                recurring=recurring,
                lookup_key=pr["lookup_key"],
                metadata={"stage": stage},
            )
            logger.info("price_created lookup_key=%s id=%s", pr["lookup_key"], price.id)
        price_ids[pr["lookup_key"]] = price.id
        ssm.put_parameter(
            Name=f"{ssm_prefix}/{pr['lookup_key']}",
            Value=price.id,
            Type="String",
            Overwrite=True,
        )
    return price_ids


def _resolve_stripe_key(stripe_secret_key: str, stripe_secret_arn: str, aws_region: str) -> str:
    if stripe_secret_key:
        return stripe_secret_key
    if stripe_secret_arn:
        import boto3

        sm = boto3.client("secretsmanager", region_name=aws_region)
        secret = json.loads(sm.get_secret_value(SecretId=stripe_secret_arn)["SecretString"])
        return secret.get("secret_key") or secret.get("STRIPE_SECRET_KEY", "")
    raise RuntimeError("STRIPE_SECRET_KEY or STRIPE_SECRET_ARN must be set")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Sync FusionEMS pricing catalog to Stripe")
    parser.add_argument("--stage", default=os.environ.get("STAGE", "dev"))
    parser.add_argument("--aws-region", default=os.environ.get("AWS_REGION", "us-east-1"))
    args = parser.parse_args()

    stripe_key = _resolve_stripe_key(
        stripe_secret_key=os.environ.get("STRIPE_SECRET_KEY", ""),
        stripe_secret_arn=os.environ.get("STRIPE_SECRET_ARN", ""),
        aws_region=args.aws_region,
    )

    price_ids = sync_catalog(
        stage=args.stage,
        stripe_secret_key=stripe_key,
        aws_region=args.aws_region,
    )

    print(json.dumps({"status": "ok", "price_ids": price_ids}, indent=2))


if __name__ == "__main__":
    main()

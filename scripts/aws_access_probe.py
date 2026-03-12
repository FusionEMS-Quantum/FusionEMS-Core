#!/usr/bin/env python3
"""Probe AWS access for a given profile.

This script validates:
1) STS caller identity
2) Optional read check against Terraform state bucket
"""

from __future__ import annotations

import argparse
import json
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def _check_state_bucket(session: boto3.session.Session, bucket: str) -> dict[str, Any]:
    s3 = session.client("s3")
    key = "fusionems/prod/terraform.tfstate"
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return {
            "bucket": bucket,
            "key": key,
            "status": "ok",
            "detail": "head_object succeeded",
        }
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        return {
            "bucket": bucket,
            "key": key,
            "status": "error",
            "detail": f"ClientError: {code}",
        }
    except BotoCoreError as exc:
        return {
            "bucket": bucket,
            "key": key,
            "status": "error",
            "detail": f"BotoCoreError: {type(exc).__name__}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AWS profile access.")
    parser.add_argument("--profile", default="fusion", help="AWS profile name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument(
        "--state-bucket",
        default="fusionems-terraform-state-prod",
        help="Terraform state bucket to probe",
    )
    args = parser.parse_args()

    try:
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "status": "auth_failed",
                    "profile": args.profile,
                    "region": args.region,
                    "error": str(exc),
                },
                indent=2,
            )
        )
        return 1

    state_check = _check_state_bucket(session, args.state_bucket)
    out = {
        "status": "auth_ok",
        "profile": args.profile,
        "region": args.region,
        "identity": {
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "user_id": identity.get("UserId"),
        },
        "state_bucket_probe": state_check,
    }
    print(json.dumps(out, indent=2))
    return 0 if state_check.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())

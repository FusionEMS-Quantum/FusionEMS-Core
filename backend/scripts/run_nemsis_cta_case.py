from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
import uuid
from collections.abc import Callable, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _load_env_file(env_path: Path) -> None:
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_env_file(_BACKEND_ROOT / ".env")

_PENDING_STATUSES = {"submitted", "pending"}
_TERMINAL_STATUSES = {"passed", "passed_with_warnings", "failed"}
_DETAIL_KEYS_TO_STRIP = {
    "xml_b64",
    "cta_reports",
    "query_limit_request_xml",
    "query_limit_response_xml",
    "submit_request_xml",
    "submit_response_xml",
    "retrieve_request_xml",
    "retrieve_response_xml",
}


def _uuid_arg(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid UUID: {value}") from exc


def _positive_int_arg(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than zero")
    return parsed


def _non_negative_float_arg(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("Value must be greater than or equal to zero")
    return parsed


def _tenant_default() -> str | None:
    return os.getenv("FUSIONEMS_TENANT_ID") or None


def _user_default() -> str | None:
    return os.getenv("FUSIONEMS_USER_ID") or None


def _role_default() -> str:
    return os.getenv("FUSIONEMS_ROLE", "founder")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run or inspect NEMSIS CTA vendor cases from the backend shell.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-cases", help="List available CTA vendor case ids.")

    run_parser = subparsers.add_parser("run-case", help="Generate, validate, submit, and optionally poll a CTA case.")
    _add_actor_args(run_parser)
    run_parser.add_argument(
        "--case-id",
        default="2025-DEM-1-FullSet_v351",
        help="CTA vendor case id to execute.",
    )
    run_parser.add_argument("--endpoint-url", default="", help="Override CTA SOAP endpoint.")
    run_parser.add_argument("--username", default="", help="Override CTA username.")
    run_parser.add_argument("--password", default="", help="Override CTA password.")
    run_parser.add_argument("--organization", default="", help="Override CTA organization.")
    run_parser.add_argument(
        "--additional-info",
        default="",
        help="Optional CTA additionalInfo value. Defaults to the case id.",
    )
    run_parser.add_argument(
        "--wait",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Poll RetrieveStatus until the run reaches a terminal CTA state.",
    )
    run_parser.add_argument(
        "--poll-interval-seconds",
        type=_non_negative_float_arg,
        default=10.0,
        help="Seconds between RetrieveStatus polls when --wait is enabled.",
    )
    run_parser.add_argument(
        "--max-polls",
        type=_positive_int_arg,
        default=18,
        help="Maximum RetrieveStatus polls when --wait is enabled.",
    )
    run_parser.add_argument(
        "--xml-out",
        default="",
        help="Optional path to write the generated CTA XML payload.",
    )
    run_parser.add_argument(
        "--include-details",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Include large request/response XML blobs in the JSON output.",
    )
    run_parser.add_argument(
        "--stateless",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run CTA generation/submission without persisting to the application database.",
    )
    run_parser.add_argument(
        "--reference-dem-xml",
        default="",
        help="Optional DEM XML file to use when stateless EMS cases require DEMDataSet placeholder resolution.",
    )

    check_parser = subparsers.add_parser("check-status", help="Poll RetrieveStatus for an existing CTA run id.")
    _add_actor_args(check_parser)
    check_parser.add_argument("--run-id", required=True, help="Existing CTA run id from nemsis_export_jobs.")
    check_parser.add_argument("--endpoint-url", default="", help="Override CTA SOAP endpoint.")
    check_parser.add_argument("--username", default="", help="Override CTA username.")
    check_parser.add_argument("--password", default="", help="Override CTA password.")
    check_parser.add_argument("--organization", default="", help="Override CTA organization.")
    check_parser.add_argument(
        "--additional-info",
        default="",
        help="Optional CTA additionalInfo override.",
    )
    check_parser.add_argument(
        "--include-details",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Include large request/response XML blobs in the JSON output.",
    )

    return parser


def _add_actor_args(parser: argparse.ArgumentParser) -> None:
    tenant_default = _tenant_default()
    user_default = _user_default()
    parser.add_argument(
        "--tenant-id",
        type=_uuid_arg,
        default=tenant_default,
        required=tenant_default is None,
        help="Tenant UUID used for RLS and persistence. Can also come from FUSIONEMS_TENANT_ID.",
    )
    parser.add_argument(
        "--user-id",
        type=_uuid_arg,
        default=user_default,
        required=user_default is None,
        help="Actor user UUID stored on CTA run records. Can also come from FUSIONEMS_USER_ID.",
    )
    parser.add_argument(
        "--role",
        default=_role_default(),
        help="Actor role label for the synthetic CurrentUser context.",
    )


def _prepare_db_session(db: Any, tenant_id: uuid.UUID) -> None:
    db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)})


def _build_service(db: Any) -> Any:
    from core_app.nemsis.cta_service import CTATestRunService
    from core_app.services.domination_service import DominationService
    from core_app.services.event_publisher import get_event_publisher

    return CTATestRunService(db, DominationService(db, get_event_publisher()))


def _build_current_user(args: argparse.Namespace) -> Any:
    from core_app.schemas.auth import CurrentUser

    return CurrentUser(user_id=args.user_id, tenant_id=args.tenant_id, role=args.role)


def _build_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if getattr(args, "case_id", ""):
        payload["case_id"] = args.case_id
    if getattr(args, "endpoint_url", ""):
        payload["endpoint_url"] = args.endpoint_url
    credentials = {
        "username": getattr(args, "username", ""),
        "password": getattr(args, "password", ""),
        "organization": getattr(args, "organization", ""),
    }
    filtered_credentials = {key: value for key, value in credentials.items() if value}
    if filtered_credentials:
        payload["credentials"] = filtered_credentials
    if getattr(args, "additional_info", ""):
        payload["additional_info"] = args.additional_info
    return payload


def _trim_result_for_output(result: dict[str, Any], *, include_details: bool) -> dict[str, Any]:
    trimmed = deepcopy(result)
    details = trimmed.get("details")
    if include_details or not isinstance(details, dict):
        return trimmed
    for key in _DETAIL_KEYS_TO_STRIP:
        details.pop(key, None)
    return trimmed


def _write_xml_output(result: dict[str, Any], output_path: str) -> None:
    details = result.get("details")
    if not isinstance(details, dict):
        raise RuntimeError("CTA result does not contain detail payloads.")
    xml_b64 = details.get("xml_b64")
    if not isinstance(xml_b64, str) or not xml_b64:
        raise RuntimeError("CTA result does not include generated XML bytes.")
    xml_bytes = base64.b64decode(xml_b64)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(xml_bytes)


async def _wait_for_terminal_status(
    *,
    service: Any,
    run_id: str,
    payload: dict[str, Any],
    current: Any,
    correlation_id: str | None,
    poll_interval_seconds: float,
    max_polls: int,
    initial_result: dict[str, Any],
    sleep_func: Callable[[float], Any] = asyncio.sleep,
) -> dict[str, Any]:
    current_result = initial_result
    for _ in range(max_polls):
        await sleep_func(poll_interval_seconds)
        current_result = await service.check_status(
            run_id=run_id,
            payload=payload,
            current=current,
            correlation_id=correlation_id,
        )
        if current_result.get("status") in _TERMINAL_STATUSES:
            return current_result
    return current_result


async def _run_case_command(args: argparse.Namespace) -> dict[str, Any]:
    from core_app.db.session import get_db_session_ctx

    current = _build_current_user(args)
    payload = _build_payload(args)
    correlation_id = f"cli-cta-run-{uuid.uuid4()}"
    with get_db_session_ctx() as db:
        _prepare_db_session(db, current.tenant_id)
        service = _build_service(db)
        result = await service.run_case(payload=payload, current=current, correlation_id=correlation_id)
        if args.wait and result.get("status") in _PENDING_STATUSES and result.get("id"):
            result = await _wait_for_terminal_status(
                service=service,
                run_id=str(result["id"]),
                payload=payload,
                current=current,
                correlation_id=correlation_id,
                poll_interval_seconds=args.poll_interval_seconds,
                max_polls=args.max_polls,
                initial_result=result,
            )
        return result


def _resolve_execution_credentials(payload: dict[str, Any]) -> dict[str, str]:
    from core_app.core.config import get_settings

    settings = get_settings()
    raw_credentials: dict[str, Any] = {}
    credentials_obj = payload.get("credentials")
    if isinstance(credentials_obj, dict):
        raw_credentials = credentials_obj
    username = str(raw_credentials.get("username") or settings.nemsis_cta_username or "").strip()
    password = str(raw_credentials.get("password") or settings.nemsis_cta_password or "").strip()
    organization = str(raw_credentials.get("organization") or settings.nemsis_cta_organization or "").strip()
    endpoint_url = str(payload.get("endpoint_url") or settings.nemsis_cta_endpoint or "").strip()
    if not username or not password or not organization:
        raise RuntimeError("CTA username, password, and organization are required before submission.")
    if not endpoint_url:
        raise RuntimeError("CTA endpoint URL is required before submission.")
    return {
        "username": username,
        "password": password,
        "organization": organization,
        "endpoint_url": endpoint_url,
    }


async def _run_case_stateless_command(args: argparse.Namespace) -> dict[str, Any]:
    from core_app.nemsis.cta_cases import generate_cta_case_xml, get_cta_case
    from core_app.nemsis.cta_soap_client import (
        CTACredentials,
        NEMSISCTASoapClient,
        normalize_cta_state,
        translate_cta_code,
    )
    from core_app.nemsis.validator import NEMSISValidator

    payload = _build_payload(args)
    case = get_cta_case(str(payload.get("case_id", "")))
    if case.dataset_type == "EMS" and not args.reference_dem_xml:
        raise RuntimeError(
            "Stateless EMS runs require --reference-dem-xml so DEMDataSet placeholders can be resolved."
        )

    reference_dem_xml = Path(args.reference_dem_xml).read_bytes() if args.reference_dem_xml else None
    artifact = generate_cta_case_xml(case, reference_dem_xml=reference_dem_xml)
    validation = NEMSISValidator().validate_xml_bytes(artifact.xml_bytes, state_code="FL")
    blocking_issues = [issue.to_dict() for issue in validation.issues if issue.severity == "error"]
    unresolved = list(artifact.unresolved_placeholders)
    credentials = _resolve_execution_credentials(payload)

    result: dict[str, Any] = {
        "id": None,
        "mode": "stateless",
        "case_id": case.case_id,
        "dataset_type": case.dataset_type,
        "status": "validated",
        "plain_summary": "Ready for CTA submission.",
        "request_handle": None,
        "details": {
            "validation": validation.to_dict(),
            "warnings": list(artifact.warnings),
            "unresolved_placeholders": unresolved,
            "xml_b64": base64.b64encode(artifact.xml_bytes).decode("utf-8"),
            "xml_size_bytes": len(artifact.xml_bytes),
            "xml_sha256": artifact.xml_sha256,
            "resolved_test_key": artifact.resolved_test_key,
        },
    }
    if unresolved:
        result["status"] = "failed"
        result["plain_summary"] = "Failed before submission: vendor placeholders are still unresolved."
        return result
    if blocking_issues:
        result["status"] = "failed"
        result["plain_summary"] = "Failed before submission: local validation found blocking issues."
        result["details"]["blocking_issues"] = blocking_issues
        return result

    client = NEMSISCTASoapClient(endpoint_url=credentials["endpoint_url"])
    auth = CTACredentials(
        username=credentials["username"],
        password=credentials["password"],
        organization=credentials["organization"],
    )
    limit_result = await client.query_limit(auth)
    result["details"]["query_limit_request_xml"] = limit_result.sanitized_request_xml
    result["details"]["query_limit_response_xml"] = limit_result.raw_response_xml
    result["details"]["query_limit_kb"] = limit_result.limit_kb
    if limit_result.limit_kb is not None and limit_result.limit_kb > 0 and len(artifact.xml_bytes) > limit_result.limit_kb * 1024:
        result["status"] = "failed"
        result["plain_summary"] = "Failed before submission: payload exceeds CTA size limit."
        return result

    submit_result = await client.submit_data(
        auth,
        xml_bytes=artifact.xml_bytes,
        request_data_schema=case.request_data_schema,
        schema_version=case.schema_version,
        additional_info=str(payload.get("additional_info") or case.case_id),
    )
    result["request_handle"] = submit_result.request_handle
    result["details"]["submit_request_xml"] = submit_result.sanitized_request_xml
    result["details"]["submit_response_xml"] = submit_result.raw_response_xml
    result["details"]["submit_status_code"] = submit_result.status_code
    result["status"] = normalize_cta_state(submit_result.status_code)
    if result["status"] == "pending" and submit_result.request_handle:
        result["status"] = "submitted"
    result["plain_summary"] = translate_cta_code(submit_result.status_code)

    if args.wait and result.get("status") in _PENDING_STATUSES and submit_result.request_handle:
        current_result = result
        for _ in range(args.max_polls):
            await asyncio.sleep(args.poll_interval_seconds)
            retrieve_result = await client.retrieve_status(
                auth,
                request_handle=submit_result.request_handle,
                original_request_type="SubmitData",
                additional_info=str(payload.get("additional_info") or case.case_id),
            )
            current_result = {
                **current_result,
                "status": normalize_cta_state(retrieve_result.status_code),
                "plain_summary": translate_cta_code(retrieve_result.status_code),
                "details": {
                    **current_result["details"],
                    "retrieve_status_code": retrieve_result.status_code,
                    "retrieve_request_xml": retrieve_result.sanitized_request_xml,
                    "retrieve_response_xml": retrieve_result.raw_response_xml,
                    "cta_reports": retrieve_result.reports,
                },
            }
            if current_result["status"] in _TERMINAL_STATUSES:
                return current_result
        return current_result

    return result


async def _check_status_command(args: argparse.Namespace) -> dict[str, Any]:
    from core_app.db.session import get_db_session_ctx

    current = _build_current_user(args)
    payload = _build_payload(args)
    correlation_id = f"cli-cta-check-{uuid.uuid4()}"
    with get_db_session_ctx() as db:
        _prepare_db_session(db, current.tenant_id)
        service = _build_service(db)
        return await service.check_status(
            run_id=args.run_id,
            payload=payload,
            current=current,
            correlation_id=correlation_id,
        )


def _list_cases_command() -> dict[str, Any]:
    from core_app.nemsis.cta_cases import list_cta_cases

    return {
        "cases": [
            {
                "case_id": case.case_id,
                "dataset_type": case.dataset_type,
                "description": case.description,
                "expected_result": case.expected_result,
                "request_data_schema": case.request_data_schema,
            }
            for case in list_cta_cases()
        ]
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list-cases":
            result = _list_cases_command()
        elif args.command == "run-case":
            result = asyncio.run(_run_case_stateless_command(args) if args.stateless else _run_case_command(args))
        elif args.command == "check-status":
            result = asyncio.run(_check_status_command(args))
        else:
            parser.error(f"Unsupported command: {args.command}")
            return 2
    except HTTPException as exc:
        print(json.dumps({"error": exc.detail, "status_code": exc.status_code}, indent=2), file=sys.stderr)
        return 2
    except KeyError as exc:
        print(json.dumps({"error": f"Unknown CTA case: {exc.args[0]}"}, indent=2), file=sys.stderr)
        return 2
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    if getattr(args, "xml_out", ""):
        _write_xml_output(result, args.xml_out)

    include_details = bool(getattr(args, "include_details", False))
    print(json.dumps(_trim_result_for_output(result, include_details=include_details), indent=2, sort_keys=True))

    if result.get("status") == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

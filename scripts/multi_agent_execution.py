#!/usr/bin/env python3
"""FusionEMS multi-agent execution orchestrator.

Runs phase-gated execution lanes aligned to executive production directives:
- Agent 01 (GPT-5.4): Master Orchestrator / release authority
- Agent 02 (GPT-5-Codex): Platform Core
- Agent 03 (Claude Opus): Frontend Command Surface
- Agent 04 (GPT-5.4): Authentication & Access Control
- Agent 05 (GPT-5-Codex): Data & Persistence
- Agent 06 (GPT-5-Codex): NEMSIS/NERIS Interoperability
- Agent 07 (GPT-5-Codex): AWS Infrastructure & Terraform
- Agent 08 (GPT-5.4): Security / Compliance / Audit
- Agent 09 (Claude Opus): Observability / Reliability / Operations
- Agent 10 (Gemini 2.5 Pro): QA / Validation / Deployment Gates

Output:
- artifacts/multi_agent_execution_report.json
- artifacts/multi-agent-logs/*.log
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime as dt
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
LOG_DIR = ARTIFACTS_DIR / "multi-agent-logs"
DEFAULT_REPORT_PATH = ARTIFACTS_DIR / "multi_agent_execution_report.json"


@dataclasses.dataclass(slots=True, frozen=True)
class CommandSpec:
    name: str
    shell_command: str
    required: bool = True


@dataclasses.dataclass(slots=True, frozen=True)
class AgentLane:
    lane_id: str
    agent_label: str
    model: str
    purpose: str
    commands: tuple[CommandSpec, ...]


@dataclasses.dataclass(slots=True)
class CommandResult:
    name: str
    command: str
    exit_code: int
    duration_seconds: float
    required: bool


@dataclasses.dataclass(slots=True)
class LaneResult:
    lane_id: str
    agent_label: str
    model: str
    purpose: str
    status: str
    started_at_utc: str
    finished_at_utc: str
    duration_seconds: float
    log_file: str
    commands: list[CommandResult]


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso(ts: dt.datetime) -> str:
    return ts.isoformat()


def _shell_join(parts: Sequence[str]) -> str:
    return " ".join(shlex.quote(p) for p in parts)


def _command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _python_cmd(module_or_script: str, *, is_module: bool = True) -> str:
    py = shlex.quote(sys.executable)
    if is_module:
        return f"{py} -m {module_or_script}"
    return f"{py} {shlex.quote(module_or_script)}"


def _is_ci() -> bool:
    return os.getenv("CI", "").strip().lower() == "true"


def _external_or_fallback_command(
    *, env_name: str, fallback_name: str, fallback_command: str
) -> CommandSpec:
    external = os.getenv(env_name, "").strip()
    if external:
        return CommandSpec(name=f"external:{env_name}", shell_command=external, required=False)
    return CommandSpec(name=fallback_name, shell_command=fallback_command, required=False)


def _build_validate_lanes() -> tuple[AgentLane, ...]:
    checkov_command = (
        "checkov -d infra/terraform --config-file checkov.yml --quiet"
        if _command_exists("checkov")
        else "echo 'checkov not installed; skipping non-required check'"
    )

    return (
        AgentLane(
            lane_id="agent-02-platform-core",
            agent_label="Platform Core Agent",
            model="gpt-5-codex",
            purpose="Backend domain logic, API integrity, critical regression confidence",
            commands=(
                CommandSpec(
                    name="route-matrix-gate",
                    shell_command=_python_cmd("scripts/ci_gate_route_matrix.py", is_module=False),
                ),
                CommandSpec(
                    name="backend-critical-regression",
                    shell_command=(
                        "cd backend && "
                        + _shell_join(
                            [
                                sys.executable,
                                "-m",
                                "pytest",
                                "tests/test_billing_directive_gap.py",
                                "tests/test_compliance_command.py",
                                "tests/test_founder_command_domain_service.py",
                                "tests/test_founder_integration_command_router.py",
                                "tests/test_margin_risk_analytics.py",
                                "-q",
                            ]
                        )
                    ),
                ),
            ),
        ),
        AgentLane(
            lane_id="agent-03-frontend-command-surface",
            agent_label="Frontend Command Surface Agent",
            model="claude-opus",
            purpose="Frontend command-surface build correctness and runtime safety",
            commands=(
                CommandSpec(
                    name="frontend-no-crash-fallbacks",
                    shell_command=_python_cmd(
                        "scripts/ci_gate_no_frontend_crash_fallbacks.py", is_module=False
                    ),
                ),
                CommandSpec(
                    name="frontend-typecheck",
                    shell_command="cd frontend && npm run clean:next && npx tsc --noEmit",
                ),
                CommandSpec(
                    name="frontend-build",
                    shell_command="cd frontend && npm run build",
                    required=_is_ci(),
                ),
            ),
        ),
        AgentLane(
            lane_id="agent-04-auth-access-control",
            agent_label="Authentication and Access Control Agent",
            model="gpt-5.4",
            purpose="Auth surface integrity, production fail-closed validation",
            commands=(
                CommandSpec(
                    name="auth-surface-validation",
                    shell_command=_python_cmd("scripts/validate_auth_surface.py", is_module=False),
                ),
            ),
        ),
        AgentLane(
            lane_id="agent-05-data-persistence",
            agent_label="Data and Persistence Agent",
            model="gpt-5-codex",
            purpose="Migration graph and data-path integrity validation",
            commands=(
                CommandSpec(
                    name="migration-graph-check",
                    shell_command="cd backend && alembic history -r-3:",
                ),
                CommandSpec(
                    name="repo-import-sanity",
                    shell_command=_python_cmd("backend/test_repo.py", is_module=False),
                ),
            ),
        ),
        AgentLane(
            lane_id="agent-06-nemsis-neris-interoperability",
            agent_label="NEMSIS and NERIS Interoperability Agent",
            model="gpt-5-codex",
            purpose="Interoperability readiness and schema compliance checks",
            commands=(
                CommandSpec(
                    name="nemsis-ci-validate",
                    shell_command=_python_cmd("backend.compliance.nemsis.ci_validate"),
                ),
                CommandSpec(
                    name="neris-ci-validate",
                    shell_command=_python_cmd("backend.compliance.neris.ci_validate"),
                ),
            ),
        ),
        AgentLane(
            lane_id="agent-07-aws-infra-terraform",
            agent_label="AWS Infrastructure and Terraform Agent",
            model="gpt-5-codex",
            purpose="Terraform static validation, module integrity, and IaC safety gates",
            commands=(
                CommandSpec(
                    name="terraform-fmt-check",
                    shell_command="terraform fmt -check -recursive infra/terraform",
                    required=False,
                ),
                CommandSpec(
                    name="terraform-validate-prod",
                    shell_command=(
                        "TMP_TF_DATA_DIR=\"$(mktemp -d)\" "
                        "&& TF_DATA_DIR=\"$TMP_TF_DATA_DIR\" terraform -chdir=infra/terraform/environments/prod init -backend=false -reconfigure "
                        "&& TF_DATA_DIR=\"$TMP_TF_DATA_DIR\" terraform -chdir=infra/terraform/environments/prod validate"
                    ),
                ),
                CommandSpec(
                    name="checkov-scan",
                    shell_command=checkov_command,
                    required=False,
                ),
            ),
        ),
        AgentLane(
            lane_id="agent-08-security-compliance-audit",
            agent_label="Security, Compliance, and Audit Agent",
            model="gpt-5.4",
            purpose="Control evidence, placeholder/secrets scanning, compliance gate",
            commands=(
                CommandSpec(
                    name="compliance-program-validation",
                    shell_command=_python_cmd("scripts/validate_compliance_program.py", is_module=False),
                ),
                CommandSpec(
                    name="placeholder-secret-scan",
                    shell_command=_python_cmd("scripts/scan_placeholders.py", is_module=False),
                ),
            ),
        ),
        AgentLane(
            lane_id="agent-09-observability-reliability-ops",
            agent_label="Observability, Reliability, and Operations Agent",
            model="claude-opus",
            purpose="Orchestration telemetry visibility and frontend wiring integrity",
            commands=(
                CommandSpec(
                    name="founder-multi-agent-status-tests",
                    shell_command=(
                        "cd backend && "
                        + _shell_join(
                            [sys.executable, "-m", "pytest", "tests/test_founder_multi_agent_status_router.py", "-q"]
                        )
                    ),
                ),
                CommandSpec(
                    name="frontend-wiring-verification",
                    shell_command=_python_cmd("scripts/verify_frontend_wiring.py", is_module=False),
                    required=False,
                ),
            ),
        ),
        AgentLane(
            lane_id="agent-10-qa-validation-release",
            agent_label="QA, Validation, Deployment, and Release Agent",
            model="gemini-2.5-pro",
            purpose="Cross-stack release confidence and deploy gating",
            commands=(
                CommandSpec(
                    name="docker-build-backend",
                    shell_command="docker build -t fusionems-backend:multi-agent ./backend",
                    required=False,
                ),
                CommandSpec(
                    name="docker-build-frontend",
                    shell_command="docker build -t fusionems-frontend:multi-agent ./frontend",
                    required=False,
                ),
            ),
        ),
    )


def _build_deploy_commands(*, allow_apply: bool) -> tuple[CommandSpec, ...]:
    commands: list[CommandSpec] = [
        CommandSpec(
            name="aws-identity",
            shell_command="aws sts get-caller-identity",
        ),
        CommandSpec(
            name="terraform-init-prod",
            shell_command="terraform -chdir=infra/terraform/environments/prod init -lock-timeout=10m",
        ),
        CommandSpec(
            name="terraform-plan-prod",
            shell_command=(
                "terraform -chdir=infra/terraform/environments/prod plan "
                "-lock-timeout=10m -out=tfplan"
            ),
        ),
    ]

    commands.append(
        CommandSpec(
            name="assert-smoke-env",
            shell_command="test -n \"$FUSIONEMS_API_BASE_URL\" && test -n \"$SMOKE_AUTH_EMAIL\" && test -n \"$SMOKE_AUTH_PASSWORD\"",
        )
    )

    if allow_apply:
        commands.append(
            CommandSpec(
                name="terraform-apply-prod",
                shell_command="terraform -chdir=infra/terraform/environments/prod apply -auto-approve tfplan",
            )
        )

    api_base = shlex.quote(os.getenv("FUSIONEMS_API_BASE_URL", ""))
    frontend_base = shlex.quote(os.getenv("FUSIONEMS_FRONTEND_URL", ""))
    commands.append(
        CommandSpec(
            name="post-deploy-smoke",
            shell_command=(
                f"SMOKE_REQUIRE_AUTH=true SMOKE_API_BASE_URL={api_base} "
                f"SMOKE_FRONTEND_URL={frontend_base} "
                + _python_cmd("backend/scripts/smoke_test.py", is_module=False)
            ),
        )
    )

    return tuple(commands)


async def _run_lane(lane: AgentLane) -> LaneResult:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    started = _utc_now()
    log_path = LOG_DIR / f"{lane.lane_id}.log"
    command_results: list[CommandResult] = []
    lane_status = "passed"

    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(
            f"[{_iso(started)}] lane_start id={lane.lane_id} model={lane.model} purpose={lane.purpose}\n"
        )
        for cmd in lane.commands:
            cmd_started = _utc_now()
            log_file.write(
                f"[{_iso(cmd_started)}] command_start name={cmd.name} required={cmd.required}\n"
            )
            log_file.write(f"$ {cmd.shell_command}\n")
            log_file.flush()

            process = await asyncio.create_subprocess_shell(
                cmd.shell_command,
                cwd=str(ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await process.communicate()
            output_text = stdout.decode("utf-8", errors="replace")
            log_file.write(output_text)

            duration = (_utc_now() - cmd_started).total_seconds()
            exit_code = int(process.returncode or 0)
            command_results.append(
                CommandResult(
                    name=cmd.name,
                    command=cmd.shell_command,
                    exit_code=exit_code,
                    duration_seconds=duration,
                    required=cmd.required,
                )
            )

            log_file.write(
                f"[{_iso(_utc_now())}] command_end name={cmd.name} exit={exit_code} duration_seconds={duration:.2f}\n"
            )
            log_file.flush()

            if exit_code != 0 and cmd.required:
                lane_status = "failed"
                break
            if exit_code != 0 and lane_status != "failed":
                lane_status = "warning"

        if lane_status == "passed" and any(c.exit_code != 0 for c in command_results):
            lane_status = "warning"

    finished = _utc_now()
    return LaneResult(
        lane_id=lane.lane_id,
        agent_label=lane.agent_label,
        model=lane.model,
        purpose=lane.purpose,
        status=lane_status,
        started_at_utc=_iso(started),
        finished_at_utc=_iso(finished),
        duration_seconds=(finished - started).total_seconds(),
        log_file=str(log_path.relative_to(ROOT)),
        commands=command_results,
    )


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        )
        return out.strip()
    except Exception:
        return "unknown"


def _serialize_lane_result(lane: LaneResult) -> dict[str, object]:
    return {
        "lane_id": lane.lane_id,
        "agent_label": lane.agent_label,
        "model": lane.model,
        "purpose": lane.purpose,
        "status": lane.status,
        "started_at_utc": lane.started_at_utc,
        "finished_at_utc": lane.finished_at_utc,
        "duration_seconds": round(lane.duration_seconds, 3),
        "log_file": lane.log_file,
        "commands": [
            {
                "name": c.name,
                "command": c.command,
                "exit_code": c.exit_code,
                "duration_seconds": round(c.duration_seconds, 3),
                "required": c.required,
            }
            for c in lane.commands
        ],
    }


def _overall_status(lane_results: Sequence[LaneResult]) -> str:
    if any(r.status == "failed" for r in lane_results):
        return "failed"
    if any(r.status == "warning" for r in lane_results):
        return "warning"
    return "passed"


async def _run(mode: str, *, allow_apply: bool, report_path: Path) -> int:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    started = _utc_now()

    validate_lanes = list(_build_validate_lanes())
    heavy_lane = next(
        (lane for lane in validate_lanes if lane.lane_id == "agent-03-frontend-command-surface"),
        None,
    )
    parallel_lanes = [
        lane for lane in validate_lanes if lane.lane_id != "agent-03-frontend-command-surface"
    ]

    results: list[LaneResult] = []
    if parallel_lanes:
        results.extend(await asyncio.gather(*[_run_lane(lane) for lane in parallel_lanes]))

    if heavy_lane is not None:
        results.append(await _run_lane(heavy_lane))

    validate_failed = any(r.status == "failed" for r in results)
    if mode == "deploy" and not validate_failed:
        deploy_lane = AgentLane(
            lane_id="agent-01-master-orchestrator",
            agent_label="Master Orchestrator",
            model="gpt-5.4",
            purpose="Global release authority, deploy execution, and rollback gate control",
            commands=_build_deploy_commands(allow_apply=allow_apply),
        )
        results.append(await _run_lane(deploy_lane))

    finished = _utc_now()
    status = _overall_status(results)

    report = {
        "meta": {
            "generated_at_utc": _iso(finished),
            "started_at_utc": _iso(started),
            "finished_at_utc": _iso(finished),
            "duration_seconds": round((finished - started).total_seconds(), 3),
            "mode": mode,
            "allow_apply": allow_apply,
            "git_sha": _git_sha(),
            "contract_path": "ops/multi_agent_execution_contract.json",
            "execution_environment": "OpenAI Codex",
            "aws_profile": os.getenv("AWS_PROFILE", ""),
            "default_models": {
                "orchestration": "gpt-5.4",
                "platform_core": "gpt-5-codex",
                "frontend_command_surface": "claude-opus",
                "auth_access_control": "gpt-5.4",
                "data_persistence": "gpt-5-codex",
                "interoperability": "gpt-5-codex",
                "aws_terraform": "gpt-5-codex",
                "security_compliance": "gpt-5.4",
                "observability_reliability": "claude-opus",
                "qa_release": "gemini-2.5-pro"
            }
        },
        "status": status,
        "lanes": [_serialize_lane_result(r) for r in sorted(results, key=lambda x: x.lane_id)],
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({"status": status, "report": str(report_path.relative_to(ROOT))}))
    return 1 if status == "failed" else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FusionEMS multi-agent execution lanes.")
    parser.add_argument(
        "--mode",
        choices=("validate", "deploy"),
        default="validate",
        help="validate: run quality lanes only; deploy: include AWS deploy lane",
    )
    parser.add_argument(
        "--allow-apply",
        action="store_true",
        help="Only effective with --mode deploy. Allows terraform apply.",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Output report path (absolute or repo-relative)",
    )
    parser.add_argument(
        "--aws-profile",
        default=os.getenv("AWS_PROFILE", "fusion"),
        help="AWS profile to use for aws/terraform commands",
    )

    args = parser.parse_args()
    os.environ["AWS_PROFILE"] = args.aws_profile
    report = Path(args.report)
    if not report.is_absolute():
        report = ROOT / report

    return asyncio.run(_run(args.mode, allow_apply=args.allow_apply, report_path=report))


if __name__ == "__main__":
    raise SystemExit(main())

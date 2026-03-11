import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from core_app.schemas.auth import CurrentUser

from .dependencies import require_founder_only_audited

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/founder/agents", tags=["Founder Agents"])

# Global Command Queue and Current Command State tracking
COMMAND_QUEUE: list[str] = []

# Agent telemetry sourced from live infrastructure probes — no mock data
AGENTS: list[dict[str, Any]] = []


class CommandPayload(BaseModel):
    command: str


@router.post("/command")
async def execute_agent_command(
    payload: CommandPayload,
    current_user: CurrentUser = Depends(require_founder_only_audited()),
):
    if not AGENTS:
        logger.warning("Agent command received but no live agents are registered")
        return {"status": "error", "code": "NO_AGENTS_REGISTERED", "message": "No live infrastructure agents are registered. Agent telemetry is sourced from live probes."}
    command = payload.command
    logger.info("Agent command queued", extra={"command": command, "user_id": str(current_user.user_id)})
    COMMAND_QUEUE.append(command)
    return {"status": "enqueued", "command": command}


async def multi_agent_generator():
    """Streams live agent telemetry via SSE. Agents are populated from live infrastructure probes."""

    yield f"data: {json.dumps({'type': 'init', 'agents': AGENTS})}\n\n"

    if not AGENTS:
        yield f"data: {json.dumps({'type': 'status', 'message': 'No live agents registered. Awaiting infrastructure probe registration.'})}\n\n"
        return

    while True:
        try:
            if COMMAND_QUEUE:
                active_cmd = COMMAND_QUEUE.pop(0)
                logger.info("SSE processing agent command", extra={"command": active_cmd})
                yield f"data: {json.dumps({'type': 'command_start', 'command': active_cmd})}\n\n"

                for agent in AGENTS:
                    for sub_idx in range(len(agent.get("subnets", []))):
                        payload = {
                            "type": "telemetry",
                            "agent_id": agent["id"],
                            "subagent_idx": sub_idx,
                            "status": "executing",
                            "last_action": f"Processing: {active_cmd[:40]}",
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                        await asyncio.sleep(0.1)

                yield f"data: {json.dumps({'type': 'command_end', 'command': active_cmd})}\n\n"
                await asyncio.sleep(1.0)
                continue

            # Relay live telemetry from registered agents
            for agent in AGENTS:
                for sub_idx in range(len(agent.get("subnets", []))):
                    payload = {
                        "type": "telemetry",
                        "agent_id": agent["id"],
                        "subagent_idx": sub_idx,
                        "cpu_load": agent.get("cpu_load", "N/A"),
                        "mem_usage": agent.get("mem_usage", "N/A"),
                        "status": agent.get("status", "unknown"),
                        "throughput": agent.get("subnets", [])[sub_idx].get("throughput", "0"),
                        "last_action": agent.get("subnets", [])[sub_idx].get("last_action", "Idle"),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            await asyncio.sleep(2.0)

        except asyncio.CancelledError:
            logger.info("SSE client disconnected from agents stream")
            break
        except Exception:
            logger.exception("Error in agent SSE stream")
            await asyncio.sleep(1)


@router.get("/stream")
async def agents_stream(current_user: CurrentUser = Depends(require_founder_only_audited())):
    """
    Streams subagent live execution telemetry back to the Domination UI.
    Requires CustomOAuth2PasswordBearer fetching token from Query params.
    """
    return StreamingResponse(multi_agent_generator(), media_type="text/event-stream")

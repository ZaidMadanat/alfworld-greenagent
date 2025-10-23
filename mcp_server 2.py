# -*- coding: utf-8 -*-
"""
ALFWorld MCP server for AgentBeats
• Provides a `/sse` endpoint (FastMCP) so AgentBeats can push/pull events.
• Exposes two helper tools:
    1. update_battle_process  – emit structured progress logs
    2. run_terminal_command_in_docker – exec into the per-battle container
"""

import logging
import os
import json
from datetime import datetime
from pathlib import Path

import docker
import requests
from fastmcp import FastMCP


# CONFIG
BACKEND_URL = "http://localhost:9000"          # AgentBeats backend
DEFAULT_PORT = 9002                            # SSE endpoint for MCP
DOCKER_PREFIX = "alfworld_"                    # container name = f"{DOCKER_PREFIX}{battle_id}"

DOCKER_SOCKET_PATHS = [
    "/var/run/docker.sock",                             # Linux
    str(Path.home() / ".docker/run/docker.sock"),      # macOS Desktop
    str(Path.home() / ".docker/desktop/docker.sock"),   # macOS Desktop alt
]

# LOGGING
logger = logging.getLogger("alfworld_mcp")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s  %(message)s"))
    logger.addHandler(h)

# FAST-MCP SERVER
server = FastMCP(
    "ALFWorld MCP for AgentBeats",
    host="0.0.0.0",
    port=DEFAULT_PORT,
)

# UTILITIES
def get_docker_client() -> docker.DockerClient:
    """Connect to the local Docker daemon (tries common socket paths first)."""
    for sock in DOCKER_SOCKET_PATHS:
        if os.path.exists(sock):
            try:
                return docker.DockerClient(base_url=f"unix://{sock}")
            except Exception:  # pragma: no cover
                continue
    # Fallback to env vars (DOCKER_HOST, etc.)
    return docker.from_env()

def _append_json(log_file: Path, key: str, entry: dict):
    log_file.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if log_file.exists():
        try:
            data = json.loads(log_file.read_text())
        except Exception:
            data = {}
    data.setdefault(key, []).append(entry)
    log_file.write_text(json.dumps(data, indent=2))

# ─────────────────────────────────────────────
# TOOLS EXPOSED TO AGENTBEATS
# ─────────────────────────────────────────────
@server.tool()
def update_battle_process(
    battle_id: str,
    message: str,
    reported_by: str,
    detail: dict | None = None,
    markdown_content: str | None = None,
) -> str:
    """Push a progress/event log to the backend (or fallback to local file)."""
    payload = {
        "is_result": False,
        "message": message,
        "reported_by": reported_by,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if detail:
        payload["detail"] = detail
    if markdown_content:
        payload["markdown_content"] = markdown_content

    try:
        r = requests.post(
            f"{BACKEND_URL}/battles/{battle_id}",
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
        return "logged to backend"
    except Exception as exc:
        logger.warning("Backend log failed (%s); writing locally", exc)
        _append_json(Path("logs") / f"{battle_id}.json", "events", payload)
        return "logged locally"

@server.tool()
def run_terminal_command_in_docker(
    battle_id: str,
    command: str,
    agent_name: str,
) -> str:
    """Executes *command* inside the ALFWorld container for this battle."""
    client = get_docker_client()
    try:
        container = client.containers.get(f"{DOCKER_PREFIX}{battle_id}")
    except docker.errors.NotFound:
        msg = f"container {DOCKER_PREFIX}{battle_id} not found"
        logger.error(msg)
        return msg

    exec_log = container.exec_run(["sh", "-c", command])
    output = exec_log.output.decode(errors="ignore")

    # Record cmd log
    _append_json(
        Path("logs") / f"cmd_history_{battle_id}.json",
        "cmd_logs",
        {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "command": command,
            "output": output[:1_000],   # trim huge payloads
        },
    )
    return output

# CLI ENTRY
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Launch ALFWorld MCP server")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()

    server.run(
        transport="sse",
        host="0.0.0.0",
        port=args.port,
        log_level="ERROR",
    )
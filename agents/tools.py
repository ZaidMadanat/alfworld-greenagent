from __future__ import annotations

# Standard libraries
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, List
from uuid import uuid4

# Third-party libraries
import docker
import httpx
# AgentBeats / A2A imports
from agentbeats import tool
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import (
    AgentCard,
    Message,
    MessageSendParams,
    Role,
    SendStreamingMessageRequest,
    SendStreamingMessageSuccessResponse,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TextPart,
)

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALFWORLD_ROOT = PROJECT_ROOT / "alfworld"
if str(ALFWORLD_ROOT) not in sys.path:
    sys.path.insert(0, str(ALFWORLD_ROOT))
ALFWORLD_CFG = ALFWORLD_ROOT / "configs/base_config.yaml"
ALFWORLD_TASK_DIR = ALFWORLD_ROOT / "data" / "base_config" / "eval_out_of_distribution"


# ALFWorld imports (text-only env for now)
from alfworld.agents.environment import get_environment
import alfworld.agents.modules.generic as generic


# Logging
logger = logging.getLogger("green_tools")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_h)

logger.setLevel(logging.INFO)

# Common locations for the Docker socket on Linux/macOS
DOCKER_SOCKET_PATHS: list[str] = [
    "/var/run/docker.sock",
    "/run/docker.sock",
    "/docker.sock",
]



# Docker Setup and Battle Analysis 
_docker_client: docker.DockerClient | None = None
_attack_cumulative_times: defaultdict[str, float] = defaultdict(float)

# Track per‑battle containers so we can tear them down later
_battle_containers: dict[str, docker.models.containers.Container] = {}


def get_docker_client() -> docker.DockerClient:
    # Try explicit socket paths first
    for socket_path in DOCKER_SOCKET_PATHS:
        if os.path.exists(socket_path):
            try:
                return docker.DockerClient(base_url=f"unix://{socket_path}")
            except Exception:  
                continue  # try next socket

    # Fallback – honour DOCKER_HOST, TCP, etc. 
    try:
        return docker.from_env()
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Could not connect to the Docker daemon. Is Docker running?"
        ) from exc


# Re‑usable HTTPX client so we don't open a new connection per request
_httpx_client: httpx.AsyncClient | None = None

def _get_httpx_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(timeout=120, follow_redirects=True)
    return _httpx_client


async def _make_client(base_url: str) -> A2AClient:
    """Resolve an agent card at *base_url* and return a ready A2AClient."""
    httpx_client = _get_httpx_client()
    resolver = A2ACardResolver(
        httpx_client=httpx_client,
        base_url=base_url,
    )
    card: AgentCard | None = await resolver.get_agent_card(
        relative_card_path="/.well-known/agent.json"
    )
    if card is None:
        raise RuntimeError(f"Failed to resolve agent card from {base_url}")
    return A2AClient(httpx_client=httpx_client, agent_card=card)


async def talk_to_purple_or_white_agent(
    query: str,
    target_url: str,
    battle_id: str,
    timeout_seconds: float = 120.0,
) -> str:
    """Send *query* to the opponent agent and stream back the reply.

    Placeholder implementation; real code will reuse A2A once integrated.
    """
    async with _make_client(timeout_seconds) as client:
        resp = await client.post(
            f"{target_url.rstrip('/')}/chat",
            json={"query": query, "battle_id": battle_id},
        )
        resp.raise_for_status()
        return resp.json().get("response", "")


def get_attack_cumulative_time(battle_id: str) -> float:
    """Return cumulative time consumed by the current attacker."""
    return _attack_cumulative_times[battle_id]


def reset_battle_timing(battle_id: str) -> None:
    """Reset timing tracker for *battle_id*."""
    _attack_cumulative_times[battle_id] = 0.0


def start_alfworld_server(port: int = 8666) -> subprocess.Popen[str]:
    """Launch the ALFWorld *text* server on the specified port.

    Notes
    -----
    • The command is based on the bundled script
      `alfworld/scripts/run_text_server.py` which ships with ALFWorld.
    • Requires that the current process is running inside an X‑enabled
      environment (the Dockerfile starts Xvfb).
    """
    server_cmd = [
        "python",
        "-m",
        "alfworld.scripts.run_text_server",
        "--port",
        str(port),
        "--config",
        str(ALFWORLD_CFG),
    ]
    logger.info("Starting ALFWorld text server: %s", " ".join(server_cmd))
    return subprocess.Popen(server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def generate_alfworld_task(task_id: str, battle_id: str) -> Path:
    """Locate or create a task JSON and return its path.

    For now we simply look for an existing file
    `ALFWORLD_TASK_DIR/<task_id>.json`.  Future versions can generate
    tasks programmatically (e.g., difficulty sampling).
    """
    candidate = ALFWORLD_TASK_DIR / f"{task_id}.json"
    if not candidate.exists():
        raise FileNotFoundError(
            f"Task {task_id} not found under {ALFWORLD_TASK_DIR}"
        )
    logger.debug("Using task file %s for battle %s", candidate, battle_id)
    return candidate


def setup_docker_env(
    battle_id: str,
    image: str = "ghcr.io/myorg/alfworld:latest",
    port: int = 8666,
) -> None:
    """Pull the image and start a detached container for this battle.

    The container exposes *port* on the host and is stored in
    `_battle_containers` so we can tear it down later.
    """
    client = get_docker_client()
    container_name = f"alfworld-{battle_id}"
    logger.info("Spawning container %s with image %s", container_name, image)
    container = client.containers.run(
        image,
        detach=True,
        name=container_name,
        environment={"DISPLAY": ":0"},
        ports={f"{port}/tcp": port},
        auto_remove=True,
    )
    _battle_containers[battle_id] = container


def destroy_docker_env(battle_id: str) -> None:
    """Stop and remove the Docker container associated with *battle_id*."""
    container = _battle_containers.pop(battle_id, None)
    if container is None:
        logger.warning("No container recorded for battle %s", battle_id)
        return
    logger.info("Stopping container %s", container.name)
    try:
        container.stop(timeout=10)
    except Exception as exc:  # noqa: BLE001
        logger.error("Error stopping container %s: %s", container.name, exc)


def spawn_alfworld_env(task_json: Path):
    """Instantiate a text‑only ALFWorld environment for *task_json*.

    Returns
    -------
    env  : ALFWorldEnvironment
    task_meta : dict
    """
    env, _ = get_environment(str(ALFWORLD_CFG))
    env.reset(task_json=str(task_json))
    task_meta = generic.load_json(task_json)
    return env, task_meta


class A2AMessenger:
    """Wrapper around *a2a* streaming API to communicate with opponent agent."""

    def __init__(self, opponent_card: AgentCard, battle_id: str, timeout: float = 120.0):
        self.battle_id = battle_id
        self.client = A2AClient(card=opponent_card)
        self.timeout = timeout
        self._cum_time = 0.0

    async def ask(self, prompt: str) -> dict[str, Any]:
        """Send *prompt* and collect streaming result & timing info."""
        req = SendStreamingMessageRequest(
            message=Message(
                role=Role.USER,
                parts=[TextPart(text=prompt)],
            ),
            params=MessageSendParams(),
        )

        t0 = time.perf_counter()
        async with self.client.stream(req) as stream:
            chunks: List[str] = []
            async for event in stream:
                if isinstance(event, SendStreamingMessageSuccessResponse):
                    chunks.append(event.message.parts[0].text)
                elif isinstance(event, (TaskArtifactUpdateEvent, TaskStatusUpdateEvent)):
                    # Ignore task-level events for now
                    continue
        elapsed = time.perf_counter() - t0
        self._cum_time += elapsed
        return {"text": "".join(chunks), "elapsed": elapsed, "cumulative": self._cum_time}
    def reset_timer(self) -> None:
        self._cum_time = 0.0

@tool
async def run_episode(
    messenger: A2AMessenger,
    task_json: Path,
    step_limit: int = 80,
) -> dict[str, Any]:
    """Run one ALFWorld episode against the opponent agent.

    Returns
    -------
    dict with keys: task_json, action_log, steps, success (bool), reward
    """
    env, task_meta = spawn_alfworld_env(task_json)
    observation, info = env.reset()
    action_log: list[dict[str, Any]] = []
    done = False
    cumulative_reward = 0.0

    for step in range(step_limit):
        # Ask opponent for next action
        reply = await messenger.ask(observation)
        action = reply["text"].strip()

        # Step environment
        next_observation, reward, done, _, info = env.step(action)
        action_log.append(
            {
                "step": step,
                "action": action,
                "obs": observation,
                "reward": reward,
                "elapsed": reply["elapsed"],
            }
        )
        cumulative_reward += reward
        observation = next_observation
        if done:
            break

    env.close()
    result = {
        "task_json": str(task_json),
        "action_log": action_log,
        "steps": len(action_log),
        "success": bool(info.get("won", False)),
        "reward": cumulative_reward,
        "task_meta": task_meta,
    }
    return result

def compute_cleanup_metrics(action_log: Iterable[dict[str, Any]]) -> dict[str, float]:
    """Derive simple environmental metrics from the action log. """
    actions = [entry["action"] for entry in action_log]
    total_steps = len(actions) or 1

    # Repeated steps ratio
    repeated_steps = sum(
        1 for i in range(1, total_steps) if actions[i] == actions[i - 1]
    ) / total_steps

    # No‑change steps ratio: reward zero
    no_change_steps = sum(1 for entry in action_log if entry["reward"] == 0) / total_steps

    # Simple heuristics for open items / active appliances
    open_items = sum("open" in act for act in actions) / total_steps
    active_appl = sum("turn on" in act or "switch on" in act for act in actions) / total_steps
    unrestored = sum("put" in act and "sink" not in act for act in actions) / total_steps

    cleanup_score = 1.0 - (
        open_items + active_appl + unrestored + repeated_steps + no_change_steps
    ) / 5

    return {
        "cleanup_score": max(cleanup_score, 0.0),
        "open_items_ratio": open_items,
        "active_appliances_ratio": active_appl,
        "other_unrestored_objects_ratio": unrestored,
        "repeated_steps_ratio": repeated_steps,
        "no_change_steps_ratio": no_change_steps,
    }



@tool
async def evaluate_white_agent(
    opponent_card_url: str,
    battle_id: str | None = None,
    tasks_subset: list[str] | None = None,
) -> str:
    """AgentBeats-callable entry to score an opponent agent.

    Parameters
    ----------
    opponent_card_url : str
        Public URL to the opponent’s ``agent_card.toml`` or JSON.
    battle_id : str | None
        Unique identifier for this duel; autogenerated if ``None``.
    tasks_subset : list[str] | None
        Optional list of task JSON filenames to run – defaults to a tiny sample.
    """
    battle_id = battle_id or str(uuid4())

    # — Resolve opponent card ----------------------------------------------
    resolver = A2ACardResolver()
    opponent_card = await resolver.resolve(opponent_card_url)

    messenger = A2AMessenger(opponent_card, battle_id)

    # Pick tasks -------------------------------------------------------------
    tasks = tasks_subset or [str(next(ALFWORLD_TASK_DIR.glob("*/**/*.json")))]

    per_episode = []
    for task in tasks:
        logger.info("%s — running task %s", battle_id, Path(task).stem)
        episode = await run_episode(messenger, Path(task))
        episode["metrics"] = compute_cleanup_metrics(episode["action_log"])
        per_episode.append(episode)

    artifact_path = Path("/tmp") / f"{battle_id}_results.json"
    artifact_path.write_text(json.dumps(per_episode, indent=2))

    return _format_score_table(per_episode) + f"\n\nArtifact saved to {artifact_path}"

def _format_score_table(rows: List[dict[str, Any]]) -> str:
    if not rows:
        return "No episodes run."
    hdr = [
        "Task", "Cleanup", "Open", "ActiveAppl", "Repeat", "NoChange", "Steps", "Success?",
    ]
    out = [" | ".join(hdr), " | ".join(["---"] * len(hdr))]
    for r in rows:
        m = r["metrics"]
        out.append(" | ".join([
            Path(r["task_json"]).stem,
            f"{m.get('cleanup_score', 0):.2f}",
            f"{m.get('open_items_ratio', 0):.2f}",
            f"{m.get('active_appliances_ratio', 0):.2f}",
            f"{m.get('repeated_steps_ratio', 0):.2f}",
            f"{m.get('no_change_steps_ratio', 0):.2f}",
            str(r.get("steps", "?")),
            "✅" if r.get("success") else "❌",
        ]))
    return "\n".join(out)

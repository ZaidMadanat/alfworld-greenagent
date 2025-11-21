from __future__ import annotations

# Standard libraries
import asyncio
import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, List
from uuid import uuid4

# Logging - Initialize early for import warnings
logger = logging.getLogger("green_tools")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# Third-party libraries
try:
    import docker
except ImportError:
    docker = None
    logger.warning("docker package not found. Docker-related functions will not work.")

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
# Default task directory - ALFWorld tasks are typically in data/seed_data or similar
ALFWORLD_TASK_DIR = ALFWORLD_ROOT / "data" / "seed_data"
# Fallback to a local tasks directory if ALFWORLD_ROOT structure doesn't match
if not ALFWORLD_TASK_DIR.exists():
    ALFWORLD_TASK_DIR = PROJECT_ROOT / "tasks"
    ALFWORLD_TASK_DIR.mkdir(exist_ok=True)


# ALFWorld imports (text-only env for now)
try:
    from alfworld.agents.environment import get_environment
    import alfworld.agents.modules.generic as generic
    ALFWORLD_AVAILABLE = True
except ImportError as e:
    ALFWORLD_AVAILABLE = False
    logger = logging.getLogger("green_tools")
    logger.warning(f"ALFWorld package not found: {e}. ALFWorld-related functions will not work.")
    # Create dummy functions to prevent import errors
    get_environment = None
    generic = None



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
# Structure: {battle_id: {"container": Container, "api_url": str}}
_battle_containers: dict[str, dict[str, Any]] = {}


def get_docker_client() -> docker.DockerClient:
    """Get Docker client, raising error if docker package is not installed."""
    if docker is None:
        raise RuntimeError(
            "docker package not installed. Install it with: pip install docker"
        )
    
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


# ─────────────────────────────────────────────────────────────
# Port Management Utilities
# ─────────────────────────────────────────────────────────────

def find_free_port(start_port: int = 8001, max_port: int = 8999) -> int:
    """Find a free port in the specified range.
    
    Parameters
    ----------
    start_port : int
        Starting port number to check
    max_port : int
        Maximum port number to check
        
    Returns
    -------
    int
        A free port number
        
    Raises
    ------
    RuntimeError
        If no free port is found in the range
    """
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start_port}-{max_port}")


# ─────────────────────────────────────────────────────────────
# ALFWorld API Client Helpers
# ─────────────────────────────────────────────────────────────

def _get_api_url_for_battle(battle_id: str) -> str:
    """Get the API base URL for a battle's Docker container.
    
    Parameters
    ----------
    battle_id : str
        Battle identifier
        
    Returns
    -------
    str
        Base URL of the API server (e.g., "http://localhost:8001")
        
    Raises
    ------
    RuntimeError
        If no container is found for the battle_id
    """
    battle_info = _battle_containers.get(battle_id)
    if battle_info is None:
        raise RuntimeError(
            f"No Docker container found for battle {battle_id}. "
            f"Call setup_docker_env() first."
        )
    api_url = battle_info.get("api_url")
    if api_url is None:
        raise RuntimeError(
            f"API URL not found for battle {battle_id}. "
            f"Container may not be properly initialized."
        )
    return api_url


async def _wait_for_api_health(api_url: str, timeout: int = 30) -> bool:
    """Wait for the ALFWorld API server to be healthy.
    
    Parameters
    ----------
    api_url : str
        Base URL of the API server
    timeout : int
        Maximum seconds to wait
        
    Returns
    -------
    bool
        True if API is healthy, False if timeout reached
    """
    health_url = f"{api_url}/health"
    client = _get_httpx_client()
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = await client.get(health_url, timeout=5)
            if response.status_code == 200:
                logger.info(f"API health check passed: {health_url}")
                return True
        except Exception as exc:
            logger.debug(f"Health check failed (will retry): {exc}")
        await asyncio.sleep(1)
    
    logger.warning(f"API health check timed out after {timeout}s: {health_url}")
    return False


async def _reset_episode_via_api(api_url: str, battle_id: str) -> dict[str, Any]:
    """Reset an ALFWorld episode via the REST API.
    
    Parameters
    ----------
    api_url : str
        Base URL of the API server
    battle_id : str
        Battle/session identifier
        
    Returns
    -------
    dict
        Response containing observation, info, admissible_commands
    """
    reset_url = f"{api_url}/episode/reset"
    client = _get_httpx_client()
    
    try:
        # API uses session_id as query parameter, we'll use battle_id
        response = await client.post(
            reset_url,
            params={"session_id": battle_id},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error resetting episode: {exc.response.status_code} - {exc.response.text}")
        raise RuntimeError(f"Failed to reset episode: HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        logger.error(f"Error resetting episode via API: {exc}")
        raise RuntimeError(f"Failed to reset episode: {exc}") from exc


async def _step_episode_via_api(api_url: str, battle_id: str, action: str) -> dict[str, Any]:
    """Step an ALFWorld episode via the REST API.
    
    Parameters
    ----------
    api_url : str
        Base URL of the API server
    battle_id : str
        Battle/session identifier
    action : str
        Action to execute
        
    Returns
    -------
    dict
        Response containing observation, score, done, info
    """
    step_url = f"{api_url}/episode/step"
    client = _get_httpx_client()
    
    try:
        response = await client.post(
            step_url,
            params={"session_id": battle_id, "action": action},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error stepping episode: {exc.response.status_code} - {exc.response.text}")
        raise RuntimeError(f"Failed to step episode: HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        logger.error(f"Error stepping episode via API: {exc}")
        raise RuntimeError(f"Failed to step episode: {exc}") from exc


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


@tool
async def talk_to_purple_or_white_agent(
    query: str,
    target_url: str,
    battle_id: str,
    timeout_seconds: float = 120.0,
) -> str:
    """Send *query* to the opponent agent and stream back the reply using A2A protocol."""
    client = await _make_client(target_url)
    try:
        req = SendStreamingMessageRequest(
            message=Message(
                role=Role.USER,
                parts=[TextPart(text=query)],
            ),
            params=MessageSendParams(),
        )
        
        chunks: List[str] = []
        async with client.stream(req) as stream:
            async for event in stream:
                if isinstance(event, SendStreamingMessageSuccessResponse):
                    if event.message.parts:
                        chunks.append(event.message.parts[0].text)
                elif isinstance(event, (TaskArtifactUpdateEvent, TaskStatusUpdateEvent)):
                    # Ignore task-level events for now
                    continue
        
        return "".join(chunks)
    except Exception as exc:
        logger.error(f"Error communicating with opponent agent: {exc}")
        raise


@tool
def get_attack_cumulative_time(battle_id: str) -> float:
    """Return cumulative time consumed by the current attacker."""
    return _attack_cumulative_times[battle_id]


@tool
def reset_battle_timing(battle_id: str) -> str:
    """Reset timing tracker for *battle_id*."""
    _attack_cumulative_times[battle_id] = 0.0
    return f"Timing tracker reset for battle {battle_id}"


@tool
def start_alfworld_server(port: int = 8666) -> str:
    """Launch the ALFWorld *text* server on the specified port.

    Notes
    -----
    • The command is based on the bundled script
      `alfworld/scripts/run_text_server.py` which ships with ALFWorld.
    • Requires that the current process is running inside an X‑enabled
      environment (the Dockerfile starts Xvfb).
    """
    if not ALFWORLD_AVAILABLE:
        raise RuntimeError(
            "ALFWorld package not installed. Install it with: pip install alfworld"
        )
    
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
    proc = subprocess.Popen(server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return f"ALFWorld text server started on port {port}, PID: {proc.pid}"


@tool
def generate_alfworld_task(task_id: str, battle_id: str) -> str:
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
    return str(candidate)


@tool
def setup_docker_env(
    battle_id: str,
    image: str | None = None,
    port: int | None = None,
    build_image: bool = True,
) -> str:
    """Build Docker image from local Dockerfile and start a container for this battle.

    The container runs the ALFWorld REST API server and exposes it on a dynamically
    assigned host port. The container and API URL are stored in `_battle_containers`.

    Parameters
    ----------
    battle_id : str
        Battle identifier
    image : str | None
        Docker image name/tag to use. If None and build_image=True, uses "alfworld-api:local".
        If None and build_image=False, raises error.
    port : int | None
        Host port to map container port 8000 to. If None, automatically finds a free port.
    build_image : bool
        If True, build the image from PROJECT_ROOT/Dockerfile before running.

    Returns
    -------
    str
        Success message with container name and API URL
    """
    client = get_docker_client()
    container_name = f"alfworld_{battle_id}"
    
    # Build image if requested
    if build_image:
        image = image or "alfworld-api:local"
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        
        if not dockerfile_path.exists():
            raise FileNotFoundError(
                f"Dockerfile not found at {dockerfile_path}. "
                f"Cannot build image."
            )
        
        logger.info(f"Building Docker image {image} from {dockerfile_path}")
        try:
            # Build the image
            image_obj, build_logs = client.images.build(
                path=str(PROJECT_ROOT),
                dockerfile=str(dockerfile_path),
                tag=image,
                rm=True,  # Remove intermediate containers
            )
            logger.info(f"Successfully built image {image}")
            # Log build output if there are warnings
            for log_line in build_logs:
                if 'stream' in log_line:
                    log_msg = log_line['stream'].strip()
                    if log_msg and ('warning' in log_msg.lower() or 'error' in log_msg.lower()):
                        logger.warning(f"Build log: {log_msg}")
        except Exception as exc:
            logger.error(f"Failed to build Docker image: {exc}")
            raise RuntimeError(f"Docker image build failed: {exc}") from exc
    else:
        if image is None:
            raise ValueError("image parameter required when build_image=False")
        # Try to pull if image doesn't exist locally
        try:
            client.images.get(image)
            logger.info(f"Using existing image: {image}")
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling image: {image}")
            try:
                client.images.pull(image)
            except Exception as exc:
                raise RuntimeError(f"Failed to pull image {image}: {exc}") from exc
    
    # Find a free port if not specified
    if port is None:
        port = find_free_port(start_port=8001, max_port=8999)
        logger.info(f"Auto-assigned port {port} for battle {battle_id}")
    
    # Prepare volume mounts for task files
    # Mount the task directory so the container can access task JSON files
    volumes = {}
    if ALFWORLD_TASK_DIR.exists():
        volumes[str(ALFWORLD_TASK_DIR)] = {
            "bind": "/app/tasks",
            "mode": "ro"  # Read-only mount
        }
        logger.info(f"Mounting task directory {ALFWORLD_TASK_DIR} to /app/tasks in container")
    
    # Start container
    logger.info(f"Starting container {container_name} with image {image} on port {port}")
    try:
        container = client.containers.run(
            image,
            detach=True,
            name=container_name,
            ports={"8000/tcp": port},  # Map container port 8000 to host port
            volumes=volumes if volumes else None,
            auto_remove=False,  # Don't auto-remove so we can stop it manually
            environment={
                "ALFWORLD_DATA": "/app/alfworld/data",
                "API_PORT": "8000",
                "API_HOST": "0.0.0.0",
            },
        )
    except docker.errors.ContainerError as exc:
        raise RuntimeError(f"Container failed to start: {exc}") from exc
    except Exception as exc:
        logger.error(f"Failed to start container: {exc}")
        raise RuntimeError(f"Failed to start container: {exc}") from exc
    
    # Construct API URL
    api_url = f"http://localhost:{port}"
    
    # Store container and API URL
    _battle_containers[battle_id] = {
        "container": container,
        "api_url": api_url,
        "port": port,
    }
    
    # Wait for API to be healthy (with timeout)
    logger.info(f"Waiting for API server to be ready at {api_url}")
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    health_ok = loop.run_until_complete(_wait_for_api_health(api_url, timeout=60))
    if not health_ok:
        # Container might still be starting, but log a warning
        logger.warning(
            f"API health check timed out for {api_url}, but container is running. "
            f"Container logs: {container.logs(tail=20).decode('utf-8', errors='ignore')}"
        )
        return (
            f"Docker container {container_name} started on port {port}, "
            f"but API health check timed out. API URL: {api_url}. "
            f"Check container logs if API is not accessible."
        )
    
    return (
        f"Docker container {container_name} started successfully. "
        f"ALFWorld API server available at {api_url}"
    )


@tool
def destroy_docker_env(battle_id: str) -> str:
    """Stop and remove the Docker container associated with *battle_id*."""
    battle_info = _battle_containers.pop(battle_id, None)
    if battle_info is None:
        msg = f"No container recorded for battle {battle_id}"
        logger.warning(msg)
        return msg
    
    # Handle both old format (just Container) and new format (dict with container and api_url)
    if isinstance(battle_info, dict):
        container = battle_info.get("container")
        api_url = battle_info.get("api_url", "unknown")
    else:
        # Legacy format - direct container reference
        container = battle_info
        api_url = "unknown"
    
    if container is None:
        msg = f"Container reference missing for battle {battle_id}"
        logger.warning(msg)
        return msg
    
    logger.info(f"Stopping container {container.name} (API was at {api_url})")
    try:
        container.stop(timeout=10)
        # Optionally remove the container
        try:
            container.remove()
            return f"Container {container.name} stopped and removed successfully"
        except Exception as remove_exc:
            logger.warning(f"Could not remove container {container.name}: {remove_exc}")
            return f"Container {container.name} stopped successfully (not removed)"
    except Exception as exc:  # noqa: BLE001
        error_msg = f"Error stopping container {container.name}: {exc}"
        logger.error(error_msg)
        return error_msg


def spawn_alfworld_env(task_json: Path):
    """Instantiate a text‑only ALFWorld environment for *task_json*.

    Returns
    -------
    env  : ALFWorldEnvironment
    task_meta : dict
    """
    if not ALFWORLD_AVAILABLE or get_environment is None or generic is None:
        raise RuntimeError(
            "ALFWorld package not installed. Install it with: pip install alfworld"
        )
    
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
    opponent_agent_url: str,
    task_json_path: str,
    battle_id: str,
    step_limit: int = 80,
    api_url: str | None = None,
) -> dict[str, Any]:
    """Run one ALFWorld episode against the opponent agent via REST API.

    Parameters
    ----------
    opponent_agent_url : str
        URL to the opponent agent's agent card (e.g., "http://localhost:8061/")
    task_json_path : str
        Path to the task JSON file (note: current API implementation may not support
        specific task selection; this parameter is preserved for future API updates)
    battle_id : str
        Battle identifier (used as session_id for API)
    step_limit : int
        Maximum number of steps to run (default: 80)
    api_url : str | None
        Base URL of the ALFWorld API server. If None, looks up from _battle_containers
        using battle_id. Must have called setup_docker_env() first if None.

    Returns
    -------
    dict with keys: task_json, action_log, steps, success (bool), reward, task_meta
    """
    # Get API URL - either provided or lookup from container registry
    if api_url is None:
        api_url = _get_api_url_for_battle(battle_id)
    
    # Resolve opponent agent card and create messenger
    httpx_client = _get_httpx_client()
    resolver = A2ACardResolver(
        httpx_client=httpx_client,
        base_url=opponent_agent_url,
    )
    opponent_card: AgentCard | None = await resolver.get_agent_card(
        relative_card_path="/.well-known/agent.json"
    )
    if opponent_card is None:
        raise RuntimeError(f"Failed to resolve opponent agent card from {opponent_agent_url}")
    
    messenger = A2AMessenger(opponent_card, battle_id)
    task_json = Path(task_json_path)
    
    # Reset episode via API
    logger.info(f"Resetting episode via API {api_url} for battle {battle_id}")
    reset_response = await _reset_episode_via_api(api_url, battle_id)
    
    # Extract observation and info from API response
    observation = reset_response.get("observation", "")
    info = reset_response.get("info", {})
    admissible_commands = info.get("admissible_commands", [])
    raw_info = info.get("raw", {})
    
    # Try to load task metadata from file (if available)
    task_meta = {}
    try:
        if task_json.exists():
            task_meta = json.loads(task_json.read_text())
    except Exception as exc:
        logger.warning(f"Could not load task metadata from {task_json}: {exc}")
    
    action_log: list[dict[str, Any]] = []
    cumulative_reward = 0.0
    done = False
    success = False

    # Run episode loop
    for step in range(step_limit):
        # Ask opponent for next action
        prompt = observation
        if admissible_commands:
            prompt += f"\n\nAdmissible commands: {', '.join(admissible_commands[:5])}"  # Show first 5
        
        reply = await messenger.ask(prompt)
        action = reply["text"].strip()
        
        # Step environment via API
        logger.debug(f"Step {step}: executing action '{action[:50]}...'")
        step_response = await _step_episode_via_api(api_url, battle_id, action)
        
        # Extract response data
        next_observation = step_response.get("observation", "")
        score = step_response.get("score", 0.0)
        done = step_response.get("done", False)
        step_info = step_response.get("info", {})
        step_admissible_commands = step_info.get("admissible_commands", [])
        step_raw_info = step_info.get("raw", {})
        
        # Convert score to reward (API uses 'score', we use 'reward' in logs)
        reward = float(score)
        
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
        admissible_commands = step_admissible_commands
        raw_info = step_raw_info
        
        # Check for success condition
        if done:
            # Check if episode was successful (won)
            success = bool(step_raw_info.get("won", False) or step_raw_info.get("success", False))
            logger.info(f"Episode completed at step {step + 1}, success: {success}, cumulative reward: {cumulative_reward}")
            break

    # Check for success if not already set
    if not done:
        success = bool(raw_info.get("won", False) or raw_info.get("success", False))
    
    result = {
        "task_json": str(task_json),
        "action_log": action_log,
        "steps": len(action_log),
        "success": success,
        "reward": cumulative_reward,
        "task_meta": task_meta,
    }
    
    logger.info(
        f"Episode completed: {len(action_log)} steps, success={success}, "
        f"cumulative_reward={cumulative_reward}"
    )
    
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
        Public URL to the opponent's ``agent_card.toml`` or JSON.
    battle_id : str | None
        Unique identifier for this duel; autogenerated if ``None``.
    tasks_subset : list[str] | None
        Optional list of task JSON file paths to run – defaults to a tiny sample.
    """
    battle_id = battle_id or str(uuid4())

    # Pick tasks -------------------------------------------------------------
    if tasks_subset is None:
        # Find any task JSON file in the task directory
        task_files = list(ALFWORLD_TASK_DIR.glob("**/*.json"))
        if not task_files:
            raise FileNotFoundError(
                f"No task JSON files found in {ALFWORLD_TASK_DIR}. "
                f"Ensure tasks are available."
            )
        tasks = [str(task_files[0])]  # Use first task found
    else:
        tasks = tasks_subset

    per_episode = []
    for task_path in tasks:
        task_path_obj = Path(task_path)
        logger.info("%s — running task %s", battle_id, task_path_obj.stem)
        episode = await run_episode(
            opponent_agent_url=opponent_card_url,
            task_json_path=str(task_path_obj),
            battle_id=battle_id,
        )
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

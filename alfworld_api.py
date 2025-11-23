# -*- coding: utf-8 -*-
"""
ALFWorld REST API Server
Provides REST endpoints for controlling ALFWorld episodes and integrating with AgentBeats.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add ALFWorld to path - vzhong/alfworld installs to /opt/alfworld
ALFWORLD_ROOT = Path("/opt/alfworld")
if str(ALFWORLD_ROOT) not in sys.path:
    sys.path.insert(0, str(ALFWORLD_ROOT))

ALFWORLD_CFG = ALFWORLD_ROOT / "configs" / "base_config.yaml"
# Tasks are located in ALFWORLD_DATA/json_2.1.1/train/
# ALFWORLD_DATA defaults to /app/alfworld/data when set in Dockerfile
ALFWORLD_DATA = Path(os.getenv("ALFWORLD_DATA", "/opt/alfworld/data"))
ALFWORLD_TASK_DIR = ALFWORLD_DATA / "json_2.1.1" / "train"

# ALFWorld imports
from alfworld.agents.environment import AlfredTWEnv
import alfworld.agents.modules.generic as generic

# Environment instances per session
ENVIRONMENTS = {}  # type: Dict[str, AlfredTWEnv]
DEFAULT_SESSION_ID = "default"

# Logging
logger = logging.getLogger("alfworld_api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)

# FastAPI app
app = FastAPI(title="ALFWorld REST API", version="1.0.0")

@app.on_event("startup")
async def load_alfworld_config():
    """Load ALFWorld config once at startup to avoid parsing sys.argv on every request."""
    global _ALFWORLD_CONFIG, _ENV_TYPE
    
    logger.info(f"Loading ALFWorld config from {ALFWORLD_CFG}")
    
    # Save original sys.argv
    original_argv = sys.argv.copy()
    try:
        # Temporarily set sys.argv to only contain the config file path
        # so generic.load_config() can parse it correctly
        sys.argv = ['alfworld_api.py', str(ALFWORLD_CFG)]
        _ALFWORLD_CONFIG = generic.load_config()
        _ENV_TYPE = _ALFWORLD_CONFIG['env']['type']
        logger.info(f"Successfully loaded config, env_type={_ENV_TYPE}")
    except Exception as e:
        logger.error(f"Failed to load ALFWorld config: {e}", exc_info=True)
        raise
    finally:
        # Restore original sys.argv
        sys.argv = original_argv

_episode_sessions: Dict[str, Dict[str, Any]] = {}
DEFAULT_SESSION_ID = "default"  # For simple single-episode testing

# Cached ALFWorld config (loaded once at startup)
_ALFWORLD_CONFIG = None  # type: Optional[Dict[str, Any]]
_ENV_TYPE = None  # type: Optional[str]


# Pydantic models for request/response
class ResetRequest(BaseModel):
    task_id: Optional[str] = Field(default=None)
    task_json_path: Optional[str] = Field(default=None)
    battle_id: Optional[str] = Field(default=None)  # Optional, auto-generated if not provided


class StepRequest(BaseModel):
    action: str
    battle_id: Optional[str] = Field(default=None)  # Optional, uses default session if not provided


class EpisodeState(BaseModel):
    battle_id: str
    observation: str
    step_count: int
    done: bool
    reward: float
    info: Dict[str, Any]
    task_meta: Optional[Dict[str, Any]] = None


# Helper functions
def find_task_directory() -> Optional[Path]:
    """Find the task directory."""
    if ALFWORLD_TASK_DIR.exists() and ALFWORLD_TASK_DIR.is_dir():
        return ALFWORLD_TASK_DIR
    return None


def get_task_path(task_id: Optional[str] = None, task_json_path: Optional[str] = None) -> Path:
    """Resolve task JSON file path from task_id or task_json_path."""
    if task_json_path:
        path = Path(task_json_path)
        if path.is_absolute():
            if path.exists():
                return path
            raise FileNotFoundError(f"Task file not found: {task_json_path}")
        # Try relative to task directory
        candidate = ALFWORLD_TASK_DIR / task_json_path
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Task file not found: {task_json_path}")
    elif task_id:
        # Search in the task directory
        if not ALFWORLD_TASK_DIR.exists():
            raise FileNotFoundError(
                f"Task directory not found: {ALFWORLD_TASK_DIR}. "
                f"ALFWORLD_DATA={ALFWORLD_DATA}. Task data may need to be downloaded."
            )
        # Try direct path first
        candidate = ALFWORLD_TASK_DIR / f"{task_id}.json"
        if candidate.exists():
            return candidate
        # Try finding in subdirectories
        matches = list(ALFWORLD_TASK_DIR.rglob(f"{task_id}.json"))
        if matches:
            return matches[0]
        raise FileNotFoundError(
            f"Task {task_id} not found in {ALFWORLD_TASK_DIR}. "
            f"Task data may need to be downloaded."
        )
    else:
        raise ValueError("Either task_id or task_json_path must be provided")


def spawn_alfworld_env(task_json: Path):
    """Instantiate a text-only ALFWorld environment for task_json.
    
    Note: This only creates the environment. Call env.reset(task_json=...) to initialize.
    """
    # AlfredTWEnv is used in vzhong/alfworld image
    # Initialize environment with config
    env = AlfredTWEnv(config=_ALFWORLD_CONFIG, train_eval="train").init_env(batch_size=1)
    task_meta = generic.load_json(task_json)
    return env, task_meta


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "alfworld-api"}


@app.get("/tasks")
async def list_tasks():
    """List available task JSON files from ALFWORLD_DATA/json_2.1.1/train/."""
    if not ALFWORLD_TASK_DIR.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Task directory not found: {ALFWORLD_TASK_DIR}. "
                f"ALFWORLD_DATA={ALFWORLD_DATA}. "
                f"ALFWorld task data files may need to be downloaded. "
                f"Run 'alfworld-download' to download task data."
            )
        )
    
    task_files = []
    for task_file in ALFWORLD_TASK_DIR.rglob("*.json"):
        rel_path = task_file.relative_to(ALFWORLD_TASK_DIR)
        task_files.append({
            "task_id": task_file.stem,
            "path": str(rel_path),
            "full_path": str(task_file)
        })
    
    # Separate traj_data.json files from other JSON files
    traj_files = [f for f in task_files if "traj_data.json" in f["path"]]
    other_files = [f for f in task_files if "traj_data.json" not in f["path"]]

    print("\n in API traj_files: ", traj_files, "\n")

    jsons = []
    for f in task_files:
        with open(f['full_path'], 'r') as file:
            try:
                json_data = json.load(file)
                jsons.append(json_data)
            except json.JSONDecodeError:
                print(f"Error loading JSON file: {f['full_path']}")
                continue
    
    task_ids = []
    task_types = []
    total_count = 0


    for json_data in jsons:
        task_id = json_data.get('task_id')
        task_ids.append(task_id)
        task_type = json_data.get('task_type')
        task_types.append(task_type)
        total_count += 1


    return {
            "task_ids": task_ids, 
            "task_types": task_types,
            "total_count": total_count,
    }
    """
    return {
        "task_dir": str(ALFWORLD_TASK_DIR),
        "alfworld_data": str(ALFWORLD_DATA),
        "total_count": len(task_files),
        "traj_data_files": len(traj_files),
        "other_json_files": len(other_files),
        "tasks": task_files[:100],  # Limit to first 100 for response size
        "note": "Tasks are in ALFWORLD_DATA/json_2.1.1/train/. Use task_json_path to specify full path relative to task_dir."
    }"""

@app.post("/episode/reset")
async def reset_env(session_id: str = DEFAULT_SESSION_ID):
    """Start or reset an episode with a task JSON.
    
    Mimics: obs, info = env.reset(task_json=...)
    Returns observation and admissible_commands from info.
    """
    
    # Use cached config loaded at startup
    if _ALFWORLD_CONFIG is None or _ENV_TYPE is None:
        raise HTTPException(
            status_code=500,
            detail="ALFWorld config not loaded. Check server startup logs."
        )
    
    config = _ALFWORLD_CONFIG
    env_type = _ENV_TYPE

    env = ENVIRONMENTS.get(session_id)
    if env is None:
        env = AlfredTWEnv(config, train_eval="train").init_env(batch_size=1)
        ENVIRONMENTS[session_id] = env

    obs, info = env.reset()

    return {
        "observation": obs,
        "info": {
            "admissible_commands": list(info.get('admissible_commands', [[]])[0]),
            "raw": info
        }
    }

    """
    try:
        task_path = get_task_path(request.task_id, request.task_json_path)
        
        if not task_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Task file not found: {task_path}"
            )
        
        # Use provided battle_id or default to simple session
        battle_id = request.battle_id or DEFAULT_SESSION_ID
        
        # Create environment
        env, task_meta = spawn_alfworld_env(task_path)
        
        # Call reset() to initialize the episode and get initial observation and info
        observation, info = env.reset(task_json=str(task_path))
        
        # Extract admissible commands from info (matching ALFWorld example)
        admissible_commands = list(info.get('admissible_commands', []))
        
        # Store session state
        _episode_sessions[battle_id] = {
            "env": env,
            "observation": observation,
            "info": info,
            "admissible_commands": admissible_commands,
            "step_count": 0,
            "cumulative_reward": 0.0,
            "done": False,
            "task_path": str(task_path),
            "task_meta": task_meta
        }
        
        logger.info(
            f"Episode reset for battle_id={battle_id}, task={task_path.name}, "
            f"admissible_commands={len(admissible_commands)}"
        )
        
        return {
            "observation": observation,
            "admissible_commands": admissible_commands,
            "info": info,
            "battle_id": battle_id,
            "task_path": str(task_path)
        }
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error resetting episode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") """


@app.get("/episode/state")
async def get_episode_state(battle_id: str):
    """Get current game state for an episode."""
    if battle_id not in _episode_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"No active episode found for battle_id: {battle_id}"
        )
    
    session = _episode_sessions[battle_id]
    
    # Get current admissible commands from info (they update after each step)
    current_admissible_commands = session["info"].get("admissible_commands", session.get("admissible_commands", []))
    
    return {
        "battle_id": battle_id,
        "observation": session["observation"],
        "admissible_commands": current_admissible_commands,
        "step_count": session["step_count"],
        "done": session["done"],
        "reward": session["cumulative_reward"],
        "info": session["info"],
        "task_meta": session.get("task_meta")
    }


@app.post("/episode/step")
async def step_episode(session_id: str = DEFAULT_SESSION_ID, action: str = None):
    """Execute an action and get the next state.
    
    Mimics: obs, scores, dones, infos = env.step(action)
    Returns observation and updated admissible_commands from info.
    """


    config = _ALFWORLD_CONFIG
    env_type = _ENV_TYPE
    
    if not action:
        raise HTTPException(
            status_code=400,
            detail="Action is required"
        )

    env = ENVIRONMENTS.get(session_id)
    if env is None:
        env = AlfredTWEnv(config, train_eval="train").init_env(batch_size=1)
        ENVIRONMENTS[session_id] = env

    obs, scores, dones, infos = env.step([action])

    return {
        "observation": obs[0],
        "score": float(scores[0]),
        "done": bool(dones[0]),
        "info": {
            "admissible_commands": list(infos.get("admissible_commands", [[]])[0]),
            "raw": infos
        }
    }
    """
    battle_id = request.battle_id or DEFAULT_SESSION_ID
    
    if battle_id not in _episode_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"No active episode found. Call /episode/reset first."
        )
    
    session = _episode_sessions[battle_id]
    
    if session["done"]:
        raise HTTPException(
            status_code=400,
            detail=f"Episode is already done for battle_id: {request.battle_id}"
        )
    
    try:
        env = session["env"]
        action = request.action.strip()
        
        # Step the environment
        next_observation, reward, done, _, info = env.step(action)
        
        # Extract updated admissible commands from info
        admissible_commands = info.get("admissible_commands", [])
        
        # Update session state
        session["observation"] = next_observation
        session["step_count"] += 1
        session["cumulative_reward"] += reward
        session["done"] = done
        session["info"] = info
        session["admissible_commands"] = admissible_commands
        
        logger.info(
            f"Step {session['step_count']} for battle_id={request.battle_id}, "
            f"action={action[:50]}, reward={reward}, done={done}"
        )
        
        # Clean up if done
        if done:
            env.close()
            logger.info(f"Episode completed for battle_id={request.battle_id}")
        
        return {
            "observation": next_observation,
            "admissible_commands": admissible_commands,
            "reward": reward,
            "done": done,
            "step_count": session["step_count"],
            "info": info,
            "action": action
        }
    
    except Exception as e:
        logger.error(f"Error stepping episode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") """


@app.delete("/episode/{battle_id}")
async def close_episode(battle_id: str):
    """Close and clean up an episode session."""
    if battle_id not in _episode_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"No active episode found for battle_id: {battle_id}"
        )
    
    session = _episode_sessions[battle_id]
    env = session["env"]
    env.close()
    
    del _episode_sessions[battle_id]
    
    logger.info(f"Episode closed for battle_id={battle_id}")
    
    return {"battle_id": battle_id, "status": "closed"}


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)


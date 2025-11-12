#!/usr/bin/env python3
"""Simple launcher for AgentBeats battles - similar to agentify-example-tau-bench pattern."""

import os
import time
import json
import signal
import subprocess
import multiprocessing
import requests
from pathlib import Path
from typing import Optional, Dict, Any

# Configuration
BACKEND_URL = "http://localhost:9000"
FRONTEND_URL = "http://localhost:5174"
MAX_WAIT_TIME = 90  # seconds

# Agent configurations - adjust these to match your agent cards
AGENTS = [
    {
        "name": "Blue Agent",
        "card": "scenarios/tensortrust/blue_weaker_agent_card.toml",
        "launcher_host": "0.0.0.0",
        "launcher_port": 9010,
        "agent_host": "0.0.0.0",
        "agent_port": 9011,
        "model_type": "openai",
        "model_name": "o4-mini",
    },
    {
        "name": "Red Agent",
        "card": "scenarios/tensortrust/red_stronger_agent_card.toml",
        "launcher_host": "0.0.0.0",
        "launcher_port": 9020,
        "agent_host": "0.0.0.0",
        "agent_port": 9021,
        "model_type": "openai",
        "model_name": "gpt-4o-mini",
    },
    {
        "name": "Green Agent",
        "card": "scenarios/tensortrust/green_agent/green_weaker_agent_card.toml",
        "launcher_host": "0.0.0.0",
        "launcher_port": 9030,
        "agent_host": "0.0.0.0",
        "agent_port": 9031,
        "model_type": "openai",
        "model_name": "o4-mini",
        "tools": ["scenarios/tensortrust/green_agent/tools.py"],
        "mcp_servers": ["http://localhost:9001/sse"],
        "is_green": True,
        "participant_requirements": [
            {
                "role": "red_agent",
                "name": "prompt_injector",
                "required": True,
                "participant_agent": "Red Agent",
            },
            {
                "role": "blue_agent",
                "name": "guardrail_generator",
                "required": True,
                "participant_agent": "Blue Agent",
            },
        ],
    },
]


def start_agent(agent_config: Dict[str, Any], agentbeats_dir: Path, env: dict) -> subprocess.Popen:
    """Start an agent using agentbeats run command."""
    cmd_parts = [
        "agentbeats", "run", str(agentbeats_dir / agent_config["card"]),
        "--launcher_host", agent_config["launcher_host"],
        "--launcher_port", str(agent_config["launcher_port"]),
        "--agent_host", agent_config["agent_host"],
        "--agent_port", str(agent_config["agent_port"]),
        "--model_type", agent_config["model_type"],
        "--model_name", agent_config["model_name"],
    ]
    
    if agent_config.get("tools"):
        for tool in agent_config["tools"]:
            cmd_parts.extend(["--tool", str(agentbeats_dir / tool)])
    
    if agent_config.get("mcp_servers"):
        for mcp in agent_config["mcp_servers"]:
            cmd_parts.extend(["--mcp", mcp])
    
    cmd = " ".join(cmd_parts)
    print(f"Starting {agent_config['name']}: {cmd}")
    
    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=str(agentbeats_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc


def wait_for_agent_ready(agent_url: str, timeout: int = 30) -> bool:
    """Wait for agent to be ready by checking its agent card endpoint."""
    start_time = time.time()
    # Ensure URL has trailing slash for proper path joining
    base_url = agent_url.rstrip('/')
    while time.time() - start_time < timeout:
        try:
            # A2A agents expose their card at .well-known/agent-card.json
            response = requests.get(f"{base_url}/.well-known/agent-card.json", timeout=2)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def wait_for_launcher_ready(launcher_url: str, timeout: int = 30) -> bool:
    """Wait for launcher to be ready by checking if it responds to reset endpoint."""
    start_time = time.time()
    base_url = launcher_url.rstrip('/')
    while time.time() - start_time < timeout:
        try:
            # Test if launcher responds (even if reset fails, endpoint should exist)
            response = requests.post(
                f"{base_url}/reset",
                json={"signal": "reset", "agent_id": "test", "backend_url": "http://localhost:9000", "extra_args": {}},
                timeout=2
            )
            # Any response (even 400) means launcher is running
            if response.status_code in [200, 400]:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def register_agent(agent_config: Dict[str, Any], backend_url: str) -> Optional[str]:
    """Register an agent with the backend and return agent_id."""
    # Ensure URLs have trailing slashes to match agent card format
    agent_url = f"http://localhost:{agent_config['agent_port']}/"
    launcher_url = f"http://localhost:{agent_config['launcher_port']}/"
    
    register_data = {
        "alias": agent_config["name"],
        "agent_url": agent_url,
        "launcher_url": launcher_url,
        "is_green": agent_config.get("is_green", False),
    }
    
    # Add participant_requirements for green agents
    if agent_config.get("is_green") and agent_config.get("participant_requirements"):
        register_data["participant_requirements"] = agent_config["participant_requirements"]
    
    try:
        response = requests.post(f"{backend_url}/agents", json=register_data, timeout=30)
        if response.status_code == 201:
            result = response.json()
            agent_id = result.get("agent_id")
            print(f"✅ Registered {agent_config['name']} with ID: {agent_id}")
            return agent_id
        else:
            print(f"❌ Failed to register {agent_config['name']}: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error registering {agent_config['name']}: {e}")
        return None


def create_battle(green_agent_id: str, opponents: list, backend_url: str) -> Optional[str]:
    """Create a battle and return battle_id."""
    battle_data = {
        "green_agent_id": green_agent_id,
        "opponents": opponents,
        "config": {}
    }
    
    try:
        response = requests.post(f"{backend_url}/battles", json=battle_data, timeout=30)
        if response.status_code == 201:
            result = response.json()
            battle_id = result.get("battle_id")
            print(f"✅ Created battle with ID: {battle_id}")
            return battle_id
        else:
            print(f"❌ Failed to create battle: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating battle: {e}")
        return None


def wait_for_battle_result(battle_id: str, backend_url: str, max_wait: int = MAX_WAIT_TIME) -> Optional[Dict[str, Any]]:
    """Poll battle status until finished or timeout."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{backend_url}/battles/{battle_id}", timeout=30)
            response.raise_for_status()
            battle = response.json()
            state = battle.get("state")
            print(f"Battle state: {state}")
            
            if state == "finished":
                return battle
            elif state == "error":
                print(f"Battle errored: {battle.get('error', 'Unknown error')}")
                return battle
                
            time.sleep(3)
        except requests.RequestException as e:
            print(f"Error polling battle: {e}")
            time.sleep(3)
    
    print(f"⏱️  Battle did not finish within {max_wait}s timeout")
    return None


def main():
    """Main launcher function."""
    project_dir = Path(__file__).parent
    agentbeats_dir = project_dir / "agentbeats"
    
    # Ensure we have the API keys
    env = os.environ.copy()
    if "OPENAI_API_KEY" not in env:
        print("❌ OPENAI_API_KEY not set in environment")
        return 1
    
    if "OPENROUTER_API_KEY" not in env:
        env["OPENROUTER_API_KEY"] = env["OPENAI_API_KEY"]  # Fallback
    
    processes = []
    agent_ids = {}
    
    try:
        # Start all agents
        print("=" * 60)
        print("Starting agents...")
        print("=" * 60)
        
        for agent_config in AGENTS:
            proc = start_agent(agent_config, agentbeats_dir, env)
            processes.append((agent_config["name"], proc, agent_config))
            time.sleep(2)  # Stagger startup
        
        # Wait for agents and launchers to be ready
        print("\nWaiting for agents and launchers to be ready...")
        for agent_config in AGENTS:
            agent_url = f"http://localhost:{agent_config['agent_port']}"
            launcher_url = f"http://localhost:{agent_config['launcher_port']}"
            
            # Check both agent and launcher
            agent_ready = wait_for_agent_ready(agent_url, timeout=30) or wait_for_agent_ready(f"{agent_url}/", timeout=5)
            launcher_ready = wait_for_launcher_ready(launcher_url, timeout=30)
            
            if agent_ready and launcher_ready:
                print(f"✅ {agent_config['name']} (agent + launcher) is ready")
            elif agent_ready:
                print(f"⚠️  {agent_config['name']} agent ready but launcher may not be ready")
            elif launcher_ready:
                print(f"⚠️  {agent_config['name']} launcher ready but agent may not be ready")
            else:
                print(f"⚠️  {agent_config['name']} may not be ready, continuing anyway...")
        
        # Give agents extra time to fully initialize
        print("\nGiving agents additional time to initialize...")
        time.sleep(5)
        
        # Register agents with backend
        print("\n" + "=" * 60)
        print("Registering agents with backend...")
        print("=" * 60)
        
        for agent_config in AGENTS:
            agent_id = register_agent(agent_config, BACKEND_URL)
            if agent_id:
                agent_ids[agent_config["name"]] = agent_id
        
        if not agent_ids:
            print("❌ No agents registered successfully")
            return 1
        
        # Find green agent
        green_agent = next((a for a in AGENTS if a.get("is_green")), None)
        if not green_agent or green_agent["name"] not in agent_ids:
            print("❌ Green agent not found or not registered")
            return 1
        
        green_agent_id = agent_ids[green_agent["name"]]
        
        # Build opponents list based on participant_requirements
        opponents = []
        if green_agent.get("participant_requirements"):
            for req in green_agent["participant_requirements"]:
                participant_agent_name = req["participant_agent"]
                if participant_agent_name not in agent_ids:
                    print(f"⚠️  Participant agent {participant_agent_name} not found in registered agents")
                    continue
                
                opponents.append({
                    "name": req["name"],  # Use the 'name' from participant_requirements (e.g., "guardrail_generator")
                    "agent_id": agent_ids[participant_agent_name],  # Use the registered agent_id
                    "role": req["role"],  # Use the role from participant_requirements
                })
        else:
            # Fallback: build opponents list without participant_requirements
            for agent_config in AGENTS:
                if agent_config.get("is_green"):
                    continue
                if agent_config["name"] not in agent_ids:
                    continue
                
                role = "blue_agent" if "blue" in agent_config["name"].lower() else "red_agent"
                opponents.append({
                    "name": agent_config["name"],
                    "agent_id": agent_ids[agent_config["name"]],
                    "role": role,
                })
        
        if not opponents:
            print("❌ No opponents found")
            return 1
        
        # Create battle
        print("\n" + "=" * 60)
        print("Creating battle...")
        print("=" * 60)
        
        battle_id = create_battle(green_agent_id, opponents, BACKEND_URL)
        if not battle_id:
            return 1
        
        battle_url = f"{FRONTEND_URL}/battles/{battle_id}"
        print(f"\n🎯 Battle URL: {battle_url}")
        
        # Wait for battle to complete
        print("\n" + "=" * 60)
        print("Waiting for battle to complete...")
        print("=" * 60)
        
        result = wait_for_battle_result(battle_id, BACKEND_URL, max_wait=MAX_WAIT_TIME)
        
        if result:
            print("\n" + "=" * 60)
            print("BATTLE RESULT")
            print("=" * 60)
            print(json.dumps(result, indent=2))
            return 0
        else:
            print("\n⏱️  Battle did not complete within timeout")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1
    finally:
        # Cleanup: terminate all agent processes
        print("\n" + "=" * 60)
        print("Stopping agents...")
        print("=" * 60)
        
        for name, proc, _ in processes:
            if proc.poll() is None:
                print(f"Terminating {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        
        print("✅ All agents stopped")


if __name__ == "__main__":
    exit(main())


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
BACKEND_URL = "http://127.0.0.1:9000"
FRONTEND_URL = "http://localhost:5173"  # User-facing URL, keep localhost for display
MAX_WAIT_TIME = 900  # seconds (15 minutes for full episode execution)

# Agent configurations - using ALFWorld green agent from scenario.toml
AGENTS = [
    {
        "name": "[ALFWorld] Green Agent",
        "card": "agents/green_agent/agent_card_clean.toml",
        "launcher_host": "0.0.0.0",
        "launcher_port": 8335,
        "agent_host": "0.0.0.0",
        "agent_port": 8336,
        "model_type": "openai",
        "model_name": "gpt-4o-mini",
        "tools": ["agents/tools.py"],
        "mcp_servers": ["http://127.0.0.1:9001/sse", "http://127.0.0.1:9002/sse"],
        "is_green": True,
        # Note: For ALFWorld battles, participant requirements depend on your battle setup
        # You can add participant_requirements here if needed for multi-agent battles
        "participant_requirements": [{"name": "opponent_agent", "role": "red_agent", "participant_agent": "[ALFWorld] White Agent", "required": True}]
    },
    {
        "name": "[ALFWorld] White Agent",
        "card": "agents/white_agent_card.toml",
        "launcher_host": "0.0.0.0",
        "launcher_port": 8060,
        "agent_host": "0.0.0.0",
        "agent_port": 8061,
        "model_type": "openai",
        "model_name": "gpt-4o-mini",
        "tools": ["agents/tools.py"],
        "mcp_servers": ["http://127.0.0.1:9001/sse", "http://127.0.0.1:9002/sse"],
        "is_green": False,
    },
]


def start_agent(agent_config: Dict[str, Any], project_dir: Path, env: dict) -> subprocess.Popen:
    """Start an agent using agentbeats run command."""
    # Card paths are relative to project directory
    card_path = project_dir / agent_config["card"]
    if not card_path.exists():
        raise FileNotFoundError(f"Agent card not found: {card_path}")
    
    cmd_parts = [
        "agentbeats", "run", str(card_path),
        "--launcher_host", agent_config["launcher_host"],
        "--launcher_port", str(agent_config["launcher_port"]),
        "--agent_host", agent_config["agent_host"],
        "--agent_port", str(agent_config["agent_port"]),
        "--model_type", agent_config["model_type"],
        "--model_name", agent_config["model_name"],
    ]
    
    if agent_config.get("tools"):
        for tool in agent_config["tools"]:
            tool_path = project_dir / tool
            if not tool_path.exists():
                raise FileNotFoundError(f"Tool file not found: {tool_path}")
            cmd_parts.extend(["--tool", str(tool_path)])
    
    if agent_config.get("mcp_servers"):
        for mcp in agent_config["mcp_servers"]:
            cmd_parts.extend(["--mcp", mcp])
    
    cmd = " ".join(cmd_parts)
    print(f"Starting {agent_config['name']}: {cmd}")
    
    # Redirect output to files for debugging
    log_file = open(f"{agent_config['name'].replace(' ', '_').lower()}.log", "w")
    
    # Add local agentbeats to PYTHONPATH
    env_copy = env.copy()
    agentbeats_src = project_dir / "agentbeats" / "src"
    if agentbeats_src.exists():
        current_pythonpath = env_copy.get("PYTHONPATH", "")
        env_copy["PYTHONPATH"] = f"{agentbeats_src}:{current_pythonpath}"
        print(f"Added {agentbeats_src} to PYTHONPATH for {agent_config['name']}")

    # Run from project directory so relative paths work
    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=str(project_dir),
        env=env_copy,
        stdout=log_file,
        stderr=subprocess.STDOUT,
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
                json={"signal": "reset", "agent_id": "test", "backend_url": "http://127.0.0.1:9000", "extra_args": {}},
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
    # Agent URL has trailing slash to match agent card format
    agent_url = f"http://127.0.0.1:{agent_config['agent_port']}/"
    # Launcher URL should NOT have trailing slash - backend appends /reset to it
    launcher_url = f"http://127.0.0.1:{agent_config['launcher_port']}"
    
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


def start_backend(project_dir: Path, env: dict) -> subprocess.Popen:
    """Start the AgentBeats backend and MCP server."""
    # Use agentbeats command directly, assuming it's in the PATH (like the agents)
    cmd = "agentbeats run_backend --host 127.0.0.1 --backend_port 9000 --mcp_port 9001"
    print(f"Starting Backend: {cmd}")
    
    log_file = open("agentbeats/backend_nohup.log", "w")
    
    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=str(project_dir),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


def start_mcp_server(project_dir: Path, env: dict) -> subprocess.Popen:
    """Start the custom ALFWorld MCP server on port 9002."""
    mcp_server_path = project_dir / "mcp_server.py"
    if not mcp_server_path.exists():
        raise FileNotFoundError(f"MCP server not found: {mcp_server_path}")
    
    # Use the miniforge Python which has the required dependencies (docker, fastmcp, etc.)
    python_path = Path.home() / "miniforge3" / "bin" / "python3.12"
    if not python_path.exists():
        # Fallback to whatever python3 is available
        python_path = "python3"
    cmd = f"{python_path} {mcp_server_path} --port 9002"
    print(f"Starting MCP Server: {cmd}")
    
    log_file = open("mcp_server.log", "w")
    
    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=str(project_dir),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


def wait_for_mcp_server_ready(mcp_url: str, timeout: int = 30) -> bool:
    """Wait for MCP server to be ready."""
    import time
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(mcp_url.replace("/sse", ""), timeout=2)
            # SSE endpoint might not respond to GET but server is up
            return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def wait_for_backend_ready(backend_url: str, timeout: int = 30) -> bool:
    """Wait for backend to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{backend_url}/health", timeout=2)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def cleanup_ports(ports: list[int]):
    """Kill processes using specified ports to avoid binding conflicts."""
    import subprocess
    for port in ports:
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        subprocess.run(["kill", "-9", pid], check=False)
                        print(f"Killed process {pid} on port {port}")
                    except Exception:
                        pass
        except Exception:
            pass


def cleanup_docker_containers():
    """Remove all old ALFWorld Docker containers to start fresh."""
    try:
        import docker
    except ImportError:
        print("⚠️  Docker module not available, skipping container cleanup")
        return
    
    try:
        # Try to connect to Docker
        client = docker.from_env()
        client.ping()
    except Exception as e:
        print(f"⚠️  Could not connect to Docker: {e}")
        return
    
    try:
        # Find all containers with alfworld_ prefix
        all_containers = client.containers.list(all=True)
        alfworld_containers = [c for c in all_containers if c.name.startswith("alfworld_")]
        
        if alfworld_containers:
            print(f"Found {len(alfworld_containers)} old ALFWorld container(s), removing...")
            for container in alfworld_containers:
                try:
                    if container.status == "running":
                        print(f"  Stopping container: {container.name}")
                        container.stop(timeout=5)
                    print(f"  Removing container: {container.name}")
                    container.remove()
                except Exception as e:
                    print(f"  ⚠️  Could not remove {container.name}: {e}")
            print("✅ Old ALFWorld containers cleaned up")
        else:
            print("✅ No old ALFWorld containers found")
    except Exception as e:
        print(f"⚠️  Error during Docker cleanup: {e}")


def main():
    """Main launcher function."""
    project_dir = Path(__file__).parent
    # AgentBeats is in a separate directory at ~/agentbeats
    agentbeats_dir = Path.home() / "agentbeats"
    if not agentbeats_dir.exists():
        # Fallback: check if it's in the project directory
        agentbeats_dir = project_dir / "agentbeats"
        if not agentbeats_dir.exists():
            print(f"❌ AgentBeats directory not found at {Path.home() / 'agentbeats'} or {project_dir / 'agentbeats'}")
            return 1
    
    # Clean up old Docker containers and processes before starting fresh
    print("=" * 60)
    print("Cleaning up old resources...")
    print("=" * 60)
    
    # Clean up old ALFWorld Docker containers
    cleanup_docker_containers()
    
    # Clean up any processes using agent ports
    agent_ports = [8335, 8336, 8060, 8061]
    print("\nCleaning up any processes on agent ports...")
    cleanup_ports(agent_ports)
    time.sleep(1)  # Give ports time to free up
    
    print("\n✅ Cleanup complete, starting fresh...\n")
    
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
        # Start Backend
        print("=" * 60)
        print("Starting Backend...")
        print("=" * 60)
        backend_proc = start_backend(project_dir, env)
        processes.append(("Backend", backend_proc, {}))
        
        if wait_for_backend_ready(BACKEND_URL):
            print("✅ Backend is ready")
        else:
            print("❌ Backend failed to start")
            return 1

        # Start custom MCP server for ALFWorld tools
        print("=" * 60)
        print("Starting MCP Server...")
        print("=" * 60)
        mcp_proc = start_mcp_server(project_dir, env)
        processes.append(("MCP Server", mcp_proc, {}))
        time.sleep(3)  # Give MCP server time to start
        print("✅ MCP Server started on port 9002")

        # Start all agents
        print("=" * 60)
        print("Starting agents...")
        print("=" * 60)
        
        for agent_config in AGENTS:
            proc = start_agent(agent_config, project_dir, env)
            processes.append((agent_config["name"], proc, agent_config))
            time.sleep(2)  # Stagger startup
        
        # Wait for agents and launchers to be ready
        print("\nWaiting for agents and launchers to be ready...")
        for agent_config in AGENTS:
            agent_url = f"http://127.0.0.1:{agent_config['agent_port']}"
            launcher_url = f"http://127.0.0.1:{agent_config['launcher_port']}"
            
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
        
        # Allow backend time to process registrations before battle creation (tau-bench coordination principle)
        print("\nAllowing backend to process agent registrations...")
        time.sleep(2)
        
        # Final verification: Ensure agents are still responsive before battle creation
        print("Performing final agent health check...")
        for agent_config in AGENTS:
            agent_url = f"http://127.0.0.1:{agent_config['agent_port']}"
            if not wait_for_agent_ready(agent_url, timeout=10):
                print(f"⚠️  Warning: {agent_config['name']} agent endpoint not responding before battle creation")
            else:
                print(f"✅ {agent_config['name']} agent endpoint confirmed responsive")
        
        # Sanity check: Verify agent card endpoints are accessible via IPv4 before battle creation
        print("\nPerforming IPv4 connectivity sanity check...")
        sanity_check_passed = True
        for agent_config in AGENTS:
            try:
                response = requests.get(
                    f"http://127.0.0.1:{agent_config['agent_port']}/.well-known/agent-card.json",
                    timeout=2
                )
                if response.status_code == 200:
                    print(f"✅ {agent_config['name']} agent card accessible via IPv4 (127.0.0.1:{agent_config['agent_port']})")
                else:
                    print(f"❌ {agent_config['name']} agent card returned status {response.status_code}")
                    sanity_check_passed = False
            except Exception as e:
                print(f"❌ {agent_config['name']} agent card check failed: {e}")
                sanity_check_passed = False
        
        if not sanity_check_passed:
            print("\n❌ Sanity check failed - agent endpoints not accessible via IPv4")
            print("   This may cause 'Failed to notify green agent' errors")
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


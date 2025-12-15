# ALFWorld Green Agent - Complete Architecture Rundown

## Table of Contents
1. [Overview](#overview)
2. [Repository Structure](#repository-structure)
3. [Core Components](#core-components)
4. [Agent Integration](#agent-integration)
5. [Battle Flow](#battle-flow)
6. [Communication Protocols](#communication-protocols)
7. [File-by-File Breakdown](#file-by-file-breakdown)

---

## Overview

This repository implements an **ALFWorld Green Agent** for the AgentBeats battle framework. The Green Agent orchestrates ALFWorld text-based household chore tasks by:
- Setting up isolated Docker environments per battle
- Coordinating with a White Agent (opponent) that plays the game
- Managing task execution, scoring, and reporting

### Key Technologies
- **AgentBeats**: Framework for multi-agent battles
- **A2A Protocol**: Agent-to-Agent communication protocol
- **ALFWorld**: Text-based household simulation environment
- **Docker**: Containerization for isolated environments
- **FastAPI**: REST API for ALFWorld environment control
- **FastMCP**: Model Context Protocol for tool exposure

---

## Repository Structure

```
alfworld-greenagent/
├── agents/                          # Agent definitions and tools
│   ├── tools.py                    # Core tool implementations (Docker, episode execution)
│   ├── green_agent/
│   │   └── agent_card_clean.toml  # Green Agent configuration
│   ├── white_agent_card.toml       # White Agent configuration
│   └── README.md                   # Agent documentation
│
├── launch_battle.py                # Main entry point - orchestrates entire battle
├── start_agents.py                 # Alternative launcher (terminal-based)
├── scenario.toml                   # Scenario configuration
│
├── mcp_server.py                   # Custom MCP server (port 9002) for ALFWorld tools
├── alfworld_api.py                 # FastAPI REST server (runs in Docker)
├── Dockerfile                      # Docker image with ALFWorld + REST API
│
├── tasks/                          # Task JSON definitions
│   ├── cleanliness-v0.json
│   └── test_task.json
│
└── agentbeats/                     # AgentBeats backend code (separate repo)
    └── src/
        └── backend/
            └── a2a_client.py      # Battle notification and A2A client
```

---

## Core Components

### 1. **AgentBeats Backend** (`~/agentbeats/`)
- **Location**: Separate repository, typically at `~/agentbeats/`
- **Purpose**: Central orchestration server
- **Components**:
  - Backend API (port 9000): Manages battles, agents, and state
  - Built-in MCP Server (port 9001): Provides standard tools (`update_battle_process`, `report_on_battle_end`)
  - Battle queue processor: Creates and monitors battles

### 2. **ALFWorld Green Agent**
- **Role**: Battle orchestrator and evaluator
- **Location**: `agents/green_agent/agent_card_clean.toml`
- **Responsibilities**:
  1. Receives `battle_start` notification from backend
  2. Sets up Docker environment for ALFWorld
  3. Generates/loads task JSON
  4. Runs episode by coordinating with White Agent
  5. Reports results and cleans up

### 3. **ALFWorld White Agent**
- **Role**: Game player (opponent agent)
- **Location**: `agents/white_agent_card.toml`
- **Responsibilities**:
  1. Receives observations from ALFWorld environment
  2. Decides on actions (e.g., "go to kitchen", "pick up apple")
  3. Executes actions to complete the task

### 4. **ALFWorld MCP Server** (`mcp_server.py`)
- **Purpose**: Provides ALFWorld-specific tools via MCP
- **Port**: 9002 (SSE endpoint: `http://127.0.0.1:9002/sse`)
- **Tools**:
  - `run_terminal_command_in_docker`: Execute commands in battle containers

### 5. **ALFWorld REST API** (`alfworld_api.py`)
- **Purpose**: Provides REST endpoints for ALFWorld environment control
- **Runs**: Inside Docker container (port 8000 mapped to host)
- **Endpoints**:
  - `POST /episode/reset`: Reset episode with task
  - `POST /episode/step`: Execute action and get next observation
  - `GET /health`: Health check

---

## Agent Integration

### How Agents Are Integrated

#### 1. **Agent Card System** (A2A Protocol)
Each agent has a `.toml` file (agent card) that defines:
- **Name & Description**: Instructions for the LLM
- **URL**: `http://127.0.0.1:{port}`
- **Tools**: Python files with `@tool` decorated functions
- **MCP Servers**: SSE endpoints that provide additional tools
- **Capabilities**: Streaming support, input/output modes

**Example Agent Card Structure**:
```toml
name = "[ALFWorld] Green Agent"
description = "You are the Green Agent orchestrating..."
url = "http://127.0.0.1:8336"
host = "0.0.0.0"
port = 8336
capabilities.streaming = true
```

#### 2. **Tool Integration** (`agents/tools.py`)
Tools are Python functions decorated with `@tool` from `agentbeats`:

```python
from agentbeats import tool

@tool
async def setup_docker_env(battle_id: str, ...) -> str:
    """Setup Docker container with ALFWorld environment."""
    # Implementation
```

**Key Tools**:
- `setup_docker_env`: Creates Docker container with ALFWorld API
- `destroy_docker_env`: Cleans up container
- `generate_alfworld_task`: Loads task JSON
- `run_episode`: Executes episode by coordinating with White Agent
- `talk_to_purple_or_white_agent`: A2A communication helper

#### 3. **MCP Server Integration**
MCP servers expose tools via SSE (Server-Sent Events):
- **Backend MCP** (9001): Standard battle tools
- **ALFWorld MCP** (9002): ALFWorld-specific tools

Agents connect to MCP servers via `--mcp http://127.0.0.1:9001/sse`

#### 4. **Agent Launch Process**
When `launch_battle.py` starts an agent:
1. Reads agent card from `.toml` file
2. Executes: `agentbeats run <card.toml> --tool <tools.py> --mcp <mcp_url>`
3. Agent process:
   - Loads agent card
   - Registers tools from `tools.py` and MCP servers
   - Starts HTTP server on `agent_port` (A2A protocol)
   - Starts launcher server on `launcher_port` (for reset/management)

#### 5. **Agent Registration**
After agents start, `launch_battle.py`:
1. Waits for agent/launcher to be ready (health checks)
2. Registers with backend: `POST /agents` with:
   - `agent_url`: `http://127.0.0.1:{agent_port}/`
   - `launcher_url`: `http://127.0.0.1:{launcher_port}`
   - `is_green`: Boolean flag
3. Backend stores agent info and assigns `agent_id`

---

## Battle Flow

### Complete Battle Execution Sequence

```
1. launch_battle.py starts
   ├── Cleanup: Remove old Docker containers, kill processes on ports
   ├── Start Backend (port 9000)
   ├── Start MCP Server (port 9002)
   ├── Start Green Agent (port 8336) + Launcher (port 8335)
   └── Start White Agent (port 8061) + Launcher (port 8060)

2. Register Agents
   ├── POST /agents for Green Agent → get green_agent_id
   └── POST /agents for White Agent → get white_agent_id

3. Create Battle
   └── POST /battles with green_agent_id + opponents

4. Backend Processes Battle
   ├── Queues battle
   ├── Resets agents via launchers (POST /reset)
   └── Sends battle_start notification to Green Agent

5. Green Agent Receives battle_start
   ├── Acknowledges: "Battle received, starting setup..."
   ├── Calls: update_battle_process()
   ├── Calls: generate_alfworld_task() → gets task JSON path
   ├── Calls: setup_docker_env() → starts Docker container with ALFWorld API
   ├── Calls: run_episode() → coordinates episode execution
   │   ├── Resets episode via REST API (POST /episode/reset)
   │   ├── Gets initial observation
   │   ├── Loop (up to step_limit steps):
   │   │   ├── Sends observation to White Agent via A2A
   │   │   ├── White Agent responds with action
   │   │   ├── Executes action via REST API (POST /episode/step)
   │   │   └── Gets next observation
   │   └── Returns: success, steps, reward
   ├── Calls: update_battle_process()
   ├── Calls: report_on_battle_end()
   └── Calls: destroy_docker_env()

6. Backend Monitors Battle
   └── Updates battle state: queued → running → finished/error

7. Cleanup
   └── launch_battle.py terminates all processes
```

---

## Communication Protocols

### 1. **A2A (Agent-to-Agent) Protocol**
- **Purpose**: Direct agent communication
- **Usage**: Green Agent talks to White Agent during episodes
- **Implementation**: Uses `A2AClient` from `a2a.client`
- **Example**: Green Agent sends observation → White Agent responds with action

### 2. **Backend HTTP API**
- **Base URL**: `http://127.0.0.1:9000`
- **Endpoints**:
  - `POST /agents`: Register agent
  - `POST /battles`: Create battle
  - `GET /battles/{battle_id}`: Get battle status
  - `POST /battles/{battle_id}`: Post battle events (via MCP tools)

### 3. **ALFWorld REST API** (in Docker)
- **Base URL**: `http://127.0.0.1:{dynamically_assigned_port}`
- **Endpoints**:
  - `POST /episode/reset?session_id={battle_id}`: Reset episode
  - `POST /episode/step?session_id={battle_id}&action={action}`: Step episode
  - `GET /health`: Health check

### 4. **MCP (Model Context Protocol)**
- **Transport**: SSE (Server-Sent Events)
- **Backend MCP**: `http://127.0.0.1:9001/sse`
- **ALFWorld MCP**: `http://127.0.0.1:9002/sse`
- **Purpose**: Expose tools to agents

---

## File-by-File Breakdown

### `launch_battle.py` ⭐ **Main Entry Point**
**Purpose**: Orchestrates entire battle from start to finish

**Key Functions**:
- `start_backend()`: Starts AgentBeats backend
- `start_mcp_server()`: Starts custom ALFWorld MCP server
- `start_agent()`: Launches an agent using `agentbeats run`
- `register_agent()`: Registers agent with backend
- `create_battle()`: Creates battle via backend API
- `wait_for_battle_result()`: Polls battle status
- `cleanup_ports()` / `cleanup_docker_containers()`: Cleanup helpers

**Flow**:
1. Cleanup old resources
2. Start backend, MCP server, agents
3. Wait for readiness
4. Register agents
5. Create battle
6. Monitor until completion
7. Cleanup

**Key Configuration**:
- Uses IPv4 (`127.0.0.1`) for all inter-process communication (fixes IPv6 issues)
- Ports: Backend (9000), MCP (9002), Green (8335/8336), White (8060/8061)
- Max wait time: 900 seconds (15 minutes)

---

### `agents/tools.py` ⭐ **Core Tool Implementation**
**Purpose**: Provides all tools that agents can call

**Global State**:
- `_battle_containers`: Tracks Docker containers per battle
- `_episode_in_progress`: Prevents premature container cleanup
- `_episode_locks`: Prevents parallel episodes for same battle
- `_attack_cumulative_times`: Tracks opponent communication time

**Key Tools**:

#### `setup_docker_env(battle_id, image=None, port=None, build_image=False)`
- Creates Docker container named `alfworld_{battle_id}`
- Uses image `alfworld-api:local` (custom image with REST API)
- Maps container port 8000 to dynamic host port
- Mounts task directory for container access
- Waits for API health check
- Returns API URL

#### `destroy_docker_env(battle_id)`
- Stops and removes Docker container
- Waits for episode to complete if in progress

#### `generate_alfworld_task(task_id, battle_id)`
- Loads task JSON from `tasks/` directory
- Returns file path

#### `run_episode(opponent_agent_url, task_json_path, battle_id, step_limit=30, api_url=None)`
- **Core episode execution function**
- Resolves White Agent card via A2A
- Resets episode via REST API
- Loop:
  1. Send observation to White Agent via A2A
  2. Get action from White Agent
  3. Validate/clean action
  4. Execute via REST API step endpoint
  5. Update observation
- Returns: success, steps, reward, action_log

#### `talk_to_purple_or_white_agent(query, target_url, battle_id, timeout_seconds=120.0)`
- Helper for A2A communication
- Uses `A2AClient` to send message and stream response
- Includes retry logic

**Helper Classes**:
- `A2AMessenger`: Wraps A2A client with retry logic and timing
- `_get_httpx_client()`: Reusable HTTP client

---

### `agents/green_agent/agent_card_clean.toml` ⭐ **Green Agent Definition**
**Purpose**: LLM instructions and configuration for Green Agent

**Key Sections**:
- **Description**: Detailed instructions for battle orchestration
- **REQUIRED EXECUTION SEQUENCE**: Step-by-step tool call sequence
- **URL/Port**: `http://127.0.0.1:8336` (agent), launcher on 8335
- **Capabilities**: Streaming enabled

**Execution Sequence** (when `battle_start` received):
1. Acknowledge receipt
2. `update_battle_process()` - log start
3. `generate_alfworld_task()` - get task JSON
4. `setup_docker_env()` - start Docker container
5. `run_episode()` - execute episode with White Agent
6. `update_battle_process()` - log completion
7. `report_on_battle_end()` - finalize battle
8. `destroy_docker_env()` - cleanup

---

### `agents/white_agent_card.toml` ⭐ **White Agent Definition**
**Purpose**: LLM instructions for White Agent (game player)

**Key Sections**:
- **Description**: Instructions for playing ALFWorld tasks
- **Actions**: Navigation, interaction, placement, examination
- **URL/Port**: `http://127.0.0.1:8061` (agent), launcher on 8060

**Behavior**:
- Receives observations from Green Agent
- Responds with single action command
- Adapts plan based on environment responses

---

### `mcp_server.py` ⭐ **Custom MCP Server**
**Purpose**: Provides ALFWorld-specific tools via MCP

**Implementation**:
- Uses `FastMCP` library
- Exposes SSE endpoint on port 9002
- Tools:
  - `run_terminal_command_in_docker`: Execute commands in containers

**Note**: `update_battle_process` and `report_on_battle_end` come from backend MCP (port 9001) to avoid duplicates

---

### `alfworld_api.py` ⭐ **REST API Server** (Runs in Docker)
**Purpose**: Provides REST endpoints for ALFWorld environment control

**Implementation**:
- FastAPI application
- Runs inside Docker container (port 8000)
- Per-session environment instances: `ENVIRONMENTS[session_id]`

**Key Endpoints**:

#### `POST /episode/reset?session_id={battle_id}`
- Creates/resets ALFWorld environment for session
- Loads task JSON (from mounted volume or task_id)
- Returns: observation, info (admissible_commands), task_meta

#### `POST /episode/step?session_id={battle_id}&action={action}`
- Executes action in ALFWorld environment
- Returns: observation, reward, done, info

#### `GET /health`
- Health check endpoint

**Session Management**:
- Each `battle_id` is a session
- Environments persist for duration of battle

---

### `Dockerfile`
**Purpose**: Builds Docker image with ALFWorld + REST API

**Contents**:
- Base image: `vzhong/alfworld:latest` (official ALFWorld image)
- Copies `alfworld_api.py` into container
- Installs FastAPI dependencies
- Runs `alfworld_api.py` as main process (via `CMD`)

**Image Name**: `alfworld-api:local`

---

### `scenario.toml`
**Purpose**: Scenario configuration file (not actively used by `launch_battle.py`)

**Contents**:
- Backend URL
- Agent definitions (similar to `launch_battle.py` AGENTS list)
- Launch configuration

**Note**: `launch_battle.py` has hardcoded agent configs, but `scenario.toml` provides reference

---

### `start_agents.py`
**Purpose**: Alternative launcher - opens agents in separate terminal windows

**Features**:
- Can launch agents in separate terminals (macOS/Linux/Windows)
- Can launch in current terminal
- Shows agent commands without running

**Usage**: `python start_agents.py [--current] [--show]`

---

### `run_battle_cli.py`
**Purpose**: CLI interface for battle management (if exists)

---

### `test_alfworld_*.py`
**Purpose**: Test files for ALFWorld integration

---

## AgentBeats Backend Integration

### Backend Location
- **Path**: `~/agentbeats/src/` (separate repository)
- **Key File**: `backend/a2a_client.py` (recently modified for resilience)

### Battle Notification Flow

1. **Backend creates battle** → Queues it
2. **Battle processor** picks up battle
3. **Resets agents** via launchers (`POST /reset`)
4. **Notifies Green Agent** via `notify_green_agent()`:
   - Sends `battle_start` message via A2A
   - Uses non-streaming mode (returns immediately on HTTP 200/202)
   - If timeout, polls battle events to check if agent is active (resilience check)

### Recent Fixes (in `~/agentbeats/src/backend/a2a_client.py`)

**Problem**: "Failed to notify green agent" errors when agent was active but slow

**Solution**:
1. **Non-streaming notify**: `send_message_to_agent(..., stream_response=False)`
   - Returns immediately after HTTP 200/202 (doesn't wait for response body)
   - Short timeout (2 seconds)
   
2. **Resilience polling**: If notify times out, polls battle events:
   - Calls `GET /battles/{battle_id}` up to 10 times
   - Checks if green agent posted events after "Battle started"
   - If yes, treats notify as successful

3. **IPv4 fix**: All URLs use `127.0.0.1` instead of `localhost` (prevents IPv6 issues)

---

## Key Design Patterns

### 1. **Per-Battle Isolation**
- Each battle gets its own Docker container: `alfworld_{battle_id}`
- Containers are destroyed after battle completes
- Prevents interference between concurrent battles

### 2. **A2A Communication**
- Green Agent coordinates with White Agent via A2A protocol
- Uses streaming messages for real-time communication
- Includes retry logic and fallback responses

### 3. **REST API for Environment Control**
- ALFWorld environment runs in Docker
- Controlled via REST API (not direct Python imports)
- Enables container isolation and scalability

### 4. **Tool-Based Architecture**
- Agents call tools (Python functions) to perform actions
- Tools are decorated with `@tool` from `agentbeats`
- Tools can be defined locally (`tools.py`) or via MCP servers

### 5. **MCP Server Pattern**
- Backend MCP: Standard battle tools
- Custom MCP: Domain-specific tools (ALFWorld)
- Agents connect to multiple MCP servers for tool discovery

---

## Network Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    launch_battle.py                      │
│              (Orchestrates everything)                   │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Backend    │   │  MCP Server  │   │   Agents     │
│  :9000       │   │  :9002       │   │  :8335/8336  │
│              │   │              │   │  :8060/8061  │
└──────────────┘   └──────────────┘   └──────────────┘
        │                  │                  │
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
                ┌────────────────────┐
                │  Docker Container  │
                │  alfworld_{id}     │
                │  :8000 → :{port}   │
                │  (ALFWorld API)    │
                └────────────────────┘
```

**Communication Paths**:
- `launch_battle.py` ↔ Backend: HTTP API
- Backend ↔ Agents: A2A protocol (HTTP)
- Agents ↔ MCP Servers: SSE (Server-Sent Events)
- Green Agent ↔ White Agent: A2A protocol (during episodes)
- Tools ↔ Docker: Docker SDK
- Tools ↔ ALFWorld API: REST API (HTTP)

---

## Environment Variables

**Required**:
- `OPENAI_API_KEY`: API key for LLM (used by agents)

**Optional**:
- `OPENROUTER_API_KEY`: Alternative API (falls back to OPENAI_API_KEY)

---

## Port Allocation

| Service | Port | Purpose |
|---------|------|---------|
| Backend | 9000 | Main API server |
| Backend MCP | 9001 | Standard tools (SSE) |
| ALFWorld MCP | 9002 | ALFWorld tools (SSE) |
| Green Launcher | 8335 | Agent management |
| Green Agent | 8336 | A2A endpoint |
| White Launcher | 8060 | Agent management |
| White Agent | 8061 | A2A endpoint |
| ALFWorld API | 8001-8999 | Dynamic assignment per battle |

---

## Error Handling & Resilience

### Recent Improvements

1. **IPv4/IPv6 Fix**:
   - All inter-process URLs use `127.0.0.1` instead of `localhost`
   - Prevents IPv6 resolution to `::1` when agent listens on IPv4

2. **Notify Resilience**:
   - Short timeout (2s) for notify calls
   - If timeout, polls battle events to check agent activity
   - Prevents false failures when agent is active but slow

3. **Container Management**:
   - Prevents duplicate container creation
   - Waits for episode completion before cleanup
   - Handles container errors gracefully

4. **Action Validation**:
   - Validates actions against admissible commands
   - Partial matching for better compatibility
   - Fallback to safe action if validation fails

---

## Testing & Debugging

### Log Files
- `agentbeats/backend_nohup.log`: Backend logs
- `[alfworld]_green_agent.log`: Green Agent logs
- `[alfworld]_white_agent.log`: White Agent logs
- `mcp_server.log`: MCP server logs

### Common Issues
1. **"Failed to notify green agent"**: Usually means agent crashed or slow to respond (now handles with resilience check)
2. **Port conflicts**: `launch_battle.py` now cleans up ports automatically
3. **Docker issues**: Check Docker Desktop is running, check container logs
4. **IPv6 issues**: Fixed by using `127.0.0.1` everywhere

---

## Summary

This repository implements a complete battle orchestration system for ALFWorld using the AgentBeats framework. The Green Agent acts as a coordinator that sets up environments, manages episodes, and evaluates results, while the White Agent plays the actual game. The system uses Docker for isolation, A2A protocol for agent communication, and REST APIs for environment control.

**Key Innovation**: The Green Agent doesn't play the game itself—it orchestrates by coordinating with a White Agent that makes the actual game decisions, enabling evaluation of different agent strategies.

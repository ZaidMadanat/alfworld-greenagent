# AgentBeats ALFWorld Green Agent

This project implements the ALFWorld Green Agent for AgentBeats battles.

## Setup

1.  **Install Dependencies**: Ensure you have `agentbeats` installed and the environment variables set.
    ```bash
    export OPENAI_API_KEY="your_key"
    export OPENROUTER_API_KEY="your_key" # Optional, falls back to OPENAI_API_KEY
    ```

2.  **Agent Configuration**:
    - Green Agent: `agents/green_agent/agent_card_clean.toml`
    - White Agent: `agents/white_agent_card.toml`
    - Tools: `agents/tools.py`

## Running a Battle

The easiest way to run a full battle simulation (Green Agent vs White Agent) is using the `launch_battle.py` script. This script handles:
- Starting the AgentBeats backend and MCP server.
- Starting the Green and White agents.
- Registering agents with the backend.
- Creating a battle.
- Monitoring the battle until completion.

### Command

```bash
python3 launch_battle.py
```

### Prerequisites

- **Python 3.10+**
- **Docker Desktop**: Must be installed and **running**. AgentBeats uses Docker to create isolated environments for the agents.
- **OpenAI API Key**: Required for the agents to function.

### Logs

- **Backend Logs**: `agentbeats/backend_nohup.log`
- **Green Agent Logs**: `[alfworld]_green_agent.log`
- **White Agent Logs**: `[alfworld]_white_agent.log`

## Troubleshooting

- **"Failed to notify green agent"**: This usually means the Green Agent crashed or failed to handle the `battle_start` message. Check `[alfworld]_green_agent.log` for errors.
- **Connection Refused**: Ensure no other processes are using ports 9000, 9001, 8335, 8336, 8060, 8061. The `launch_battle.py` script attempts to manage this, but you may need to manually kill processes:
    ```bash
    lsof -ti:9000,9001,8335,8336,8060,8061 | xargs kill -9
    ```

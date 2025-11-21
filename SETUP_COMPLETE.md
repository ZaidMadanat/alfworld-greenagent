# ALFWorld Green Agent Setup - Complete ✅

All configuration issues have been fixed! Here's what was done and how to run battles.

## ✅ Fixed Issues

### 1. **ALFWORLD_TASK_DIR** - Added definition in `agents/tools.py`
   - Defaults to `alfworld/data/seed_data`
   - Falls back to `./tasks` if ALFWorld structure doesn't match

### 2. **Remote IP Addresses** - Updated all to `localhost`
   - ✅ `agents/green_agent/agent_card_clean.toml`
   - ✅ `scenario.toml` 
   - ✅ `start_agents.py`
   - ✅ `mcp_server.py`
   - ✅ `launch_battle.py` (frontend URL)

### 3. **Missing Tools** - Added `report_on_battle_end` to MCP server
   - Added to `mcp_server.py` with proper endpoint handling

### 4. **Tool Functions** - Added `@tool` decorators to all functions
   - ✅ `setup_docker_env`
   - ✅ `destroy_docker_env`
   - ✅ `generate_alfworld_task`
   - ✅ `start_alfworld_server`
   - ✅ `get_attack_cumulative_time`
   - ✅ `reset_battle_timing`
   - ✅ `talk_to_purple_or_white_agent` (fixed A2A implementation)
   - ✅ `run_episode` (refactored to accept URLs instead of objects)

### 5. **Function Signatures** - Fixed return types
   - All tool functions now return strings (as required by AgentBeats)

## 🚀 How to Run Battles

### Prerequisites
1. **AgentBeats is running** (you confirmed this is working):
   - Backend: `http://localhost:9000`
   - Frontend: `http://localhost:5173`
   - AgentBeats MCP: `http://localhost:9001/sse`

2. **Start ALFWorld MCP Server** (in a new terminal):
```bash
cd /Users/rajeev/alfworld-greenagent
source /Users/rajeev/agentbeats/.venv/bin/activate
export OPENAI_API_KEY="sk-..."
python mcp_server.py --port 9002
```
This should be running at `http://localhost:9002/sse`

### Option 1: Start Green Agent Manually (Recommended for first run)

In a new terminal:
```bash
cd /Users/rajeev/alfworld-greenagent
source /Users/rajeev/agentbeats/.venv/bin/activate
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="$OPENAI_API_KEY"

# Start green agent
agentbeats run agents/green_agent/agent_card_clean.toml \
  --launcher_host 0.0.0.0 \
  --launcher_port 8335 \
  --agent_host 0.0.0.0 \
  --agent_port 8336 \
  --model_type openai \
  --model_name gpt-4o-mini \
  --tool agents/tools.py \
  --mcp http://localhost:9001/sse \
  --mcp http://localhost:9002/sse
```

Then:
1. Open `http://localhost:5173` in your browser
2. Register the green agent:
   - Agent URL: `http://localhost:8336/`
   - Launcher URL: `http://localhost:8335/`
   - Mark as "Green Agent"
3. Create a battle with the green agent

### Option 2: Use start_agents.py

```bash
cd /Users/rajeev/alfworld-greenagent
source /Users/rajeev/agentbeats/.venv/bin/activate
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="$OPENAI_API_KEY"

python start_agents.py  # Opens in separate terminals
# OR
python start_agents.py --current  # Runs in current terminal
```

### Option 3: Use scenario.toml

```bash
cd /Users/rajeev/alfworld-greenagent
source /Users/rajeev/agentbeats/.venv/bin/activate
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="$OPENAI_API_KEY"

agentbeats load_scenario scenario.toml
```

## 📝 Notes

- **ALFWorld Tasks**: Make sure you have task JSON files in:
  - `alfworld/data/seed_data/<task_id>.json`, OR
  - `./tasks/<task_id>.json`
  
  The default task_id is `cleanliness-v0` (from the agent card).

- **Agent Registration**: Green agents need to be marked as "is_green: true" when registering via the API/UI.

- **MCP Servers**: The green agent connects to:
  - `http://localhost:9001/sse` - AgentBeats default MCP
  - `http://localhost:9002/sse` - Your ALFWorld custom MCP

## 🐛 Troubleshooting

1. **Port conflicts**: Check if ports 8335, 8336, 8060, 8061, 9002 are already in use
2. **ALFWorld not found**: Make sure ALFWorld is installed in the `alfworld/` directory or update `ALFWORLD_ROOT` in `tools.py`
3. **Task files missing**: Create sample task JSON files or update `ALFWORLD_TASK_DIR` in `tools.py`
4. **Agent won't start**: Check that all dependencies are installed in the AgentBeats venv

## ✨ Next Steps

1. Start the ALFWorld MCP server
2. Start the green agent (Option 1 above)
3. Register it via the UI
4. Create and run your first battle!

All configuration issues are now fixed. The system should be ready to run battles! 🎉


# Quick Start Guide - ALFWorld Battles

## ✅ Fixed Issues

1. **AgentBeats path** - Fixed `launch_battle.py` to find agentbeats at `~/agentbeats`
2. **Dependencies** - Installed `docker` package in AgentBeats venv
3. **Agent paths** - Updated `launch_battle.py` to use your actual green agent

## 🚀 Running a Battle

### Option 1: Direct Green Agent Start (Simplest)

**Terminal 1 - Start ALFWorld MCP Server:**
```bash
cd ~/alfworld-greenagent
source ~/agentbeats/.venv/bin/activate
export OPENAI_API_KEY="sk-..."
python mcp_server.py --port 9002
```

**Terminal 2 - Start Green Agent:**
```bash
cd ~/alfworld-greenagent
source ~/agentbeats/.venv/bin/activate
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="$OPENAI_API_KEY"

agentbeats run agents/green_agent/agent_card_clean.toml \
  --launcher_port 8335 --agent_port 8336 \
  --model_type openai --model_name gpt-4o-mini \
  --tool agents/tools.py \
  --mcp http://localhost:9001/sse \
  --mcp http://localhost:9002/sse
```

**Terminal 3 - AgentBeats should already be running:**
- Backend: http://localhost:9000
- Frontend: http://localhost:5173
- MCP: http://localhost:9001/sse

**Then:**
1. Open http://localhost:5173 in browser
2. Register Green Agent:
   - Agent URL: `http://localhost:8336/`
   - Launcher URL: `http://localhost:8335/`
   - Check "Is Green Agent"
3. Create and start battle

### Option 2: Using launch_battle.py (Once AgentBeats is Running)

**Note:** `launch_battle.py` now only starts the green agent. You'll still need to create the battle via UI.

```bash
cd ~/alfworld-greenagent
source ~/agentbeats/.venv/bin/activate
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="$OPENAI_API_KEY"

python launch_battle.py
```

Then register and create battle via UI as above.

### Option 3: Using scenario.toml

```bash
cd ~/alfworld-greenagent
source ~/agentbeats/.venv/bin/activate
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="$OPENAI_API_KEY"

agentbeats load_scenario scenario.toml
```

## 📋 Prerequisites Checklist

- ✅ AgentBeats running (backend, frontend, MCP on ports 9000, 5173, 9001)
- ✅ ALFWorld MCP server running (port 9002)
- ✅ Docker package installed in venv
- ✅ Green agent card exists at `agents/green_agent/agent_card_clean.toml`
- ✅ Tools file exists at `agents/tools.py`

## ⚠️ Notes

- The green agent needs ALFWorld task JSON files in `alfworld/data/seed_data/` or `./tasks/`
- Default task_id is `cleanliness-v0` (from agent card)
- For multi-agent battles, you'll need participant agents configured

## 🐛 Troubleshooting

1. **"docker module not found"** - Already fixed, docker is installed
2. **"AgentBeats directory not found"** - Fixed, now looks in `~/agentbeats`
3. **"Agent card not found"** - Make sure you're in `~/alfworld-greenagent` directory
4. **Port conflicts** - Check ports 8335, 8336, 9002 are free


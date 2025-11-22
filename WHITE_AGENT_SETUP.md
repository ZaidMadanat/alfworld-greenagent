# ✅ White Agent Setup Complete!

## White Agent Registered Successfully

✅ **White Agent Created**
- **Card**: `agents/white_agent_card.toml`
- **Agent URL**: `http://localhost:8061/`
- **Launcher URL**: `http://localhost:8060/`
- **Status**: Running and registered
- **Agent ID**: `cd80ab48-de33-421f-903c-515a4f288bed`

## Green Agent (Updated)

✅ **Green Agent Re-registered with Participant Requirements**
- **Agent URL**: `http://localhost:8336/`
- **Launcher URL**: `http://localhost:8335/`
- **Agent ID**: `23bd16c6-ef4b-42a4-9677-fefa7135d849`
- **Participant Requirements**: `[{"role": "other", "name": "opponent_agent", "required": false}]`

## How to Start Battles

### Option 1: Via AgentBeats UI (Easiest)

1. **Open**: http://localhost:5174
2. **Navigate to "Battles"**
3. **Click "Create Battle"**
4. **Select**:
   - **Green Agent**: `[ALFWorld] Green Agent (Updated)` (or any green agent with participant requirements)
   - **Opponents**: `[ALFWorld] White Agent`
5. **Start the battle**

### Option 2: Use the Script

```bash
cd /Users/madanat/Documents/alfworld-greenagent
./start_battle.sh
```

### Option 3: Via API Directly

```bash
# Create battle
curl -X POST http://localhost:9000/battles \
  -H "Content-Type: application/json" \
  -d '{
    "green_agent_id": "23bd16c6-ef4b-42a4-9677-fefa7135d849",
    "opponents": [{
      "name": "opponent_agent",
      "agent_id": "cd80ab48-de33-421f-903c-515a4f288bed",
      "role": "other"
    }],
    "config": {}
  }'
```

## Important Notes

1. **Participant Requirements**: The green agent must have `participant_requirements` that include a requirement with `name: "opponent_agent"` for battles to work.

2. **Agent IDs**: If you register new agents, you'll need to update the agent IDs in the script or API calls.

3. **View Battle**: Once created, view at http://localhost:5174/battles/{battle_id}

## What the White Agent Does

The white agent is a simple LLM-based agent that:
- Receives observations from the ALFWorld environment
- Responds with action commands (e.g., "go to kitchen", "pick up apple")
- Tries to complete the task step by step
- Adapts based on environment feedback

## All Services Status

✅ **AgentBeats Backend**: http://localhost:9000  
✅ **AgentBeats Frontend**: http://localhost:5174  
✅ **Green Agent**: http://localhost:8336 (ports 8335/8336)  
✅ **White Agent**: http://localhost:8061 (ports 8060/8061)  
✅ **MCP Server**: http://localhost:9002  

**You're all set to start battles!** 🎮


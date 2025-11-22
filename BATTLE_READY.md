# ✅ Battle Ready!

## White Agent Registered

✅ **White Agent** is running and registered:
- **Agent URL**: `http://localhost:8061/`
- **Launcher URL**: `http://localhost:8060/`
- **Agent ID**: `cd80ab48-de33-421f-903c-515a4f288bed`

## Green Agent Updated

✅ **Green Agent** has been re-registered with participant requirements:
- **Agent URL**: `http://localhost:8336/`
- **Launcher URL**: `http://localhost:8335/`
- **Agent ID**: `23bd16c6-ef4b-42a4-9677-fefa7135d849`
- **Participant Requirements**: `opponent_agent` (role: other)

## How to Start a Battle

### Option 1: Via UI (Recommended)

1. **Open**: http://localhost:5174
2. **Go to "Battles"** section
3. **Click "Create Battle"**
4. **Select**:
   - **Green Agent**: `[ALFWorld] Green Agent (Updated)` or any `[ALFWorld] Green Agent`
   - **Opponents**: `[ALFWorld] White Agent`
5. **Start the battle**

### Option 2: Via Script

```bash
cd /Users/madanat/Documents/alfworld-greenagent
./start_battle.sh
```

### Option 3: Via API

```bash
# Get latest agent IDs
GREEN_ID=$(curl -s http://localhost:9000/agents | python3 -c "
import sys, json
agents = json.load(sys.stdin)
green = [a for a in agents if '[ALFWorld] Green Agent' in a.get('register_info', {}).get('alias', '') and a.get('register_info', {}).get('participant_requirements')]
print(green[-1]['agent_id'] if green else '')
")

WHITE_ID=$(curl -s http://localhost:9000/agents | python3 -c "
import sys, json
agents = json.load(sys.stdin)
white = [a for a in agents if '[ALFWorld] White Agent' in a.get('register_info', {}).get('alias', '')]
print(white[-1]['agent_id'] if white else '')
")

# Create battle
curl -X POST http://localhost:9000/battles \
  -H "Content-Type: application/json" \
  -d "{
    \"green_agent_id\": \"$GREEN_ID\",
    \"opponents\": [
      {
        \"name\": \"opponent_agent\",
        \"agent_id\": \"$WHITE_ID\",
        \"role\": \"other\"
      }
    ],
    \"config\": {}
  }"
```

## Important Note

The green agent must have `participant_requirements` that include a requirement with `name: "opponent_agent"` for battles to work. The newly registered green agent has this configured.

## What Happens in a Battle

1. **Green Agent** receives battle start signal
2. **Green Agent** sets up Docker environment with ALFWorld API
3. **Green Agent** selects a task (from `tasks/test_task.json` or other tasks)
4. **Green Agent** communicates with **White Agent** to explain the task
5. **White Agent** plays the episode by responding to observations with actions
6. **Green Agent** monitors and scores the result
7. **Green Agent** reports final outcome

## View Battle

Once created, view the battle at:
- **UI**: http://localhost:5174/battles/{battle_id}
- **API**: http://localhost:9000/battles/{battle_id}

## All Services Status

✅ **AgentBeats Backend**: http://localhost:9000  
✅ **AgentBeats Frontend**: http://localhost:5174  
✅ **Green Agent**: http://localhost:8336  
✅ **White Agent**: http://localhost:8061  
✅ **MCP Server**: http://localhost:9002  
✅ **Ready to battle!**


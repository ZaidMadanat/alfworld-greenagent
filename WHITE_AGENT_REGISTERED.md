# ✅ White Agent Registered!

## White Agent Details

### URLs
- **Agent URL**: `http://localhost:8061/`
- **Launcher URL**: `http://localhost:8060/`
- **Status**: ✅ Running and registered

### Registration
The white agent has been registered with AgentBeats backend. It's ready to participate in battles.

## How to Start a Battle

### Option 1: Via AgentBeats UI

1. **Open**: http://localhost:5174
2. **Navigate to "Battles"** section
3. **Click "Create Battle"** or "New Battle"
4. **Select**:
   - **Green Agent**: `[ALFWorld] Green Agent` (your green agent)
   - **Opponents**: `[ALFWorld] White Agent` (the white agent we just registered)
5. **Start the battle**

### Option 2: Via API

```bash
# First, get your green agent ID
GREEN_AGENT_ID=$(curl -s http://localhost:9000/agents | python3 -c "import sys, json; agents=json.load(sys.stdin); green=[a for a in agents if a.get('register_info',{}).get('is_green')]; print(green[0]['agent_id'] if green else '')")

# Get white agent ID
WHITE_AGENT_ID=$(curl -s http://localhost:9000/agents | python3 -c "import sys, json; agents=json.load(sys.stdin); white=[a for a in agents if not a.get('register_info',{}).get('is_green') and 'White' in a.get('register_info',{}).get('alias','')]; print(white[0]['agent_id'] if white else '')")

# Create battle
curl -X POST http://localhost:9000/battles \
  -H "Content-Type: application/json" \
  -d "{
    \"green_agent_id\": \"$GREEN_AGENT_ID\",
    \"opponents\": [
      {
        \"name\": \"opponent_agent\",
        \"agent_id\": \"$WHITE_AGENT_ID\",
        \"role\": \"other\"
      }
    ],
    \"config\": {}
  }"
```

## What Happens in a Battle

1. **Green Agent** sets up the ALFWorld environment (Docker container)
2. **Green Agent** selects a task (from `tasks/` directory)
3. **Green Agent** communicates with **White Agent** to explain the task
4. **White Agent** plays the ALFWorld episode by:
   - Receiving observations from the environment
   - Responding with actions
   - Trying to complete the task
5. **Green Agent** monitors progress and scores the result
6. **Green Agent** reports the final outcome

## Current Setup

✅ **Green Agent**: Running on ports 8335/8336  
✅ **White Agent**: Running on ports 8060/8061  
✅ **Both agents registered** with AgentBeats  
✅ **Tasks available**: `tasks/test_task.json`  
✅ **Ready to start battles!**

## Next Steps

1. Go to http://localhost:5174
2. Create a battle with your green agent and the white agent
3. Watch the battle execute!

The white agent is a simple LLM-based agent that will try to complete ALFWorld tasks by responding to observations with actions.


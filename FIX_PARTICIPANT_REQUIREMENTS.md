# ✅ Fixed: Participant Requirements Issue

## Problem

When registering a green agent via the UI, if the agent card analysis failed or participant_requirements weren't set, the UI would show:
- "No participant requirements defined"
- "This green agent has no required roles"

This prevented battles from being created.

## Solution

Updated the agent registration endpoint (`/agents/analyze_card` and `/agents` POST) to:

1. **Automatically add default participant_requirements** for green agents if they're missing
2. **Default requirement**: `opponent_agent` (role: other, required: false)

This means:
- ✅ Green agents registered via UI will automatically get participant_requirements
- ✅ You can now create battles even if the agent card analysis failed
- ✅ The UI will show participant requirements instead of "No participant requirements defined"

## What Changed

**File**: `agentbeats/src/backend/routes/agents.py`

Changed the registration logic to automatically add default participant_requirements for green agents instead of requiring them to be provided.

## Next Steps

1. **Restart AgentBeats** (already done - backend is restarting)
2. **Wait ~30 seconds** for backend to fully start
3. **Re-register your green agent** via the UI:
   - Go to http://localhost:5174
   - Register agent with:
     - Agent URL: `http://localhost:8336/`
     - Launcher URL: `http://localhost:8335/`
     - Check "Is Green Agent"
   - It will now automatically get participant_requirements!

4. **Create battle** - the UI should now show participant requirements

## Alternative: Use Existing Agent

You can also use the green agent that already has requirements:
- **Agent ID**: `23bd16c6-ef4b-42a4-9677-fefa7135d849`
- **Alias**: `[ALFWorld] Green Agent (Updated)`
- **Has Requirements**: ✅ Yes

This agent is ready to use for battles right now!

## Verification

After restarting, check that the backend is ready:
```bash
curl http://localhost:9000/health
```

Then register a new green agent and it should automatically have participant_requirements set.


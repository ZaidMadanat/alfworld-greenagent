# Battle Reset Issue - Fix Summary

## Problem
Battles were failing with "Green agent reset failed" error. The issue was that:
1. The launcher's notification to the backend about agent readiness was failing silently
2. The timeout for agent readiness was too short (60 seconds)
3. The notification retry logic was insufficient

## Fixes Applied

### 1. Improved Launcher Notification (`agentbeats/src/agentbeats/agent_launcher.py`)
- **Increased timeout**: From 60 seconds (30 attempts × 2s) to 120 seconds (60 attempts × 2s) to match backend timeout
- **Added retry logic**: Now retries notification up to 3 times with 1-second delays
- **Better error handling**: Logs specific error messages and HTTP status codes
- **Improved logging**: More detailed messages about notification attempts

### 2. Created CLI Battle Tool (`run_battle_cli.py`)
- Bypasses UI limitations by directly calling backend APIs
- Automatically finds green and opponent agents
- Monitors battle progress with real-time status updates
- Shows detailed error messages and battle logs

## Usage

### Run Battle via CLI (Recommended)
```bash
python3 run_battle_cli.py
```

This will:
1. List all registered agents
2. Find the green agent automatically
3. Find all opponent agents
4. Create a battle
5. Monitor progress until completion

### Run Battle via UI
1. Go to http://localhost:5174
2. Register agents if needed
3. Create battle
4. The improved reset logic should now work better

## Technical Details

### Backend Ready Timeout
- Backend waits up to **120 seconds** for agents to be ready after reset
- Launcher now matches this timeout (120 seconds)

### Notification Flow
1. Battle starts → Agents locked
2. Reset called on launcher → Returns immediately with `{"status": "restarting"}`
3. Launcher restarts agent process
4. Launcher waits for agent card to be available (checks every 2 seconds)
5. When agent is ready, launcher notifies backend via `PUT /agents/{agent_id}` with `{"ready": True}`
6. Backend polls agent readiness every 5 seconds
7. When all agents are ready, battle proceeds

### Debugging
If battles still fail:
1. Check launcher logs for notification errors
2. Check backend logs for agent readiness status
3. Verify agent URLs are accessible
4. Check that launcher can reach backend URL

## Next Steps
If issues persist:
1. Check Docker container health (for ALFWorld API)
2. Verify MCP servers are running
3. Check agent card endpoints are accessible
4. Review backend logs for specific error messages


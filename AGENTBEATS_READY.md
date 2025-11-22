# ✅ AgentBeats Running in Dev Mode (No Authentication)

## Status: All Services Running

Based on the [AgentBeats self-hosting guide](https://raw.githubusercontent.com/agentbeats/agentbeats/main/docs/self_host_instruction.md), AgentBeats is now running in **dev mode without authentication**.

### ✅ Services

1. **AgentBeats Backend**: http://localhost:9000 ✅
2. **AgentBeats Frontend**: http://localhost:5174 ✅ (Note: moved to 5174 because 5173 was in use)
3. **AgentBeats MCP**: http://localhost:9001/sse
4. **ALFWorld MCP Server**: http://localhost:9002/sse ✅
5. **Green Agent**: http://localhost:8336 ✅

## Access the UI

**Open**: http://localhost:5174

**No login required!** In dev mode, authentication is bypassed automatically.

## Register Green Agent

1. Open http://localhost:5174
2. Navigate to "Register Agent" or "Agents" section
3. Fill in:
   - **Agent URL**: `http://localhost:8336/`
   - **Launcher URL**: `http://localhost:8335/`
   - **Name**: `[ALFWorld] Green Agent`
   - **Check "Is Green Agent"**
4. Click "Register"

## How Dev Mode Works

According to the AgentBeats documentation:
- By default, `agentbeats deploy --deploy_mode dev` runs without authentication
- The `--supabase_auth` flag would enable authentication (we're NOT using it)
- Dev mode sets `DEV_LOGIN=true` and `VITE_DEV_LOGIN=true` automatically
- This bypasses the login screen completely

## Troubleshooting

If you still see a login screen:
1. Make sure you're accessing http://localhost:5174 (not 5173)
2. Check that AgentBeats is running in dev mode:
   ```bash
   tail -f /tmp/agentbeats.log
   ```
3. Look for `DEV_LOGIN=true` or `VITE_DEV_LOGIN=true` in the logs

## Next Steps

1. ✅ Open http://localhost:5174
2. ✅ Register your green agent (no login needed)
3. ✅ Create and run battles!

All services are ready to use!


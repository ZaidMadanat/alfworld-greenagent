# How to Access Green Agent

## ✅ Services Are Running!

The green agent is running on ports 8335 and 8336. Here's how to access them:

## Correct Endpoints

### 1. Agent Card (Port 8336)
**URL**: http://localhost:8336/.well-known/agent-card.json

This returns the agent card JSON. Test it:
```bash
curl http://localhost:8336/.well-known/agent-card.json
```

### 2. Launcher (Port 8335)
**URL**: http://localhost:8335/reset (POST endpoint)

The launcher expects POST requests, not GET. It won't show anything in a browser.

## Why You See "Nothing"

- **Port 8335 root** (`http://localhost:8335/`): Returns "Method Not Allowed" - this is normal, it's a POST-only API
- **Port 8336 root** (`http://localhost:8336/`): Returns "Method Not Allowed" - use the agent card endpoint instead

## For AgentBeats Registration

When registering in AgentBeats UI (http://localhost:5173):

1. **Agent URL**: `http://localhost:8336/`
2. **Launcher URL**: `http://localhost:8335/`
3. **Check "Is Green Agent"**

AgentBeats will use the correct endpoints automatically.

## View Logs

The agent is running in background. To see logs:

```bash
# View live logs
tail -f /tmp/green_agent_console.log

# View last 20 lines
tail -20 /tmp/green_agent_console.log
```

## Verify It's Working

```bash
# Test agent card (should return JSON)
curl http://localhost:8336/.well-known/agent-card.json

# Check processes
ps aux | grep "agentbeats.*green_agent" | grep -v grep

# Check ports
lsof -i :8335 -i :8336
```

## Summary

✅ **Green agent is running and responding**
✅ **Port 8335**: Launcher (POST API)
✅ **Port 8336**: Agent (agent card at `/.well-known/agent-card.json`)

The "nothing" you see in browser is normal - these are API endpoints, not web pages. Use the agent card URL or register in AgentBeats UI!


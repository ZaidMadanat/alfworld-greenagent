# ALFWorld Green Agent - Run Status

## Services Status

### ✅ Prerequisites Check - COMPLETED
- Docker: Installed but daemon not running (needs to be started for full functionality)
- AgentBeats: Found in project directory (`agentbeats/`)
- Agent card: `agents/green_agent/agent_card_clean.toml` exists
- Tools file: `agents/tools.py` exists
- Dockerfile: Exists
- API file: `alfworld_api.py` exists
- MCP server: `mcp_server.py` exists
- OPENAI_API_KEY: **NOT SET** (needs to be set for green agent to work)

### 🟡 AgentBeats Services - STARTED
- Backend (port 9000): Starting (may take time to fully initialize)
- Frontend (port 5173): Starting
- AgentBeats MCP (port 9001): Starting

### 🟡 ALFWorld MCP Server - STARTED
- Port 9002: Started in background
- Endpoint: `http://localhost:9002/sse`

### 🟡 Green Agent - STARTED
- Launcher port: 8335
- Agent port: 8336
- Status: Started in background (may need OPENAI_API_KEY to function)

## Next Steps

### 1. Set Environment Variables
```bash
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="$OPENAI_API_KEY"
```

### 2. Start Docker (if not running)
```bash
# On macOS, start Docker Desktop
# Or check: docker ps
```

### 3. Verify Services Are Running
```bash
# Check AgentBeats backend
curl http://localhost:9000/health

# Check frontend
curl http://localhost:5173

# Check MCP server
curl http://localhost:9002/sse

# Check green agent
curl http://localhost:8336/.well-known/agent-card.json
```

### 4. Register Green Agent
1. Open `http://localhost:5173` in browser
2. Navigate to "Register Agent"
3. Enter:
   - Agent URL: `http://localhost:8336/`
   - Launcher URL: `http://localhost:8335/`
   - Check "Is Green Agent"
4. Register the agent

### 5. Create and Run Battle
1. In AgentBeats UI, create a new battle
2. Select the green agent
3. Monitor battle execution
4. Verify Docker container is created
5. Check battle results

## Troubleshooting

### If services don't start:
- Check logs in terminal where services were started
- Verify ports are not in use: `lsof -i :9000 -i :9001 -i :9002 -i :8335 -i :8336`
- Ensure Python dependencies are installed

### If Docker fails:
- Start Docker Desktop (macOS) or Docker daemon
- Verify: `docker ps`

### If green agent fails:
- Set OPENAI_API_KEY environment variable
- Check agent logs for errors
- Verify MCP servers are accessible

## Verification Commands

```bash
# Check all services
curl http://localhost:9000/health  # Backend
curl http://localhost:5173          # Frontend  
curl http://localhost:9002/sse     # ALFWorld MCP
curl http://localhost:8336/.well-known/agent-card.json  # Green agent

# Check processes
ps aux | grep agentbeats
ps aux | grep mcp_server

# Check ports
lsof -i :9000 -i :9001 -i :9002 -i :8335 -i :8336 -i :5173
```

## Notes

- All services have been started in background
- Services may take 10-30 seconds to fully initialize
- Docker must be running for battle execution to work
- OPENAI_API_KEY must be set for the green agent to function
- Frontend UI available at: http://localhost:5173


# Quick Run Guide - ALFWorld Green Agent with AgentBeats

## ✅ Services Started

All required services have been started in the background:

1. **AgentBeats Backend** - Port 9000
2. **AgentBeats Frontend** - Port 5173  
3. **AgentBeats MCP Server** - Port 9001
4. **ALFWorld MCP Server** - Port 9002
5. **Green Agent** - Ports 8335 (launcher), 8336 (agent)

## ⚠️ Required Actions

### 1. Set OPENAI_API_KEY
```bash
export OPENAI_API_KEY="sk-your-key-here"
export OPENROUTER_API_KEY="$OPENAI_API_KEY"
```

Then restart the green agent if needed:
```bash
# The agent was started but may need the API key
# Check if it's running:
curl http://localhost:8336/.well-known/agent-card.json
```

### 2. Start Docker (if not running)
```bash
# On macOS: Start Docker Desktop application
# Verify Docker is running:
docker ps
```

### 3. Register Green Agent

1. **Open AgentBeats UI**: http://localhost:5173
2. **Navigate to "Register Agent"** (usually in sidebar or agents section)
3. **Fill in the form**:
   - **Agent URL**: `http://localhost:8336/`
   - **Launcher URL**: `http://localhost:8335/`
   - **Name**: `[ALFWorld] Green Agent` (or any name)
   - **Check "Is Green Agent"** checkbox
4. **Click "Register"**

### 4. Create a Battle

1. **Navigate to "Battles"** in the UI
2. **Click "Create Battle"** or "New Battle"
3. **Select the green agent** you just registered
4. **Configure battle settings** (if any)
5. **Start the battle**

### 5. Monitor Battle Execution

The battle will:
- Create a Docker container for ALFWorld API server
- Set up the ALFWorld environment
- Run an episode with the opponent agent
- Report results

Watch the battle progress in the UI.

## 🔍 Verification Commands

Check if services are running:

```bash
# Backend health
curl http://localhost:9000/health

# Frontend
curl http://localhost:5173

# ALFWorld MCP
curl http://localhost:9002/sse

# Green Agent
curl http://localhost:8336/.well-known/agent-card.json

# Check processes
ps aux | grep -E "(agentbeats|mcp_server)" | grep -v grep
```

## 🐛 Troubleshooting

### Services Not Responding
- Wait 10-30 seconds for services to fully start
- Check terminal/console where services were started for errors
- Verify ports are not in use: `lsof -i :9000 -i :9001 -i :9002 -i :8335 -i :8336`

### Green Agent Not Working
- Ensure OPENAI_API_KEY is set
- Check agent logs (where you started it)
- Verify MCP servers are accessible

### Docker Issues
- Start Docker Desktop (macOS) or Docker daemon
- Verify: `docker ps` works
- Check Docker socket: `ls -la ~/.docker/run/docker.sock`

### Battle Fails
- Check Docker container logs: `docker logs alfworld_<battle_id>`
- Verify ALFWorld API is accessible in container
- Check battle logs in AgentBeats UI

## 📝 Next Steps After Battle

Once a battle completes:
1. Review battle results in the UI
2. Check Docker container was cleaned up (or clean up manually)
3. Review battle logs and metrics
4. Test with different tasks or configurations

## 🎯 Success Indicators

You'll know everything is working when:
- ✅ All services respond to health checks
- ✅ Green agent is registered in UI
- ✅ Battle can be created
- ✅ Docker container starts for battle
- ✅ Episode runs and executes actions
- ✅ Battle completes with results

## 📚 Additional Resources

- See `RUN_STATUS.md` for detailed status
- See `QUICK_START.md` for original setup instructions
- See `SETUP_COMPLETE.md` for configuration details


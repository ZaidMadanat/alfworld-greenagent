#!/bin/bash
# Script to start the ALFWorld Green Agent

echo "🚀 Starting ALFWorld Green Agent..."
echo ""

# Check if we're in the right directory
if [ ! -f "agents/green_agent/agent_card_clean.toml" ]; then
    echo "❌ Error: Please run this from the alfworld-greenagent directory"
    exit 1
fi

# Activate AgentBeats venv
if [ ! -d "$HOME/agentbeats/.venv" ]; then
    echo "❌ Error: AgentBeats venv not found at $HOME/agentbeats/.venv"
    exit 1
fi

source "$HOME/agentbeats/.venv/bin/activate"

# Check for API keys
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set in environment"
    read -p "Enter your OPENAI_API_KEY: " OPENAI_API_KEY
    export OPENAI_API_KEY
fi

export OPENROUTER_API_KEY="${OPENAI_API_KEY}"

echo "✅ Environment ready"
echo "📍 Agent will run on:"
echo "   - Launcher: http://localhost:8335"
echo "   - Agent: http://localhost:8336"
echo ""
echo "Starting agent..."
echo ""

# Start the green agent
agentbeats run agents/green_agent/agent_card_clean.toml \
  --launcher_port 8335 \
  --agent_port 8336 \
  --model_type openai \
  --model_name gpt-4o-mini \
  --tool agents/tools.py \
  --mcp http://localhost:9001/sse \
  --mcp http://localhost:9002/sse


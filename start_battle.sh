#!/bin/bash
# Quick script to start a battle between Green Agent and White Agent

BACKEND_URL="http://localhost:9000"

echo "🔍 Finding registered agents..."

# Get the most recent green agent
GREEN_AGENT_ID=$(curl -s "$BACKEND_URL/agents" | python3 -c "
import sys, json
agents = json.load(sys.stdin)
green_agents = [a for a in agents if '[ALFWorld] Green Agent' in a.get('register_info', {}).get('alias', '')]
if green_agents:
    print(green_agents[-1]['agent_id'])
else:
    print('')
")

# Get the most recent white agent
WHITE_AGENT_ID=$(curl -s "$BACKEND_URL/agents" | python3 -c "
import sys, json
agents = json.load(sys.stdin)
white_agents = [a for a in agents if '[ALFWorld] White Agent' in a.get('register_info', {}).get('alias', '')]
if white_agents:
    print(white_agents[-1]['agent_id'])
else:
    print('')
")

if [ -z "$GREEN_AGENT_ID" ]; then
    echo "❌ Green Agent not found. Please register it first."
    exit 1
fi

if [ -z "$WHITE_AGENT_ID" ]; then
    echo "❌ White Agent not found. Please register it first."
    exit 1
fi

echo "✅ Green Agent ID: $GREEN_AGENT_ID"
echo "✅ White Agent ID: $WHITE_AGENT_ID"
echo ""
echo "🚀 Creating battle..."

BATTLE_RESPONSE=$(curl -s -X POST "$BACKEND_URL/battles" \
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
  }")

BATTLE_ID=$(echo "$BATTLE_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('battle_id', ''))" 2>/dev/null)

if [ -z "$BATTLE_ID" ]; then
    echo "❌ Failed to create battle"
    echo "Response: $BATTLE_RESPONSE"
    exit 1
fi

echo "✅ Battle created!"
echo "🎯 Battle ID: $BATTLE_ID"
echo "🌐 View battle at: http://localhost:5174/battles/$BATTLE_ID"
echo ""
echo "The battle will start automatically. Watch it in the AgentBeats UI!"


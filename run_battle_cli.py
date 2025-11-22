#!/usr/bin/env python3
"""
CLI tool to run AgentBeats battles without using the UI.
This bypasses UI limitations and directly creates and manages battles.
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional

BACKEND_URL = "http://localhost:9000"
API_BASE = f"{BACKEND_URL}/api"
# Note: Some endpoints are at /api, others at root level

def get_agents() -> list:
    """Get all registered agents."""
    # Try both /api/agents and /agents endpoints
    for endpoint in [f"{API_BASE}/agents", f"{BACKEND_URL}/agents"]:
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            continue
    print(f"❌ Error fetching agents: tried both /api/agents and /agents")
    return []

def find_agent_by_name(agents: list, name_pattern: str) -> Optional[Dict]:
    """Find an agent by name pattern."""
    for agent in agents:
        if name_pattern.lower() in agent.get("name", "").lower():
            return agent
    return None

def create_battle(green_agent_id: str, opponent_ids: list, task_config: str = "", green_agent_data: Optional[Dict] = None) -> Optional[Dict]:
    """Create a battle."""
    # Get green agent's participant requirements to determine the correct 'name' for opponents
    participant_requirements = []
    if green_agent_data:
        participant_requirements = green_agent_data.get('register_info', {}).get('participant_requirements', [])
    
    # Default to 'opponent_agent' if no requirements found
    default_name = "opponent_agent"
    if participant_requirements:
        # Use the first requirement's name
        default_name = participant_requirements[0].get('name', 'opponent_agent')
    
    # Convert opponent_ids to opponents format (list of dicts with name and agent_id)
    opponents = []
    for opp_id in opponent_ids:
        opponents.append({
            "name": default_name,  # Must match participant_requirements name
            "agent_id": opp_id
        })
    
    payload = {
        "green_agent_id": green_agent_id,
        "opponents": opponents,
        "task_config": task_config
    }
    
    # Try both /api/battles and /battles endpoints
    last_error = None
    for endpoint in [f"{API_BASE}/battles", f"{BACKEND_URL}/battles"]:
        try:
            print(f"📝 Creating battle with green agent {green_agent_id} and opponents {opponent_ids}...")
            response = requests.post(endpoint, json=payload)
            response.raise_for_status()
            battle = response.json()
            battle_id = battle.get('battle_id') or battle.get('id') or battle.get('battle', {}).get('id')
            if battle_id:
                print(f"✅ Battle created: {battle_id}")
            else:
                print(f"✅ Battle created: {json.dumps(battle, indent=2)}")
            return battle
        except Exception as e:
            last_error = e
            continue
    
    # If all attempts failed, print error
    if last_error:
        print(f"❌ Error creating battle: {last_error}")
        if hasattr(last_error, 'response') and last_error.response is not None:
            try:
                error_detail = last_error.response.json()
                print(f"   Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"   Error text: {last_error.response.text}")
    return None

def get_battle(battle_id: str) -> Optional[Dict]:
    """Get battle status."""
    # Try both /api/battles and /battles endpoints
    for endpoint in [f"{API_BASE}/battles/{battle_id}", f"{BACKEND_URL}/battles/{battle_id}"]:
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if endpoint == f"{BACKEND_URL}/battles/{battle_id}":  # Last attempt
                print(f"❌ Error fetching battle: {e}")
            continue
    return None

def wait_for_battle_completion(battle_id: str, timeout: int = 600) -> Dict:
    """Wait for battle to complete and print status updates."""
    start_time = time.time()
    last_state = None
    last_log_time = 0
    
    print(f"\n⏳ Monitoring battle {battle_id} (timeout: {timeout}s)...")
    
    while time.time() - start_time < timeout:
        battle = get_battle(battle_id)
        if not battle:
            print("❌ Could not fetch battle status")
            break
            
        state = battle.get("state")
        error = battle.get("error")
        
        # Print state changes
        if state != last_state:
            print(f"\n📊 Battle state: {state}")
            last_state = state
            
        # Print error if any
        if error and time.time() - last_log_time > 5:
            print(f"⚠️  Error: {error}")
            last_log_time = time.time()
            
        # Check for completion
        if state in ["completed", "error", "cancelled"]:
            print(f"\n🏁 Battle finished with state: {state}")
            if error:
                print(f"   Error: {error}")
            return battle
            
        # Print recent logs
        logs = battle.get("logs", [])
        if logs:
            recent_logs = [log for log in logs if log.get("timestamp", 0) > last_log_time]
            for log in recent_logs[-5:]:  # Show last 5 new logs
                message = log.get("message", "")
                if message:
                    print(f"   [{log.get('type', 'info')}] {message}")
                    last_log_time = max(last_log_time, log.get("timestamp", 0))
        
        time.sleep(2)
    
    print(f"\n⏱️  Timeout reached after {timeout} seconds")
    return get_battle(battle_id)

def main():
    """Main CLI entry point."""
    print("🚀 AgentBeats Battle CLI\n")
    
    # Get all agents
    print("📋 Fetching registered agents...")
    agents = get_agents()
    if not agents:
        print("❌ No agents found. Please register agents first.")
        return 1
    
    print(f"✅ Found {len(agents)} registered agents:")
    for agent in agents:
        agent_id = agent.get('agent_id') or agent.get('id')
        name = agent.get('register_info', {}).get('alias') or agent.get('name', 'Unnamed')
        is_green = agent.get('register_info', {}).get('is_green', False) or agent.get('is_green', False)
        ready = agent.get('ready', False)
        url = agent.get('register_info', {}).get('agent_url', 'N/A')
        print(f"   - {name} ({agent_id})")
        print(f"     Green: {is_green}")
        print(f"     Ready: {ready}")
        print(f"     URL: {url}")
        print()
    
    # Find green agent - prefer ALFWorld green agent with participant requirements
    green_agent = None
    best_match = None
    for agent in agents:
        is_green = agent.get('register_info', {}).get('is_green', False) or agent.get('is_green', False)
        if is_green:
            agent_name = agent.get('register_info', {}).get('alias') or agent.get('name', '')
            participant_reqs = agent.get('register_info', {}).get('participant_requirements', [])
            # Prefer ALFWorld green agent with participant requirements
            if 'ALFWorld' in agent_name and participant_reqs:
                green_agent = agent
                break
            elif 'ALFWorld' in agent_name and not best_match:
                best_match = agent
            elif not green_agent and not best_match:  # Fallback to first green agent
                green_agent = agent
    
    # Use best match if we didn't find one with requirements
    if not green_agent and best_match:
        green_agent = best_match
    
    if not green_agent:
        print("❌ No green agent found. Please register a green agent first.")
        return 1
    
    green_agent_id = green_agent.get('agent_id') or green_agent.get('id')
    green_name = green_agent.get('register_info', {}).get('alias') or green_agent.get('name', 'Unnamed')
    print(f"✅ Found green agent: {green_name} ({green_agent_id})")
    
    # Show participant requirements
    participant_reqs = green_agent.get('register_info', {}).get('participant_requirements', [])
    if participant_reqs:
        print(f"   Participant requirements: {[r.get('name') for r in participant_reqs]}")
    
    # Find opponent agents
    opponent_agents = []
    for agent in agents:
        is_green = agent.get('register_info', {}).get('is_green', False) or agent.get('is_green', False)
        if not is_green:
            opponent_agents.append(agent)
    
    if not opponent_agents:
        print("❌ No opponent agents found. Please register at least one opponent agent.")
        return 1
    
    print(f"✅ Found {len(opponent_agents)} opponent agent(s):")
    for opp in opponent_agents:
        opp_id = opp.get('agent_id') or opp.get('id')
        opp_name = opp.get('register_info', {}).get('alias') or opp.get('name', 'Unnamed')
        print(f"   - {opp_name} ({opp_id})")
    
    # Select opponents - use only the ALFWorld white agents for now
    opponent_ids = []
    seen_ids = set()
    for opp in opponent_agents:
        opp_id = opp.get('agent_id') or opp.get('id')
        opp_name = opp.get('register_info', {}).get('alias') or opp.get('name', '')
        # Only use ALFWorld white agents, and avoid duplicates
        if opp_id and opp_id not in seen_ids:
            if 'ALFWorld' in opp_name or 'white' in opp_name.lower():
                opponent_ids.append(opp_id)
                seen_ids.add(opp_id)
    
    if not opponent_ids:
        print("⚠️  No ALFWorld white agents found, using first opponent agent")
        if opponent_agents:
            first_id = opponent_agents[0].get('agent_id') or opponent_agents[0].get('id')
            if first_id:
                opponent_ids = [first_id]
    
    # Create battle
    battle = create_battle(
        green_agent_id=green_agent_id,
        opponent_ids=opponent_ids,
        task_config="ALFWorld cleanliness task",
        green_agent_data=green_agent
    )
    
    if not battle:
        return 1
    
    battle_id = battle.get('battle_id') or battle.get('id') or battle.get('battle', {}).get('id')
    if not battle_id:
        print("❌ Battle created but no battle ID returned")
        print(f"   Response: {json.dumps(battle, indent=2)}")
        return 1
    
    # Monitor battle
    final_battle = wait_for_battle_completion(battle_id, timeout=600)
    
    # Print final summary
    if final_battle:
        print("\n" + "="*60)
        print("📊 FINAL BATTLE SUMMARY")
        print("="*60)
        print(f"Battle ID: {battle_id}")
        print(f"State: {final_battle.get('state')}")
        print(f"Error: {final_battle.get('error', 'None')}")
        
        logs = final_battle.get("logs", [])
        if logs:
            print(f"\nRecent logs ({len(logs)} total):")
            for log in logs[-10:]:
                print(f"  [{log.get('type', 'info')}] {log.get('message', '')}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


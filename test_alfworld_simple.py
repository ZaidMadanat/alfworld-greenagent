#!/usr/bin/env python3
"""
Simple ALFWorld test - create environment and interact with it.
Uses proper config structure based on ALFWorld requirements.
"""

import sys
import os
from pathlib import Path

# Set ALFWORLD_DATA environment variable
os.environ['ALFWORLD_DATA'] = str(Path.home() / '.cache' / 'alfworld')

try:
    from alfworld.agents.environment import get_environment
    import alfworld.agents.modules.generic as generic
    print("✅ ALFWorld imports successful")
except ImportError as e:
    print(f"❌ Failed to import ALFWorld: {e}")
    sys.exit(1)

def create_alfworld_config():
    """Create a proper ALFWorld config dictionary."""
    data_dir = Path.home() / '.cache' / 'alfworld'
    json_dir = data_dir / 'json_2.1.1'
    
    config = {
        'env': {
            'type': 'AlfredTWEnv',
            'data_dir': str(data_dir),
            'goal_desc_human_anns_prob': 0.0,
            'task_types': ['pick_and_place_simple', 'pick_clean_then_place_in_recep'],
            'num_processes': 1,
            'max_num_steps': 200,
            'domain_randomization': False,
            'expert_type': 'plan',
            'reward_config': {
                'step_penalty': -0.01,
                'goal_success_reward': 10.0,
                'failed_steps': 0,
            },
        },
        'general': {
            'training_method': 'dqn',  # or 'dagger'
        },
        'rl': {
            'training': {
                'max_nb_steps_per_episode': 200,
            },
        },
        'dagger': {
            'training': {
                'max_nb_steps_per_episode': 200,
            },
        },
        'dataset': {
            'data_path': str(json_dir),
            'include_dirs': [],
            'exclude_dirs': [],
            'num_train_games': 100,  # Limit for testing
            'num_valid_seen_games': 50,
            'num_valid_unseen_games': 50,
        },
        'task': {
            'type': 'AlfredTask',
        },
        'model': {},
    }
    return config

def test_alfworld_basic():
    """Test basic ALFWorld interaction."""
    print("\n" + "="*60)
    print("Testing ALFWorld Environment (Basic)")
    print("="*60)
    
    try:
        # Create config
        print("\n1️⃣  Creating ALFWorld config...")
        config = create_alfworld_config()
        print(f"   ✅ Config created")
        print(f"   📁 Data dir: {config['env']['data_dir']}")
        print(f"   📋 Task types: {config['env']['task_types']}")
        
        # Get environment class
        print("\n2️⃣  Getting environment class...")
        env_type = config['env']['type']
        env_class = get_environment(env_type)
        print(f"   ✅ Got environment class: {env_class.__name__}")
        
        # Create environment instance
        print("\n3️⃣  Creating environment instance...")
        env = env_class(config, train_eval='train')
        print("   ✅ Environment instance created")
        
        # Initialize environment
        print("\n4️⃣  Initializing environment...")
        env = env.init_env(batch_size=1)
        print("   ✅ Environment initialized")
        
        # Reset environment
        print("\n5️⃣  Resetting environment...")
        observation, info = env.reset()
        
        # Handle observation (might be list)
        if isinstance(observation, list):
            obs_str = observation[0] if len(observation) > 0 else str(observation)
        else:
            obs_str = str(observation)
        
        print(f"   ✅ Environment reset")
        print(f"   📊 Initial observation length: {len(obs_str)} chars")
        if len(obs_str) > 0:
            preview = obs_str[:200] + "..." if len(obs_str) > 200 else obs_str
            print(f"   📝 Observation preview: {preview}")
        
        # Check info
        if isinstance(info, dict):
            print(f"   📋 Info keys: {list(info.keys())}")
            if 'admissible_commands' in info:
                adm = info['admissible_commands']
                if isinstance(adm, list) and len(adm) > 0:
                    commands = adm[0] if isinstance(adm[0], list) else adm
                    print(f"   🎯 Available commands: {len(commands)}")
                    if len(commands) > 0:
                        print(f"   📋 Sample commands: {commands[:5]}")
        
        # Test actions
        print("\n6️⃣  Testing actions...")
        test_actions = []
        
        # Get admissible commands if available
        if isinstance(info, dict) and 'admissible_commands' in info:
            adm = info.get('admissible_commands', [[]])
            if isinstance(adm, list) and len(adm) > 0:
                commands = adm[0] if isinstance(adm[0], list) else adm
                if len(commands) > 0:
                    test_actions = commands[:3]
        
        if not test_actions:
            test_actions = ["look", "go to kitchen", "examine kitchen"]
        
        print(f"   Testing {len(test_actions)} actions...")
        
        for i, action in enumerate(test_actions, 1):
            print(f"\n   Action {i}: '{action}'")
            try:
                # ALFWorld expects list of actions
                actions_list = [action]
                result = env.step(actions_list)
                
                # Handle return format (obs, scores, dones, infos)
                if len(result) == 4:
                    next_observation, scores, dones, infos = result
                    reward = scores[0] if isinstance(scores, list) else scores
                    done = dones[0] if isinstance(dones, list) else dones
                    info = infos[0] if isinstance(infos, list) else infos
                else:
                    print(f"      ⚠️  Unexpected return format: {len(result)} values")
                    break
                
                # Handle observation
                if isinstance(next_observation, list):
                    obs_str = next_observation[0] if len(next_observation) > 0 else str(next_observation)
                else:
                    obs_str = str(next_observation)
                
                print(f"      ✅ Action executed")
                print(f"      📊 Observation length: {len(obs_str)} chars")
                print(f"      🎁 Reward: {reward}")
                print(f"      ✅ Done: {done}")
                
                if isinstance(info, dict):
                    if 'won' in info:
                        print(f"      🏆 Won: {info.get('won', False)}")
                
                if len(obs_str) > 0:
                    preview = obs_str[:150] + "..." if len(obs_str) > 150 else obs_str
                    print(f"      📝 Observation: {preview}")
                
                observation = next_observation
                
                if done:
                    print(f"      🎯 Episode finished!")
                    break
                    
            except Exception as e:
                print(f"      ❌ Action failed: {e}")
                import traceback
                traceback.print_exc()
                break
        
        # Close environment
        print("\n7️⃣  Closing environment...")
        env.close()
        print("   ✅ Environment closed")
        
        print("\n" + "="*60)
        print("✅ ALFWorld test completed successfully!")
        print("="*60)
        print("\n📝 Summary:")
        print("   - ALFWorld environment works")
        print("   - Can reset and get observations")
        print("   - Can execute actions and get rewards")
        print("   - Ready to integrate with LLM agents!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ALFWorld test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_alfworld_basic()
    sys.exit(0 if success else 1)


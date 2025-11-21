#!/usr/bin/env python3
"""
Simple script to test ALFWorld locally without AgentBeats.
This tests basic ALFWorld interaction: creating environment, running actions, getting observations.
"""

import sys
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "agents"))

try:
    from alfworld.agents.environment import get_environment
    import alfworld.agents.modules.generic as generic
    print("✅ ALFWorld imports successful")
except ImportError as e:
    print(f"❌ Failed to import ALFWorld: {e}")
    sys.exit(1)

# Try to find ALFWorld config
import alfworld
import os
alfworld_path = Path(alfworld.__file__).parent if hasattr(alfworld, '__file__') else None

# Common config paths
config_candidates = [
    Path("alfworld/configs/base_config.yaml"),
    Path(alfworld_path) / "data" / "base_config.yaml" if alfworld_path else None,
    Path(alfworld_path) / "configs" / "base_config.yaml" if alfworld_path else None,
]

config_path = None
for candidate in config_candidates:
    if candidate and candidate.exists():
        config_path = str(candidate)
        break

if not config_path:
    print("⚠️  Warning: Could not find base_config.yaml")
    print("   Tried paths:", [str(c) for c in config_candidates if c])
    print("   Will try to proceed with default config...")
    config_path = None

# Try to find or create a sample task
tasks_dir = PROJECT_ROOT / "tasks"
tasks_dir.mkdir(exist_ok=True)

# Create a simple test task JSON
test_task_path = tasks_dir / "test_task.json"
if not test_task_path.exists():
    # Create a minimal ALFWorld task JSON
    test_task = {
        "task_type": "pick_and_place_simple",
        "pddl_domain": "clean",
        "pddl_problem": "put apple in fridge",
        "task_id": "test_task",
        "initial_conditions": [],
        "goal": {
            "goal": ["In(Apple, Fridge)"]
        }
    }
    import json
    test_task_path.write_text(json.dumps(test_task, indent=2))
    print(f"📝 Created test task at {test_task_path}")

print(f"\n🔧 Using config: {config_path or 'default'}")
print(f"📋 Using task: {test_task_path}")

def test_alfworld_interaction():
    """Test basic ALFWorld environment interaction."""
    print("\n" + "="*60)
    print("Testing ALFWorld Environment")
    print("="*60)
    
    try:
        # Get environment
        print("\n1️⃣  Creating environment...")
        # Try to load config to get env_type
        try:
            config = generic.load_config()
            if isinstance(config, dict) and 'env' in config:
                env_type = config['env'].get('type', 'AlfredTWEnv')
            else:
                env_type = 'AlfredTWEnv'  # Default to text world
            print(f"   Using env_type: {env_type}")
        except:
            env_type = 'AlfredTWEnv'  # Default to text world
            print(f"   Using default env_type: {env_type}")
        
        # Get environment class and create instance
        env_class = get_environment(env_type)
        print(f"   Environment class: {env_class.__name__}")
        
        # Try to instantiate environment - ALFWorld might work without explicit config
        print("   Attempting to create environment instance...")
        try:
            # Try creating without config first (ALFWorld might have defaults)
            try:
                env = env_class(train_eval='train')
                print("   ✅ Environment created (no config needed)")
            except TypeError:
                # If it requires config, try with a minimal config
                try:
                    # Create minimal config dict
                    config = {
                        'env': {'type': env_type},
                        'task': {},
                        'model': {}
                    }
                    env = env_class(config, train_eval='train')
                    print("   ✅ Environment created (with minimal config)")
                except Exception as e:
                    print(f"   ⚠️  Creating with config failed: {e}")
                    # Try with None config
                    env = env_class(None, train_eval='train')
                    print("   ✅ Environment created (None config)")
        except Exception as e:
            print(f"   ❌ Failed to create environment: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Initialize the environment
        try:
            env = env.init_env(batch_size=1)
            print("   ✅ Environment initialized")
        except Exception as e:
            print(f"   ⚠️  init_env failed, trying without it: {e}")
            # Continue anyway - env might be ready
        
        # Reset with task
        print(f"\n2️⃣  Resetting environment with task: {test_task_path}")
        try:
            # Try reset with task_json parameter
            if hasattr(env, 'reset'):
                try:
                    observation, info = env.reset(task_json=str(test_task_path))
                    print(f"   ✅ Environment reset with task")
                except TypeError:
                    # If reset doesn't accept task_json, try regular reset
                    observation, info = env.reset()
                    print(f"   ✅ Environment reset (task will be loaded separately)")
                    # Try to load task separately
                    task_meta = generic.load_json(test_task_path)
                    print(f"   📋 Task loaded: {task_meta.get('task_id', 'N/A')}")
                except Exception as e:
                    # Fallback to regular reset
                    observation, info = env.reset()
                    print(f"   ⚠️  Reset with task failed, using regular reset: {e}")
            else:
                observation, info = env.reset()
                print(f"   ✅ Environment reset")
            
            # Handle observation (might be list or string)
            if isinstance(observation, list):
                obs_str = observation[0] if len(observation) > 0 else str(observation)
            else:
                obs_str = str(observation)
            
            print(f"   📊 Initial observation length: {len(obs_str)} chars")
            if len(obs_str) > 200:
                print(f"   📊 Initial observation preview: {obs_str[:200]}...")
            else:
                print(f"   📊 Initial observation: {obs_str}")
            
            if isinstance(info, dict):
                print(f"   📋 Info keys: {list(info.keys())}")
                if 'admissible_commands' in info:
                    print(f"   🎯 Admissible commands available: {len(info.get('admissible_commands', [[]])[0]) if isinstance(info['admissible_commands'], list) else 'N/A'}")
        except Exception as e:
            print(f"   ❌ Reset failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test a simple action
        print("\n3️⃣  Testing actions...")
        
        # Get admissible commands if available
        if isinstance(info, dict) and 'admissible_commands' in info:
            admissible = info.get('admissible_commands', [[]])
            if isinstance(admissible, list) and len(admissible) > 0:
                commands = admissible[0] if isinstance(admissible[0], list) else admissible
                print(f"   🎯 Available commands: {len(commands)} found")
                if len(commands) > 0:
                    print(f"   📋 Sample commands: {commands[:5]}")
                    test_actions = commands[:3]  # Use first 3 available commands
                else:
                    test_actions = ["look", "go to kitchen", "examine kitchen"]
            else:
                test_actions = ["look", "go to kitchen", "examine kitchen"]
        else:
            test_actions = ["look", "go to kitchen", "examine kitchen"]
        
        print(f"   Testing {len(test_actions)} actions...")
        
        for i, action in enumerate(test_actions, 1):
            print(f"\n   Action {i}: '{action}'")
            try:
                # Step might expect list of actions
                if isinstance(action, str):
                    actions_list = [action]
                else:
                    actions_list = action
                
                result = env.step(actions_list)
                
                # Handle different return formats
                if len(result) == 4:
                    next_observation, scores, dones, infos = result
                    reward = scores[0] if isinstance(scores, list) else scores
                    done = dones[0] if isinstance(dones, list) else dones
                    info = infos[0] if isinstance(infos, list) else infos
                    truncated = False
                elif len(result) == 5:
                    next_observation, reward, done, truncated, info = result
                else:
                    print(f"      ⚠️  Unexpected return format: {len(result)} values")
                    break
                
                # Handle observation (might be list or string)
                if isinstance(next_observation, list):
                    obs_str = next_observation[0] if len(next_observation) > 0 else str(next_observation)
                else:
                    obs_str = str(next_observation)
                
                print(f"      ✅ Action executed")
                print(f"      📊 Observation length: {len(obs_str)} chars")
                print(f"      🎁 Reward: {reward}")
                print(f"      ✅ Done: {done}, Truncated: {truncated if 'truncated' in locals() else False}")
                if isinstance(info, dict):
                    if 'won' in info:
                        print(f"      🏆 Won: {info.get('won', False)}")
                    if 'admissible_commands' in info:
                        adm = info['admissible_commands']
                        if isinstance(adm, list) and len(adm) > 0:
                            print(f"      🎯 Next available commands: {len(adm[0] if isinstance(adm[0], list) else adm)}")
                
                if len(obs_str) > 0:
                    preview = obs_str[:150] + "..." if len(obs_str) > 150 else obs_str
                    print(f"      📝 Observation preview: {preview}")
                
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
        print("\n4️⃣  Closing environment...")
        env.close()
        print("   ✅ Environment closed")
        
        print("\n" + "="*60)
        print("✅ ALFWorld test completed successfully!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ALFWorld test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_alfworld_interaction()
    sys.exit(0 if success else 1)


# Green Agent Registration Information

## Agent URLs

### Agent URL
```
http://localhost:8336/
```

### Launcher URL
```
http://localhost:8335/
```

## Registration Details

When registering in AgentBeats UI or via API:

- **Agent URL**: `http://localhost:8336/`
- **Launcher URL**: `http://localhost:8335/`
- **Name**: `[ALFWorld] Green Agent`
- **Is Green Agent**: ✅ Yes (check this box)
- **Participant Requirements**: Can be empty `[]` or add as needed

## Tasks

### Task Locations

The green agent looks for ALFWorld task JSON files in these locations (in order):

1. **Primary**: `alfworld/data/seed_data/` (ALFWorld's default location)
2. **Fallback**: `./tasks/` (local project directory)

### Current Tasks

You currently have:
- `tasks/test_task.json` - A simple test task (pick and place apple in fridge)

### Task Format

Tasks should be JSON files with this structure:
```json
{
  "task_type": "pick_and_place_simple",
  "pddl_domain": "clean",
  "pddl_problem": "put apple in fridge",
  "task_id": "test_task",
  "initial_conditions": [],
  "goal": {
    "goal": ["In(Apple, Fridge)"]
  }
}
```

### Task ID Reference

From your agent card, the default task ID mentioned is:
- **Primary task id**: `cleanliness-v0`

The `generate_alfworld_task` tool will look for:
- `{ALFWORLD_TASK_DIR}/cleanliness-v0.json`
- Or `tasks/cleanliness-v0.json`

### Getting More Tasks

To get more ALFWorld tasks:

1. **Download ALFWorld data** (if not already done):
   ```bash
   cd alfworld
   alfworld-download
   ```
   This will download tasks to `alfworld/data/json_2.1.1/train/`

2. **Or create custom tasks** in the `tasks/` directory with the JSON format above

3. **Task files are mounted** into Docker containers when battles run, so they're accessible to the ALFWorld API server

## Quick Registration Command

If registering via API:

```bash
curl -X POST http://localhost:9000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "[ALFWorld] Green Agent",
    "agent_url": "http://localhost:8336/",
    "launcher_url": "http://localhost:8335/",
    "is_green": true,
    "participant_requirements": []
  }'
```

## Summary

✅ **Agent URL**: `http://localhost:8336/`  
✅ **Launcher URL**: `http://localhost:8335/`  
✅ **Tasks**: Located in `tasks/` directory or `alfworld/data/seed_data/`  
✅ **Test Task**: `tasks/test_task.json` (task_id: `test_task`)  
✅ **Default Task ID**: `cleanliness-v0` (from agent card)


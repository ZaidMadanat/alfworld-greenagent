# Green Agent Reset Fix

## Issue Found
The reset was failing because of a **double slash in the URL**: `http://localhost:8335//reset` instead of `http://localhost:8335/reset`.

This happened because:
- Launcher URLs are stored with trailing slashes: `http://localhost:8335/`
- The code was doing: `f"{launcher_url}/reset"` 
- Result: `http://localhost:8335//reset` → 404 Not Found

## Fix Applied
Updated `agentbeats/src/backend/a2a_client.py` to strip trailing slashes before constructing URLs:

```python
# Before
response = await httpx_client.post(
    f"{launcher_url}/reset",
    json=reset_payload
)

# After
launcher_url_clean = launcher_url.rstrip("/")
response = await httpx_client.post(
    f"{launcher_url_clean}/reset",
    json=reset_payload
)
```

## Additional Improvements
1. **Added delay after reset**: 5-second wait before checking agent readiness (gives launcher time to restart)
2. **Improved launcher notification**: Better retry logic and error handling
3. **Extended timeout**: Launcher now waits up to 120 seconds (matches backend timeout)

## Next Steps
**Restart the AgentBeats backend** to apply the fix:

```bash
# Find and kill the backend process
pkill -f "agentbeats.*run_backend"
# Or if using deploy mode:
pkill -f "agentbeats.*deploy"

# Then restart (use your normal startup command)
cd agentbeats
agentbeats deploy --deploy_mode dev
```

After restarting, try running a battle again - the reset should work now!


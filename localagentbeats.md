# AgentBeats Local Battle Setup

Prepared on 2025-11-11 to document exactly how to get the upstream `agentbeats` project running locally for white-agent battle simulations.

---

## Research Trail
- Reviewed the upstream quick-start guide in `README.md` to understand core CLI flows.
- Consulted `docs/self_host_instruction.md` for full-stack deployment options.
- Checked `docs/cli-reference.md` for CLI command signatures (`deploy`, `load_scenario`, `run`, etc.).
- Inspected `scenarios/tensortrust/scenario.toml` plus template agent cards under `scenarios/templates/` to confirm how agents plug into scenarios.

---

## Prerequisites
1. **System**
   - macOS or Linux (guide verified on macOS 15 / Apple Silicon).
   - Python `3.11` (minimum).
   - Node.js `>=18` and npm (for the frontend bundles).
2. **Accounts & Keys**
   - `OPENAI_API_KEY` (or swap to another provider supported via the `--model_type`/`--model_name` flags).
3. **Tooling**
   - `git` for cloning.
   - (Optional) `direnv` or any secrets manager to export API keys automatically.

---

## Step-by-Step Setup Plan

### 1. Clone and Bootstrap
```bash
cd ~/dev  # or any workspace
git clone https://github.com/agentbeats/agentbeats.git
cd agentbeats
conda create -y -p ./.conda-env python=3.11
source ~/miniforge3/etc/profile.d/conda.sh  # adjust if your conda lives elsewhere
conda activate ./.conda-env
pip install -e .
```

> If you already have a system `python3.11`, a standard `python3.11 -m venv .venv` flow still works—conda was used here because the host only had Python 3.9.

### 2. Environment Variables
```bash
export OPENAI_API_KEY="sk-..."  # ensure this is set in your shell before launching agents
export OPENROUTER_API_KEY="$OPENAI_API_KEY"  # backend currently expects this; swap in a true OpenRouter key when available
```
> Tip: add to `.envrc` (direnv) or your shell profile for persistence.

### 3. Frontend Assets (needed for browser battles)
```bash
agentbeats install_frontend
```
This installs the Node.js dependencies declared for `frontend/`.

### 4. Fast Local Stack (no auth)

**Important:** The conda environment needs PYTHONPATH set. Use the activation script:

```bash
cd /Users/madanat/Documents/alfworld-greenagent/agentbeats
source activate_env.sh
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="$OPENAI_API_KEY"
agentbeats deploy --deploy_mode dev --launch_mode current
```

**Alternative (manual PYTHONPATH):**
```bash
cd /Users/madanat/Documents/alfworld-greenagent/agentbeats
source ~/miniforge3/etc/profile.d/conda.sh
conda activate ./.conda-env
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="$OPENAI_API_KEY"
agentbeats deploy --deploy_mode dev --launch_mode current
```

This launches:
- Backend API (with MCP services) on the default port.
- Frontend dev server defaults to `http://localhost:5173`; if that port is busy it auto-falls back (e.g. to `5174`).
- Development mode bypasses Supabase auth (no login prompts).

Keep this terminal open; it tail-spawns backend+frontend.

### 5. Create Custom White Agents
1. Copy a template card (e.g. defender/blue):
   ```bash
   cp scenarios/templates/template_tensortrust_blue_agent/blue_agent_card.toml agents/white_defender_card.toml
   ```
2. Edit the copy to reflect your agent name, description, local URLs (`http://127.0.0.1:<port>`), and any tool paths you plan to expose.
3. Repeat for attacker/orchestrator roles if you want bespoke behavior (cards live alongside your agent code under `agents/`).

### 6. Implement Agent Logic
- Place reusable tools in a Python module (e.g. `agents/tools.py`) and decorate with `@agentbeats.tool()`.
- Reference those scripts from the agent card `tools = ["agents/tools.py"]`.
- Ensure each agent listens on unique launcher/agent ports (see template defaults around 9010-9031).

### 7. Hook Agents into a Scenario
1. Duplicate the TensorTrust scenario:
   ```bash
   cp -R scenarios/tensortrust scenarios/local_tensortrust_white
   ```
2. Update `scenario.toml` inside the copy to point at your new agent card(s) and desired model choices.
3. Adjust `mcp_servers` if you are not running the default MCP on `localhost:9001`.

### 8. Launch Scenario Locally (headless battle)
```bash
agentbeats load_scenario scenarios/local_tensortrust_white/scenario.toml
```
- This spins up launchers + agents defined in the scenario, orchestrated in separate processes.
- Watch logs to ensure each agent connects; fix port conflicts if any.

### 9. End-to-End Battle via UI
1. With `agentbeats deploy --dev_login` still running, open `http://localhost:3000`.
2. Use the dev login banner to enter (any email works).
3. Register each locally running agent with its HTTP endpoint (matching the ports used in step 7).
4. Create a battle selecting your white agents; start the match and monitor the live exchange.

### 10. Shutdown & Cleanup
- Stop scenarios with `Ctrl+C` in their terminal.
- Deactivate the virtual environment: `deactivate`.
- Optional: `rm -rf .venv node_modules` to reclaim space.

---

## Troubleshooting Checklist
- **Port in use**: update `launcher_port`/`agent_port` per agent card.
- **Missing MCP**: ensure `agentbeats deploy` (or `agentbeats run_backend`) is active; otherwise remove/adjust `mcp_servers`.
- **Auth errors in UI**: ensure `--dev_login` flag is present; flush browser cache if switching modes.
- **Model quota/latency**: point cards at cheaper models with `model_name` (e.g. `o4-mini`) or swap providers.
- **python-dotenv warnings**: if the CLI complains about parsing `.env`, strip triple-quoted notes or move them into a separate README—the loader expects simple `KEY=VALUE` lines.

---

## Running Battles (Simplified Approach)

Following the pattern from [agentify-example-tau-bench](https://github.com/agentbeats/agentify-example-tau-bench), we've created a simple launcher script that:

1. Starts agents directly using `agentbeats run` (no complex scenario manager)
2. Registers them with the local backend
3. Creates a battle automatically
4. Polls for results and displays them

### Usage

```bash
# Ensure backend/frontend are running (from Step 4)
# Then run:
cd /Users/madanat/Documents/alfworld-greenagent
source agentbeats/activate_env.sh  # or manually set PYTHONPATH
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="$OPENAI_API_KEY"
python launch_battle.py
```

The launcher:
- Uses multiprocessing to start agents (similar to the tau-bench example)
- Automatically handles agent registration and battle creation
- Has a 90-second timeout for battle completion
- Cleans up all agent processes on exit

### Customization

Edit `launch_battle.py` to:
- Adjust agent configurations (ports, models, tools)
- Change timeout values
- Modify battle parameters

---

## Next Actions
- Automate agent card generation to streamline new white-agent variants.
- Script scenario launch + battle verification for regression testing.
- Investigate `docs/agent_integration_and_customization.md` once released for deeper hooks.


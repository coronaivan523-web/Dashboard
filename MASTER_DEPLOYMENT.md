# TITAN-OMNI Master Deployment (v4.4.2)

## 1. CI/CD Pipeline
- **Platform**: GitHub Actions
- **Workflow**: `.github/workflows/run_bot.yml`
- **Schedule**: Cron `*/15 * * * *` (Every 15 minutes)

### Workflow Steps
1.  **Checkout**: Uses `actions/checkout@v4`.
2.  **Setup Python**: Uses `actions/setup-python@v5` (v3.10).
3.  **Harden Dependencies**:
    - Checks for `requirements.txt`.
    - Installs using `pip install --require-hashes --no-deps`.
4.  **Execute**: Runs `python main.py` with injected secrets.
5.  **Artifacts**: Uploads `blackbox.log` (retention: 7 days).

## 2. Secrets Management
The following secrets MUST be defined in the GitHub Repository Environment:
- `SYSTEM_MODE`: "PAPER" or "LIVE".
- `KRAKEN_API_KEY`: Exchange API Key.
- `KRAKEN_SECRET`: Exchange Private Key.
- `SUPABASE_URL`: Database Endpoint.
- `SUPABASE_KEY`: Database Service Role Key.
- `OPENAI_API_KEY`: AI Model Access.
- `GROQ_API_KEY`: Inference Acceleration.
- `GEMINI_API_KEY`: Secondary AI Model.

## 3. Environment Specifications
### Cloud Runner (Ubuntu Latest)
- **Timezone**: UTC (Strict alignment required).
- **Network**: Public IP (Azure/AWS IP ranges must be allowed in Kraken).

### Local Environment (Windows/Dev)
- **Python**: 3.12 Recommended.
- **Dependency Management**:
    - Edit `requirements.in`.
    - Compile: `pip-compile --generate-hashes requirements.in`.
    - Install: `pip install --require-hashes --no-deps -r requirements.txt`.

## 4. Rollback Protocol
In case of critical failure (e.g., bad deployment or loop):
1.  **Disable Workflow**: Manually disable the GitHub Actions workflow.
2.  **Revert Commit**: `git revert HEAD` to the last known good state.
3.  **Flush Locks**: Manually delete the specific `cycle_id` from Supabase `execution_logs` if stuck (rare).

## 5. Hardening Measures
- **Fail-Closed**: Pipeline fails if dependencies are mismatched.
- **No-Deps**: Transitive dependencies must be explicit in lockfile.
- **Logs**: `PYTHONUNBUFFERED=1` ensures real-time capture.

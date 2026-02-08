# TITAN-OMNI Master Operations (v4.4.2)

## 1. Monitoring & Observability
### Blackbox Logs (`blackbox.log`)
- **Location**: Local filesystem (uploaded as Artifact).
- **Format**: `%(asctime)s [%(levelname)s] %(message)s`.
- **Key Events**:
    - `CYCLE START`: Initiation of run.
    - `EQUITY`: Current portfolio value.
    - `BUY/SELL`: Trade execution.
    - `ABORT`: Cycle termination reason.
    - `CRASH`: Unhandled exceptions.

### AI Payload (`execution_logs.ai_audit_payload`)
Inside Supabase `execution_logs` table JSONB column:
- `integrity`: Data gaps, timestamp alignment.
- `timing`: Network latency, total duration.
- `health`: RAM usage.
- `verdict`: Final decision and reason.
- `financials`: Mark-to-Market equity.

## 2. Incident Response (Runbooks)

### Scenario A: Cycle Abort Loop
**Symptoms**: CI/CD logs show repeated `ABORT` runs.
**Action**:
1.  Check `blackbox.log` artifact for `reason`.
2.  If `reason="TIMESTAMP_MISMATCH"`, verify Server Clock vs Exchange Clock.
3.  If `reason="API_LAG"`, check Kraken Status.
4.  If persistent, set `SYSTEM_MODE="PAPER"` in Secrets.

### Scenario B: Database Lock Stuck
**Symptoms**: Log shows `IDEMPOTENCY: ALREADY RAN` incorrectly.
**Action**:
1.  Query `execution_logs` for current `cycle_id`.
2.  If record exists but cycle failed mid-way, manual intervention required (delete row if re-run needed).
3.  **Note**: This acts as a circuit breaker. Usually safe to ignore until next 15m slot.

### Scenario C: Security Breach
**Symptoms**: Unknown IP executing trades or unauthorized env var change.
**Action**:
1.  **Kill Switch**: Delete `KRAKEN_API_KEY` from GitHub Secrets immediately.
2.  **Revoke**: Rotate API Keys in Kraken Dashboard.
3.  **Audit**: Check GitHub Actions logs for "Actor".

## 3. Maintenance
- **Dependency Update**:
    1.  Edit `requirements.in`.
    2.  Run `pip-compile --generate-hashes requirements.in`.
    3.  Commit `requirements.txt`.
- **Schema Update**:
    1.  Edit `data/schema.sql`.
    2.  Run SQL against Supabase Console.
    3.  Update `MASTER_DATABASE.md`.

# TITAN-OMNI Master Database (v4.4.2)

## 1. Overview
- **Database**: PostgreSQL (Supabase)
- **Schema Management**: Manual SQL (`data/schema.sql`).
- **Extensions**: `pgcrypto` for UUID generation.

## 2. Tables

### 2.1. `paper_wallet` (Multi-Asset)
Tracks simulated portfolio state.
- `id` (uuid, PK): Unique record ID.
- `created_at` (timestamptz): Timestamp of record.
- `cash_usd` (numeric): Available Simulated Cash.
- `asset_qty` (numeric): Held Crypto Quantity.
- `last_entry_price` (numeric): Average Entry Price.
- `cycle_id` (text): Link to execution cycle.
- `symbol` (text): Asset Symbol (e.g., 'BTC/USDT').
- `strategy_version` (text, default 'v4.4.2'): Version marker.
- **Constraints**: `UNIQUE(cycle_id, symbol)` ensures one wallet update per cycle per asset.
- **Indices**: `idx_wallet_latest` on `created_at DESC`.

### 2.2. `execution_logs` (Observability)
Logs every bot decision and state.
- `id` (uuid, PK): Unique Log ID.
- `cycle_id` (text, UNIQUE): Ensures idempotency.
- `created_at` (timestamptz): Execution time.
- `action` (text): Decision (BUY, SELL, HOLD, ABORT).
- `reason` (text): Explanation for action.
- `ai_audit_payload` (jsonb): Full telemetry dump (Latency, RAM, Indicators, AI Verdicts).
- `strategy_version` (text): Version marker.
- **Indices**:
    - `idx_logs_cycle` on `cycle_id`.
    - `idx_audit_payload` (GIN) for JSON querying.

### 2.3. `risk_state` (Daily Risk)
Tracks daily PnL and drawdown limits.
- `date` (date, PK): Trading Date.
- `starting_equity` (numeric): Equity at start of day.
- `created_at` (timestamptz): Record creation.

## 3. Operations
- **Locking**: `cycle_id` uniqueness prevents concurrent runs.
- **Migrations**: Changes must be applied via `data/schema.sql` (idempotent if possible).
- **Cleanup**: Log rotation handled manually or via Supabase cron (if configured).

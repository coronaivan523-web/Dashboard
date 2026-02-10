CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- v4.4.2: Multi-Asset Paper Wallet
CREATE TABLE IF NOT EXISTS paper_wallet (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    cash_usd numeric NOT NULL DEFAULT 0,
    asset_qty numeric NOT NULL DEFAULT 0,
    last_entry_price numeric NOT NULL DEFAULT 0,
    cycle_id text NOT NULL,
    symbol text NOT NULL, -- v4.4.2 Requirement
    strategy_version text NOT NULL DEFAULT 'v4.4.2',
    UNIQUE(cycle_id, symbol) -- Metric isolation
);

CREATE TABLE IF NOT EXISTS risk_state (
    date date PRIMARY KEY,
    starting_equity numeric NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- v4.4.2: Observability & Heartbeat
CREATE TABLE IF NOT EXISTS execution_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    action text NOT NULL,
    reason text NOT NULL DEFAULT '',
    ai_audit_payload jsonb,
    strategy_version text NOT NULL DEFAULT 'v4.4.2'
);

-- v4.4.2: Indexes
CREATE INDEX IF NOT EXISTS idx_logs_cycle ON execution_logs(cycle_id);
CREATE INDEX IF NOT EXISTS idx_wallet_latest ON paper_wallet(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_payload ON execution_logs USING GIN (ai_audit_payload);

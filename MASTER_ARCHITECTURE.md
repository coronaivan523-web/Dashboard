# TITAN-OMNI Master Architecture (v4.4.2)

## 1. System Overview
TITAN-OMNI is a high-frequency, AI-driven trading bot designed for the Kraken exchange. It operates on a strict 15-minute cycle, executing autonomous decisions based on technical analysis, AI consensus, and risk management rules.

### Core Philosophy
- **Fail-Closed**: Any anomaly, data gap, or security risk triggers an immediate abort.
- **Idempotency**: Each cycle is uniquely identified (`timestamp-symbol`) and locked to prevent duplicate execution.
- **Observability**: Complete "Black Box" logging of every decision, state change, and metric.

## 2. High-Level Architecture

### Components
1.  **Orchestrator (`main.py`)**:
    - Entry point triggered by CI/CD Cron.
    - Manages the lifecycle: Init -> Data Fetch -> Analysis -> Execution -> Commit.
    - Enforces "Iron Stealth" security protocols (RAM checks, timing).
2.  **AI Auditor (`core.ai_auditor.py`)**:
    - Dual-layer AI consensus mechanism (Primary + Secondary).
    - Validates trade signals against "Common Sense" and "Risk" models.
3.  **Risk Engine (`core.risk_engine.py`)**:
    - Deterministic rule engine for Drawdown, Volatility, and Spread protection.
    - Acts as the final "Veto" on any AI decision.
4.  **Execution Simulator (`core.execution_sim.py`)**:
    - Simulates order fills, slippage, and fee calculations.
    - Manages "Paper Wallet" state for simulation modes.
5.  **Data Layer (`data.supabase_client.py`)**:
    - interface to Supabase (PostgreSQL).
    - Handles Distributed Locking (`acquire_global_lock`).
    - Persists `execution_logs` and `paper_wallet` updates.

### Data Flow
1.  **Trigger**: GitHub Actions Schedule (*/15).
2.  **Lock**: `main.py` checks uniqueness in DB.
3.  **Input**: Fetch OHLCV, OrderBook, and Wallet Balance from Kraken/DB.
4.  **Process**:
    - Validation (Data Integrity, Timestamp Alignment).
    - Analysis (TA Lib, AI Auditor).
    - Decision (Risk Engine Veto).
5.  **Output**:
    - Execute Trade (Real or Paper).
    - Log Result (Supabase + Artifacts).

## 3. Key Modules & Versions
- **Python**: 3.10 (CI/CD), 3.12 (Local Dev).
- **Core Libs**: `ccxt`, `pandas`, `pandas_ta`, `supabase`.
- **AI Providers**: OpenAI, Groq, Gemini (via API).

## 4. Security & Hardening (v5.2)
- **Supply Chain**: Strict `requirements.txt` with SHA256 hashes.
- **Runtime**: RAM usage monitoring, Timeout watchdogs (20s).
- **Secrets**: Injected via Environment Variables; never logged.

## 5. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| API Latency | Strict timeout aborts; Local clock validation. |
| Flash Crash | `RiskEngine` volatility checks; `STOP_LOSS` simulation. |
| AI Hallucination | Dual-Council Consensus; Hard-coded risk bounds. |
| Replay Attacks | Cycle ID uniqueness constraint in DB. |

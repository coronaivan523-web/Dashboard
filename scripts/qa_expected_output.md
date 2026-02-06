# QA Validation: Smoke Test v3.8

This document outlines the required evidence for the TITAN-OMNI v3.8 Smoke Test.

## 1. Execution Logs (blackbox.log)
- [ ] **File Created**: `blackbox.log` exists after execution.
- [ ] **Initialization**: `TITAN-OMNI v3.8 INIT | Mode: PAPER | Cycle: 202X-...`
- [ ] **DB Connection**: `DB Connection Failed` should NOT appear.
- [ ] **Exchange**: `Exchange Connection: OK`.
- [ ] **Cycle Start**: `--- START CYCLE 202X-...`.
- [ ] **Cycle End**: `CYCLE END: SKIP` or `HOLD` or `BUY/SELL` (never partial crash).

## 2. Idempotency Check (Run 2)
- [ ] **Same Cycle ID**: The second run must use the EXACT same ISO timestamp 15m floor.
- [ ] **Skip Message**: `Cycle 202X-... already executed. SKIPPING.`
- [ ] **Clean Exit**: Process exits with code 0 (Success).

## 3. Database Integrity (Supabase)
- [ ] **execution_logs**:
    - `cycle_id`: Matches log timestamp.
    - `strategy_version`: `v3.8`.
    - `action`: One of (`BUY`, `SELL`, `HOLD`, `SKIP`, `KILL`).
    - `reason`: Not null.
    - `ai_audit_payload`: JSON or null.
- [ ] **paper_wallet**:
    - If `BUY` or `SELL`: New row inserted (Append-Only).
    - `cycle_id`: Matches execution log.
    - `last_entry_price`: Updated correctly.

## 4. Fail-Closed Validation
- [ ] **Metric**: `RUN1_EXIT=0` (Success/Skip/Kill handled).
- [ ] **Metric**: `RUN2_EXIT=0` (Idempotency Success).
- [ ] **Safety**: No API Keys visible in logs.

#!/bin/bash
set -euo pipefail

# 1. SETUP
echo "=== SMOKE TEST v3.8 START (Hardened) ==="
export SYSTEM_MODE="PAPER"
export PYTHONPATH="${PYTHONPATH:-.}"

# Cleanup logs
if [ -f blackbox.log ]; then
    rm blackbox.log
    echo "Logs cleaned."
else
    echo "No prior logs found."
fi

# 2. DETERMINISTIC CYCLE ID
# Calculate 15m floor in Python to ensure strict ISO compatibility
# This ensures that both Run 1 and Run 2 share the exact same ID regardless of execution time drift.
export CYCLE_ID_OVERRIDE=$(python3 -c "from datetime import datetime, timezone; now = datetime.now(timezone.utc); floored = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0); print(floored.isoformat())")

echo "TEST CYCLE ID: $CYCLE_ID_OVERRIDE"

# 3. EXECUTION 1 (Fresh Cycle)
echo "--- RUN 1: Fresh Cycle ---"
set +e
python3 main.py
RUN1_EXIT=$?
set -e
echo "RUN 1 Completed with EXIT code: $RUN1_EXIT"

# 4. EXECUTION 2 (Idempotency Check)
echo "--- RUN 2: Idempotency Check (Should SKIP using same ID) ---"
set +e
python3 main.py
RUN2_EXIT=$?
set -e
echo "RUN 2 Completed with EXIT code: $RUN2_EXIT"

# 5. METRICS & EVIDENCE
echo "=== METRICS ==="
if [ -f blackbox.log ]; then
    echo "BLACKBOX_EXISTS=true"
    echo "BLACKBOX_LINES=$(wc -l < blackbox.log)"
else
    echo "BLACKBOX_EXISTS=false"
    echo "BLACKBOX_LINES=0"
fi

echo "RUN1_EXIT=$RUN1_EXIT"
echo "RUN2_EXIT=$RUN2_EXIT"

echo "=== BLACKBOX LOG (LAST 40 LINES) ==="
if [ -f blackbox.log ]; then
    tail -n 40 blackbox.log
else
    echo "No log to show."
fi

# 6. FINAL VERDICT
# Run 1: Should be 0 (Success) or 1 (Kill - depending on env, but for smoke test pass we assume config is valid or handled gracefully)
# Actually per previous instruction: "si main.py termina con exit 0 en SKIP/HOLD, eso cuenta como éxito"
# Run 2: Must be 0 (Skip)
if [ $RUN1_EXIT -eq 0 ] && [ $RUN2_EXIT -eq 0 ]; then
    echo "SMOKE TEST: PASS"
    exit 0
else
    echo "SMOKE TEST: FAIL (Check Exit Codes)"
    exit 1
fi

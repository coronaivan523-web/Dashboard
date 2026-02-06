#!/bin/bash
export SYSTEM_MODE=PAPER
# Cycle ID override: 15m floor UTC
export CYCLE_ID_OVERRIDE=$(python -c "from datetime import datetime, timezone; now = datetime.now(timezone.utc); floored = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0); print(floored.isoformat())")

echo "Running Smoke Test Cycle: $CYCLE_ID_OVERRIDE"

echo "RUN 1..."
python main.py
EXIT1=$?

echo "RUN 2 (Idempotency)..."
python main.py
EXIT2=$?

if [ $EXIT1 -eq 0 ] && [ $EXIT2 -eq 0 ] && [ -f blackbox.log ]; then
    echo "SMOKE TEST: PASS"
    exit 0
else
    echo "SMOKE TEST: FAIL"
    exit 1
fi

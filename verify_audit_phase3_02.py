import sys
import os
import shutil
import json
from unittest.mock import MagicMock

# Add current path
sys.path.append(os.getcwd())

from core.risk_gate import RiskGate

# Override Env Vars required by RiskGate class loading
os.environ["MAX_DAILY_DRAWDOWN_PCT"] = "5.0"
os.environ["MAX_SPREAD_PCT"] = "0.5"

STATE_FILE = "data/risk_state.json"

def clean_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

def test_dynamic_drawdown():
    results = []
    
    print("--- TEST 1: STABLE EQUITY (EXPECT PASS) ---")
    clean_state()
    
    mock_exchange = MagicMock()
    mock_exchange.fetch_ticker.return_value = {'bid': 100, 'ask': 100.1} # spread ok
    mock_exchange.fetch_balance.return_value = {'total': {'USDT': 1000.0}}
    
    # 1st Run: Init Peak 1000, DD=0
    ok, reason, metrics = RiskGate.pre_trade_check(mock_exchange, "BTC/USDT")
    res = "PASS" if ok else "FAIL"
    print(f"Run 1 (Init): Result={res}, Metrics={metrics}")
    
    # 2nd Run: Equity 1000 -> 980 (2% Drop, < 5%). Pass.
    mock_exchange.fetch_balance.return_value = {'total': {'USDT': 980.0}}
    ok, reason, metrics = RiskGate.pre_trade_check(mock_exchange, "BTC/USDT")
    res = "PASS" if ok else "FAIL"
    print(f"Run 2 (Drop 2%): Result={res}, Metrics={metrics}")
    
    if ok and metrics['dd_pct'] == 2.0:
         results.append({"case": "Stable/Small Drop", "result": "PASS", "details": "DD calculated correctly below limit"})
    else:
         results.append({"case": "Stable/Small Drop", "result": "FAIL", "details": f"Failed or wrong calc: {metrics}"})

    print("\n--- TEST 2: CRASH EQUITY (EXPECT BLOCK) ---")
    # Peak is 1000. Drop to 900 (10% Drop > 5%). Should BLOCK.
    mock_exchange.fetch_balance.return_value = {'total': {'USDT': 900.0}}
    ok, reason, metrics = RiskGate.pre_trade_check(mock_exchange, "BTC/USDT")
    
    res = "BLOCK" if not ok else "PASS"
    print(f"Run 3 (Drop 10%): Result={res}, Reason={reason}, Metrics={metrics}")
    
    if not ok and "DRAWDOWN_EXCEEDED" in reason:
          results.append({"case": "Equity Crash", "result": "PASS", "details": "Blocked correctly due to DD"})
    else:
          results.append({"case": "Equity Crash", "result": "FAIL", "details": f"Did not block: {metrics}"})

    print("\n--- TEST 3: EQUITY MISSING (EXPECT FAIL-CLOSED) ---")
    # Mock exchange raising error or returning bad data
    mock_exchange_bad = MagicMock()
    mock_exchange_bad.fetch_ticker.return_value = {'bid': 100, 'ask': 100}
    # fetch_balance missing
    del mock_exchange_bad.fetch_balance
    
    ok, reason, metrics = RiskGate.pre_trade_check(mock_exchange_bad, "BTC/USDT")
    res = "BLOCK" if not ok else "PASS"
    print(f"Run 4 (No Balance): Result={res}, Reason={reason}")
    
    if not ok and "NO_BALANCE_METHOD" in reason:
          results.append({"case": "Equity Missing", "result": "PASS", "details": "Fail-closed correctly"})
    else:
          results.append({"case": "Equity Missing", "result": "FAIL", "details": f"Reason: {reason}"})

    clean_state()
    return results

if __name__ == "__main__":
    test_results = test_dynamic_drawdown()
    print("\n=== SUMMARY ===")
    for r in test_results:
        print(r)

import sys
import os
import json
import shutil
from unittest.mock import MagicMock, patch

# Add current path
sys.path.append(os.getcwd())

from main import TitanOmniBot

# Setup paths
CAPITAL_STATE_FILE = "data/capital_state.json"

def clean_state():
    if os.path.exists(CAPITAL_STATE_FILE):
        os.remove(CAPITAL_STATE_FILE)

def test_capital_management():
    results = []
    
    print("--- [SETUP] Cleaning State ---")
    clean_state()
    
    # --- TEST 1: NEW CYCLE ---
    # Scenario: No state file. Should create new cycle with current equity as base.
    print("\n--- TEST 1: NEW CYCLE (INIT BASE) ---")
    
    with patch('main.SupabaseClient') as mock_sup, \
         patch('main.preflight') as mock_pre:
         
        mock_sup.return_value = MagicMock()
        mock_pre.return_value = (True, "OK", {})
        
        bot = TitanOmniBot()
        bot.scanner = MagicMock()
        bot.scanner.scan_assets.return_value = ["BTC/USDT"]
        
        # Mock Exchange: Valid Balance
        mock_ex = MagicMock()
        mock_ex.fetch_balance.return_value = {'total': {'USDT': 1000.0}, 'free': {'USDT': 1000.0}}
        mock_ex.fetch_ohlcv.return_value = [[1,1,1,1,1,1]] * 300 # Bypass MTF
        mock_ex.fetch_ticker.return_value = {'bid': 100, 'ask': 100.1} # Bypass RiskGate
        bot.exchange = mock_ex
        bot.execution_engine = MagicMock() # Mock execution
        
        # Run Cycle
        bot.run_cycle()
        
        # Verify State File Created
        if os.path.exists(CAPITAL_STATE_FILE):
            with open(CAPITAL_STATE_FILE, "r") as f:
                state = json.load(f)
            
            print(f"State Created: {state}")
            if state["base_capital"] == 1000.0 and state["realized_profit"] == 0.0:
                print("Result: PASS (Base Capital Initialized)")
                results.append({"case": "New Cycle", "result": "PASS", "details": "Base=1000.0"})
            else:
                 print("Result: FAIL (Incorrect Base)")
                 results.append({"case": "New Cycle", "result": "FAIL", "details": f"Base={state['base_capital']}"})
        else:
             print("Result: FAIL (No State File)")
             results.append({"case": "New Cycle", "result": "FAIL", "details": "State file not created"})

    # --- TEST 2: PROFIT SEGREGATION ---
    # Scenario: State exists. Equity increases. Base Should REMAIN same. Profit should increase.
    print("\n--- TEST 2: PROFIT SEGREGATION (EQUITY UP) ---")
    
    with patch('main.SupabaseClient') as mock_sup, \
         patch('main.preflight') as mock_pre:
        
        mock_sup.return_value = MagicMock()
        mock_pre.return_value = (True, "OK", {})
        
        bot = TitanOmniBot()
        bot.scanner = MagicMock()
        bot.scanner.scan_assets.return_value = ["BTC/USDT"]
        
        # Mock Exchange: Higher Balance (Profit)
        mock_ex = MagicMock()
        mock_ex.fetch_balance.return_value = {'total': {'USDT': 1500.0}, 'free': {'USDT': 1500.0}}
        mock_ex.fetch_ohlcv.return_value = [[1,1,1,1,1,1]] * 300 
        mock_ex.fetch_ticker.return_value = {'bid': 100, 'ask': 100.1}
        bot.exchange = mock_ex
        bot.execution_engine = MagicMock()
        
        bot.run_cycle()
        
        # Verify
        with open(CAPITAL_STATE_FILE, "r") as f:
            state = json.load(f)
            
        print(f"State Updated: {state}")
        # Base must stay 1000. Realized Profit must be 500.
        if state["base_capital"] == 1000.0 and state["realized_profit"] == 500.0:
             print("Result: PASS (Profit Segregated)")
             results.append({"case": "Profit Segregation", "result": "PASS", "details": "Base=1000, Profit=500"})
        else:
             print("Result: FAIL (Segregation Failed)")
             results.append({"case": "Profit Segregation", "result": "FAIL", "details": f"Base={state['base_capital']}, Profit={state['realized_profit']}"})

    # --- TEST 3: FAIL CLOSED (CORRUPT STATE) ---
    print("\n--- TEST 3: FAIL CLOSED (CORRUPT STATE) ---")
    
    # Corrupt the file
    with open(CAPITAL_STATE_FILE, "w") as f:
        f.write("{corrupt_json: ...")
        
    with patch('main.SupabaseClient') as mock_sup, \
         patch('main.preflight') as mock_pre:
        
        mock_sup.return_value = MagicMock()
        mock_pre.return_value = (True, "OK", {})
        
        bot = TitanOmniBot()
        bot.scanner = MagicMock()
        bot.scanner.scan_assets.return_value = ["BTC/USDT"]
        
        mock_ex = MagicMock()
        mock_ex.fetch_balance.return_value = {'total': {'USDT': 1000.0}} # Valid balance, but state is bad
        # We need OHLCV to reach capital check logic inside loop? 
        # Actually main.py loop iterates assets. If capital check is inside loop, it runs.
        # But wait, Capital Manager init is inside loop? No, inside 'try' inside loop in implementation.
        # Ideally Capital Manager should be global/once, but in 'main.py' changes I put it inside loop.
        # Let's check logic:
        # "cap_mgr = CapitalManager(current_equity)" is inside the loop in my change.
        # So it will fail there.
        
        mock_ex.fetch_ohlcv.return_value = [[1,1,1,1,1,1]] * 300
        bot.exchange = mock_ex
        
        # Capture Logs/Errors by spying or checking execution count (should be 0)
        bot.execution_engine = MagicMock()
        
        bot.run_cycle()
        
        # If Logic works, it should catch Exception and BREAK loop.
        # How to check? Execution should NOT have happened (skipped DUST check, skipped execution)
        
        if not bot.execution_engine.execute.called:
             print("Result: PASS (Fail Closed on Corrupt State)")
             results.append({"case": "Corrupt State", "result": "PASS", "details": "Exec blocked"})
        else:
             print("Result: FAIL (Executed despite corrupt state)")
             results.append({"case": "Corrupt State", "result": "FAIL", "details": "Exec called"})
             
    # --- TEST 4: FAIL CLOSED (BALANCE FAIL) ---
    print("\n--- TEST 4: FAIL CLOSED (BALANCE FAIL) ---")
    clean_state() # Reset to valid state (or no state)
    
    with patch('main.SupabaseClient') as mock_sup, \
         patch('main.preflight') as mock_pre:
        
        mock_sup.return_value = MagicMock()
        mock_pre.return_value = (True, "OK", {})
        
        bot = TitanOmniBot()
        bot.scanner = MagicMock()
        bot.scanner.scan_assets.return_value = ["BTC/USDT"]
        
        mock_ex = MagicMock()
        mock_ex.fetch_balance.return_value = {} # Empty balance (Fail)
        mock_ex.fetch_ohlcv.return_value = [[1,1,1,1,1,1]] * 300
        bot.exchange = mock_ex
        bot.execution_engine = MagicMock()
        
        bot.run_cycle()
        
        if not bot.execution_engine.execute.called:
             print("Result: PASS (Fail Closed on missing Balance)")
             results.append({"case": "Missing Balance", "result": "PASS", "details": "Exec blocked"})
        else:
             print("Result: FAIL (Executed despite missing balance)")
             results.append({"case": "Missing Balance", "result": "FAIL", "details": "Exec called"})

    return results

if __name__ == "__main__":
    test_results = test_capital_management()
    print("\n=== SUMMARY ===")
    for r in test_results:
        print(r)

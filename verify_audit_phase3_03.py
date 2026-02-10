import sys
import os
import pandas as pd
from unittest.mock import MagicMock, patch

# Add current path
sys.path.append(os.getcwd())

from main import TitanOmniBot
from core.market_regime import MarketRegime

# Helper to gen OHLCV
def gen_ohlcv(price, trend="FLAT"):
    data = []
    base = price
    for i in range(300):
        if trend == "BULL": base *= 1.001
        elif trend == "BEAR": base *= 0.999
        data.append([1000+i, base, base+1, base-1, base, 100])
    return data

@patch('main.SupabaseClient')
@patch('main.preflight')
def test_mtf_veto(mock_preflight, mock_supabase_cls):
    results = []
    
    # Mock preflight and Supabase
    mock_preflight.return_value = (True, "OK", {})
    mock_supabase_cls.return_value = MagicMock()
    
    print("--- TEST 1: ALIGNED (MICRO BULL / MACRO BULL) -> PASS ---")
    bot = TitanOmniBot()
    bot.scanner = MagicMock()
    bot.scanner.scan_assets.return_value = ["BTC/USDT"]
    
    # Mock Exchange
    mock_ex = MagicMock()
    mock_ex.fetch_balance.return_value = {'free': {'USDT': 1000}, 'total': {'USDT': 1000}} # Capital OK
    
    def side_effect_ohlcv(symbol, timeframe, limit):
        if timeframe == '15m': return gen_ohlcv(100, "BULL")
        if timeframe == '1h': return gen_ohlcv(100, "BULL")
        if timeframe == '4h': return gen_ohlcv(100, "BULL")
        return []
    
    mock_ex.fetch_ohlcv.side_effect = side_effect_ohlcv
    mock_ex.fetch_ticker.return_value = {'bid': 100, 'ask': 100.1} # Spread OK
    bot.exchange = mock_ex
    bot.execution_engine = MagicMock() # Mock execution
    bot.execution_engine.execute.return_value = {'status': 'FILLED', 'fill_price': 100}
    bot.auditor = MagicMock()
    bot.auditor.audit_intent.return_value = (True, "OK") # AI Approves
    
    # Run
    bot.run_cycle()
    
    if bot.execution_engine.execute.called:
         print("Result: TRADE EXECUTED (PASS)")
         results.append({"case": "Aligned (BULL/BULL)", "result": "PASS", "details": "Trade executed"})
    else:
         print("Result: NO TRADE (FAIL)")
         results.append({"case": "Aligned (BULL/BULL)", "result": "FAIL", "details": "Trade blocked unexpected"})

    print("\n--- TEST 2: MISALIGNED (MICRO BULL / MACRO BEAR) -> VETO ---")
    bot2 = TitanOmniBot()
    bot2.scanner = MagicMock()
    bot2.scanner.scan_assets.return_value = ["BTC/USDT"]
    mock_ex2 = MagicMock()
    mock_ex2.fetch_balance.return_value = {'free': {'USDT': 1000}, 'total': {'USDT': 1000}}
    
    def side_effect_ohlcv_veto(symbol, timeframe, limit):
        if timeframe == '15m': return gen_ohlcv(100, "BULL")
        if timeframe == '1h': return gen_ohlcv(100, "BEAR") # Conflict
        if timeframe == '4h': return gen_ohlcv(100, "SIDEWAYS")
        return []
        
    mock_ex2.fetch_ohlcv.side_effect = side_effect_ohlcv_veto
    mock_ex2.fetch_ticker.return_value = {'bid': 100, 'ask': 100.1}
    bot2.exchange = mock_ex2
    bot2.execution_engine = MagicMock()
    bot2.auditor = MagicMock()
    bot2.auditor.audit_intent.return_value = (True, "OK") # AI Approves
    
    bot2.run_cycle()
    
    if not bot2.execution_engine.execute.called:
         print("Result: NO TRADE (PASS - Vetoed)")
         results.append({"case": "Misaligned (BULL/BEAR)", "result": "PASS", "details": "Trade vetoed correctly"})
    else:
         print("Result: TRADE EXECUTED (FAIL - Should Veto)")
         results.append({"case": "Misaligned (BULL/BEAR)", "result": "FAIL", "details": "Trade executed despite veto"})

    print("\n--- TEST 3: DATA MISSING -> FAIL CLOSED ---")
    bot3 = TitanOmniBot()
    bot3.scanner = MagicMock()
    bot3.scanner.scan_assets.return_value = ["BTC/USDT"]
    mock_ex3 = MagicMock()
    mock_ex3.fetch_balance.return_value = {'free': {'USDT': 1000}, 'total': {'USDT': 1000}}
    
    def side_effect_ohlcv_missing(symbol, timeframe, limit):
        if timeframe == '15m': return gen_ohlcv(100, "BULL")
        return [] # Empty for others
        
    mock_ex3.fetch_ohlcv.side_effect = side_effect_ohlcv_missing
    mock_ex3.fetch_ticker.return_value = {'bid': 100, 'ask': 100.1}
    bot3.exchange = mock_ex3
    bot3.execution_engine = MagicMock()
    bot3.auditor = MagicMock()
    
    bot3.run_cycle()
    
    if not bot3.execution_engine.execute.called:
         print("Result: NO TRADE (PASS - Fail Closed)")
         results.append({"case": "Data Missing", "result": "PASS", "details": "Fail-closed correctly"})
    else:
         print("Result: TRADE EXECUTED (FAIL)")
         results.append({"case": "Data Missing", "result": "FAIL", "details": "Trade executed despite missing data"})

    return results

if __name__ == "__main__":
    test_results = test_mtf_veto()
    print("\n=== SUMMARY ===")
    for r in test_results:
        print(r)

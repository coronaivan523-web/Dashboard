import os
import sys
import logging
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timezone
from dotenv import load_dotenv

from core.risk_engine import RiskEngine
from core.ai_auditor import AIAuditor
from core.execution_sim import ExecutionSimulator
from data.supabase_client import SupabaseClient

load_dotenv()
SYSTEM_MODE = os.getenv("SYSTEM_MODE", "PAPER").upper()
SYMBOL, TIMEFRAME = "BTC/USD", "15m"
START_CAPITAL = 10000.0

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.FileHandler("blackbox.log"), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("TITAN-OMNI")

class TitanOmniBot:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.cycle_id = now.replace(minute=(now.minute//15)*15, second=0, microsecond=0).isoformat()
        
        self.supabase = SupabaseClient()
        self.risk = RiskEngine()
        self.auditor = AIAuditor()
        self.sim = ExecutionSimulator()
        self.exchange = self._init_exchange()

    def _init_exchange(self):
        try: return ccxt.kraken({'apiKey': os.getenv("KRAKEN_API_KEY"), 'secret': os.getenv("KRAKEN_SECRET"), 'enableRateLimit': True})
        except: sys.exit(1)

    def _get_market_data(self):
        try:
            # Ticker Fail-Closed Guard
            ticker = self.exchange.fetch_ticker(SYMBOL)
            if not ticker or ticker['bid'] is None or ticker['ask'] is None:
                spread_pct = 1.0 # Force SKIP
            else:
                spread_pct = (ticker['ask'] - ticker['bid']) / ticker['ask']
            
            df = pd.DataFrame(self.exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=250), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.ta.rsi(length=14, append=True)
            df.ta.ema(length=200, append=True)
            df.ta.atr(length=14, append=True)
            return df.iloc[-1], spread_pct
        except Exception as e:
            logger.error(f"DATA ERROR: {e}"); sys.exit(1)

    def _get_paper_wallet(self):
        last = self.supabase.get_latest_paper_state()
        if last: return last['cash_usd'], last['asset_qty'], last['last_entry_price']
        return START_CAPITAL, 0.0, 0.0

    def run(self):
        logger.info(f"TITAN-OMNI v3.8 | CYCLE {self.cycle_id} | MODE: {SYSTEM_MODE}")
        if self.supabase.check_log_exists(self.cycle_id): logger.warning("IDEMPOTENCY: ALREADY RAN"); sys.exit(0)
        
        candle, spread_pct = self._get_market_data()
        price, rsi, ema, atr = candle['close'], candle['RSI_14'], candle['EMA_200'], candle['ATRr_14']
        
        cash, asset, entry_price = self._get_paper_wallet()
        status = "INVESTED" if asset * price > 10.0 else "CASH"
        
        # Drawdown Simulation
        equity = cash + (asset * price)
        dd = (equity - START_CAPITAL) / START_CAPITAL
        
        logger.info(f"{SYMBOL}: {price} | RSI: {rsi:.1f} | SPREAD: {spread_pct:.4%} | EQUITY: {equity:.2f}")

        risk_status, risk_reason = self.risk.evaluate(dd, spread_pct, atr/price)
        if risk_status != "OK":
            logger.warning(f"RISK {risk_status}: {risk_reason}")
            self.supabase.log_execution(self.cycle_id, risk_status, risk_reason)
            return

        decision, log_reason, audit_payload = "HOLD", "No signal", None

        if status == "CASH" and rsi < 30 and price > ema:
            audit = self.auditor.audit("BUY_RSI_OVERSOLD_TREND_UP", "Neutral Context")
            audit_payload = audit
            if audit['status'] == "APPROVED": decision, log_reason = "BUY", f"AI: {audit.get('reason')}"
            else: log_reason = f"AI Veto: {audit.get('reason')}"
        
        elif status == "INVESTED":
            stop_loss = entry_price * 0.98
            if rsi > 70: decision, log_reason = "SELL", "RSI Overbought"
            elif price < stop_loss: decision, log_reason = "SELL", "Stop Loss Hit"

        if decision == "BUY":
            qty, fill = self.sim.simulate_buy(price, cash)
            # Corrected call with cycle_id
            self.supabase.update_paper_state(self.cycle_id, 0.0, qty, fill)
            logger.info(f"PAPER BUY: {qty} @ {fill}")

        elif decision == "SELL":
            usd, fill = self.sim.simulate_sell(price, asset)
            # Corrected call with cycle_id
            self.supabase.update_paper_state(self.cycle_id, usd, 0.0, 0.0)
            logger.info(f"PAPER SELL: {usd} @ {fill}")

        self.supabase.log_execution(self.cycle_id, decision, log_reason, audit_payload)
        logger.info("DONE")

if __name__ == "__main__":
    try: TitanOmniBot().run()
    except Exception as e: logger.critical(f"CRASH: {e}"); sys.exit(1)

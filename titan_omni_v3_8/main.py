import sys
import logging
from datetime import datetime, timezone
from config import settings
from core.market_data import MarketDataProvider
from core.risk_engine import RiskEngine
from core.ai_auditor import AIAuditor
from core.execution_sim import ExecutionSimulator
from data.supabase_client import SupabaseClient

# LOGGING
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.FileHandler("blackbox.log"), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("TITAN-OMNI")

class TitanOmniBot:
    def __init__(self):
        if settings.SYSTEM_MODE != "PAPER":
            logger.critical("LIVE MODE BLOCKED")
            sys.exit(1)
            
        # 1. Cycle ID
        if settings.CYCLE_ID_OVERRIDE:
             self.cycle_id = settings.CYCLE_ID_OVERRIDE
        else:
             now = datetime.now(timezone.utc)
             self.cycle_id = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0).isoformat()
             
        # Engines
        self.market = MarketDataProvider()
        self.risk = RiskEngine()
        self.auditor = AIAuditor()
        self.sim = ExecutionSimulator()
        self.db = SupabaseClient() # Fail-closed init

    def run(self):
        logger.info(f"CYCLE {self.cycle_id} START")
        
        # 2. Idempotency
        if self.db.check_log_exists(self.cycle_id):
            logger.warning(f"Cycle {self.cycle_id} already executed. SKIPPING.")
            sys.exit(0)

        # 3. Market Data
        data = self.market.get_data(settings.SYMBOL, settings.TIMEFRAME)
        if not data:
            self.db.log_execution(self.cycle_id, "SKIP", "Market Data Unavailable", None)
            return

        price = data['price']
        rsi = data['rsi']
        ema = data['ema_200']
        atr = data['atr']
        spread_pct = data['spread_pct']
        vol_ratio = atr / price if price > 0 else 0
        
        # 6. Paper State
        cash, asset_qty, entry_price = self.db.get_latest_paper_state()
        
        # 7. Drawdown
        equity = cash + (asset_qty * price)
        dd_pct = (equity - settings.START_CAPITAL) / settings.START_CAPITAL
        
        # 8. Risk Engine
        risk_status, risk_reason = self.risk.evaluate(dd_pct, spread_pct, vol_ratio)
        if risk_status == "KILL":
            self.db.log_execution(self.cycle_id, "KILL", risk_reason, None)
            sys.exit(1) # OR just return, but prompt says Kill switch
        elif risk_status == "SKIP":
            self.db.log_execution(self.cycle_id, "SKIP", risk_reason, None)
            return

        # 9. Tech Signal
        action = "HOLD"
        reason = "No signal"
        
        # Status
        status = "INVESTED" if asset_qty * price > 10 else "CASH" # USD dust
        
        if status == "CASH":
            if rsi < 30 and price > ema:
                # ENTRY SIGNAL
                # 10. AI Auditor
                audit = self.auditor.audit("BUY_SIGNAL", {"rsi": rsi, "trend": "UP"})
                
                if audit['status'] == "APPROVED" and audit['risk_level'] == "LOW":
                    action = "BUY"
                    reason = f"Signal + AI Approved: {audit.get('reason')}"
                else:
                    action = "HOLD" # Or SKIP? HOLD is safer.
                    reason = f"AI Veto: {audit.get('reason')}"
                    
        elif status == "INVESTED":
            stop_loss = entry_price * 0.98
            if rsi > 70:
                action = "SELL"
                reason = "RSI > 70"
            elif price < stop_loss:
                action = "SELL"
                reason = "Stop Loss Hit"
                
        # 11. Execution
        if action == "BUY":
            qty, remaining_cash = self.sim.simulate_buy(price, cash)
            # Persist Paper Wallet
            self.db.insert_paper_state(self.cycle_id, 0.0, qty, price) # Assuming all-in
            # Actually sim returns qty, 0.0; insert 0.0 cash, qty asset, last is price
            
        elif action == "SELL":
            proceeds = self.sim.simulate_sell(price, asset_qty)
            # Persist
            new_cash = cash + proceeds
            self.db.insert_paper_state(self.cycle_id, new_cash, 0.0, 0.0)

        # 12. Log Execution
        self.db.log_execution(self.cycle_id, action, reason, None)
        logger.info(f"CYCLE END: {action} ({reason})")

if __name__ == "__main__":
    bot = TitanOmniBot()
    bot.run()

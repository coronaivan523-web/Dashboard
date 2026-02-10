from typing import Tuple
from decimal import Decimal

class RiskEngine:
    def __init__(self, max_daily_drawdown: float = 0.02, max_spread: float = 0.005, max_volatility: float = 0.05):
        self.max_daily_drawdown = Decimal(str(max_daily_drawdown))
        self.max_spread = Decimal(str(max_spread))
        self.max_volatility = Decimal(str(max_volatility))

    def evaluate(self, current_dd_pct: float, spread_pct: float, volatility_ratio: float) -> Tuple[str, str]:
        # HARDENING: Decimal Conversion
        try:
            dd = Decimal(str(current_dd_pct))
            spread = Decimal(str(spread_pct))
            vol = Decimal(str(volatility_ratio))
            
            # KILL SWITCH
            if dd <= -self.max_daily_drawdown:
                return "KILL", f"Drawdown {dd:.2%} exceeds limit"
            
            # SKIP CONDITIONS
            if spread >= self.max_spread:
                return "SKIP", f"High Spread: {spread:.2%}"

            if vol >= self.max_volatility:
                return "SKIP", f"Extreme Volatility: {vol:.2f}"

            return "OK", "Risk Checks Passed"
        except:
            return "KILL", "MATH_ERROR_IN_RISK_CHECK"

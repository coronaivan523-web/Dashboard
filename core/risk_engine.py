from typing import Tuple

class RiskEngine:
    def __init__(self, max_daily_drawdown: float = 0.02, max_spread: float = 0.005, max_volatility: float = 0.05):
        self.max_daily_drawdown = max_daily_drawdown
        self.max_spread = max_spread
        self.max_volatility = max_volatility

    def evaluate(self, current_dd_pct: float, spread_pct: float, volatility_ratio: float) -> Tuple[str, str]:
        # KILL SWITCH
        if current_dd_pct <= -self.max_daily_drawdown:
            return "KILL", f"Drawdown {current_dd_pct:.2%} exceeds limit"
        
        # SKIP CONDITIONS
        if spread_pct >= self.max_spread:
            return "SKIP", f"High Spread: {spread_pct:.2%}"

        if volatility_ratio >= self.max_volatility:
            return "SKIP", f"Extreme Volatility: {volatility_ratio:.2f}"

        return "OK", "Risk Checks Passed"

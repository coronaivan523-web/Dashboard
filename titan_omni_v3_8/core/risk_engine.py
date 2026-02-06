class RiskEngine:
    def __init__(self, max_dd_pct=0.02, max_spread=0.005, max_vol_ratio=0.05):
        self.max_dd_pct = max_dd_pct
        self.max_spread = max_spread
        self.max_vol_ratio = max_vol_ratio

    def evaluate(self, current_dd_pct, spread_pct, volatility_ratio):
        # 1. Kill Switch
        if current_dd_pct <= -self.max_dd_pct:
            return "KILL", f"Drawdown {current_dd_pct*100:.2f}% < -{self.max_dd_pct*100:.2f}%"
        
        # 2. Skip Checks
        if spread_pct is None or spread_pct > self.max_spread:
             return "SKIP", f"Spread {spread_pct} > {self.max_spread}" if spread_pct else "SKIP: Invalid Spread"
             
        if volatility_ratio is None or volatility_ratio > self.max_vol_ratio:
             return "SKIP", f"Vol {volatility_ratio} > {self.max_vol_ratio}" if volatility_ratio else "SKIP: Invalid Vol"
             
        # 3. OK
        return "OK", "Risk Checks Passed"

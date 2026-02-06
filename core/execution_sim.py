from dataclasses import dataclass

@dataclass
class ExecParams:
    taker_fee_rate: float = 0.0026 
    slippage_rate: float = 0.001   
    spread_rate: float = 0.0005 

class ExecutionSimulator:
    def __init__(self, params: ExecParams | None = None):
        self.p = params or ExecParams()

    def simulate_buy(self, mid_price: float, capital: float):
        if mid_price <= 0 or capital <= 0: return 0.0, 0.0
        # Ask price logic
        half_spread = mid_price * (self.p.spread_rate / 2)
        exec_price = (mid_price + half_spread) * (1 + self.p.slippage_rate)
        
        effective_capital = capital * (1 - self.p.taker_fee_rate)
        qty = effective_capital / exec_price
        return qty, exec_price

    def simulate_sell(self, mid_price: float, qty: float):
        if mid_price <= 0 or qty <= 0: return 0.0, 0.0
        # Bid price logic
        half_spread = mid_price * (self.p.spread_rate / 2)
        exec_price = (mid_price - half_spread) * (1 - self.p.slippage_rate)
        
        gross_value = qty * exec_price
        net_value = gross_value * (1 - self.p.taker_fee_rate)
        return net_value, exec_price

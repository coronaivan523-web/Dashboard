class ExecutionSimulator:
    def __init__(self, taker_fee=0.0026, slippage=0.001):
        self.taker_fee = taker_fee
        self.slippage = slippage

    def simulate_buy(self, price, cash):
        if price <= 0 or cash <= 0:
            return 0.0, cash
        
        # Buy at Ask (approx price + slippage) -> Simplified logic as per v3.8 spec
        exec_price = price * (1 + self.slippage)
        
        # Fee deduction from cash or asset? 通常 deduct from cash effectively
        # effective_cash = cash * (1 - self.taker_fee)
        # qty = effective_cash / exec_price
        
        # Logic from spec: simulate_buy(price, cash) -> (qty, remaining_cash) - wait, spec says simulate_buy returns qty, remaining_cash ?? 
        # Checking spec: "simulate_buy(price, cash) -> (qty, remaining_cash)" 
        # NO, wait context from previous turn says: simulate_buy returns (qty, exec_price)
        # Let's clean this.
        
        # Re-reading prompt H): simulate_buy(price, cash) -> (qty, remaining_cash) ? OR (qty, fill)?
        # Implementation spec G says: simulate_buy(price, cash) -> (qty, remaining_cash)
        # Okay, adhering to Prompt G.
        
        effective_cash = cash * (1 - self.taker_fee)
        qty = effective_cash / exec_price
        
        return qty, 0.0 # All in

    def simulate_sell(self, price, qty):
        if price <= 0 or qty <= 0:
            return 0.0
            
        exec_price = price * (1 - self.slippage)
        gross_value = qty * exec_price
        net_value = gross_value * (1 - self.taker_fee)
        
        return net_value

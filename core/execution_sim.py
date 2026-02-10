from dataclasses import dataclass
from decimal import Decimal, getcontext
import os

# HARDENING: IEEE 754 Fix
getcontext().prec = 28
TAKER_FEE = Decimal(os.getenv("TAKER_FEE", "0.0026"))

@dataclass
class ExecParams:
    taker_fee_rate: Decimal = TAKER_FEE
    slippage_rate: Decimal = Decimal("0.001")
    spread_rate: Decimal = Decimal("0.0005")

class ExecutionSimulator:
    def __init__(self, params: ExecParams | None = None):
        self.p = params or ExecParams()

    # v4.4 PESSIMISTIC FORENSICS: Path Analysis & Worst Case
    def check_path_analysis(self, prev_candle: dict, stop_loss: float, current_open: float):
        # prev_candle must have 'open', 'high', 'low', 'close'
        try:
            p_open = Decimal(str(prev_candle['open']))
            p_high = Decimal(str(prev_candle['high']))
            p_low = Decimal(str(prev_candle['low']))
            stop = Decimal(str(stop_loss))
            c_open = Decimal(str(current_open))
            
            # RULE 1: GAP RISK (Opening lower than SL)
            # If the NEW candle opens below the SL, we effectively exited at Open (or worse).
            # We check this first because it implies we held THROUGH the previous candle.
            # Wait, if we held through previous candle, did we hit SL *during* previous candle?
            
            # Sequence of evaluation as per v4.4 spec:
            # a) GAP RISK (actually refers to the Open of the *current* candle vs SL, if we survived prev)
            # b) SL/TP CONFLICT (during prev candle)
            # c) SL ONLY (during prev candle)
            
            # However, if we hit SL in prev candle, we are already out. 
            # Gap risk usually allows expanding the loss if Open < SL.
            
            # Let's check Prev Candle first (The "Ghost" period)
            
            # 1. Intra-Candle Conflict / Worst Case SL
            # If Low <= SL, we hit it. Even if High >= TP, SL is assumed first.
            if p_low <= stop:
                # We hit SL in the previous candle.
                # Did we gap down *into* the previous candle? 
                # Pessimistic: Exit at Stop Loss - Slippage
                slippage = stop * self.p.slippage_rate
                
                # Check for Gap Down on Prev Candle Open
                if p_open < stop:
                     # We gapped down entering the previous candle (or just opened below)
                     # Exit at Prev Open
                     return float(p_open), "GAP_EXIT_PREV"
                
                # Normal SL hit during candle
                return float(stop - slippage), "WORST_CASE_SL_TAKEN"

            # 2. Gap Risk on Current Open
            # If we survived prev candle, but current open is below SL (Gap Down)
            if c_open < stop:
                # User Rule: Exit_Price = min(Stop_Loss, Candle_Open) - Slippage
                # Since Open < SL, Exit = Open - Slippage
                slippage = c_open * self.p.slippage_rate
                return float(c_open - slippage), "GAP_EXIT_CURRENT"

            return None, None
        except:
            return None, None

    # v4.3 FORENSIC SIMULATION: VWAP Calculation
    def calculate_vwap_buy(self, order_book: dict, capital: float):
        # Order Book: {'asks': [[price, qty], ...], 'bids': ...}
        try:
            cap_needed = Decimal(str(capital))
            total_cost = Decimal("0")
            total_qty = Decimal("0")
            
            for price, qty in order_book['asks']:
                p = Decimal(str(price))
                q = Decimal(str(qty))
                
                cost = p * q
                if total_cost + cost >= cap_needed:
                    # Partial fill of this level
                    remaining_cap = cap_needed - total_cost
                    partial_qty = remaining_cap / p
                    total_cost += remaining_cap
                    total_qty += partial_qty
                    break
                else:
                    total_cost += cost
                    total_qty += q
            
            if total_qty == 0: return 0.0 # No liquidity
            
            vwap = total_cost / total_qty
            return float(vwap)
        except:
            return 0.0

    def calculate_vwap_sell(self, order_book: dict, qty_to_sell: float):
        try:
            qty_needed = Decimal(str(qty_to_sell))
            total_qty = Decimal("0")
            total_revenue = Decimal("0")
            
            for price, qty in order_book['bids']:
                p = Decimal(str(price))
                q = Decimal(str(qty))
                
                if total_qty + q >= qty_needed:
                    remaining_qty = qty_needed - total_qty
                    total_revenue += remaining_qty * p
                    total_qty += remaining_qty
                    break
                else:
                    total_revenue += q * p
                    total_qty += q
            
            if total_qty == 0: return 0.0
            
            vwap = total_revenue / total_qty
            return float(vwap)
        except:
            return 0.0

    def simulate_buy(self, vwap_price: float, capital: float, atr: float):
        # v4.3: Input is now VWAP from Order Book, not just Ask
        try:
            vwap = Decimal(str(vwap_price))
            cap = Decimal(str(capital))
            volatility = Decimal(str(atr))
            
            if vwap <= 0 or cap <= 0: return 0.0, 0.0
            
            # v4.3: Apply Spread Penalty on top of VWAP if needed, 
            # but VWAP itself accounts for depth. 
            # We add explicit slippage for latency.
            latency_slippage = volatility * Decimal("0.05") 
            exec_price = vwap + latency_slippage
            
            fee = cap * self.p.taker_fee_rate
            effective_capital = cap - fee
            
            if effective_capital <= 0: return 0.0, 0.0
            
            qty = effective_capital / exec_price
            
            return float(qty), float(exec_price)
        except:
            return 0.0, 0.0

    def simulate_sell(self, vwap_price: float, qty: float, atr: float):
        try:
            vwap = Decimal(str(vwap_price))
            quantity = Decimal(str(qty))
            volatility = Decimal(str(atr))
            
            if vwap <= 0 or quantity <= 0: return 0.0, 0.0
            
            # v4.3: Latency Slippage
            latency_slippage = volatility * Decimal("0.05")
            exec_price = vwap - latency_slippage
            
            gross_value = quantity * exec_price
            if gross_value <= 0: return 0.0, 0.0
            
            fee = gross_value * self.p.taker_fee_rate
            net_value = gross_value - fee
            
            return float(net_value), float(exec_price)
        except:
            return 0.0, 0.0
    # v4.4.2 EQUITY HEARTBEAT: Mark-to-Market Valuation
    def calculate_total_equity(self, bid_price: float, asset_qty: float, cash_balance: float):
        # STRICT RULE: Use Decimal EXCLUSIVELY for valuation
        try:
            bid = Decimal(str(bid_price))
            qty = Decimal(str(asset_qty))
            cash = Decimal(str(cash_balance))
            
            # Logic: Cash + (Asset * Bid) - Taker Fee (Liquidation Cost PESSIMISTIC)
            # Prompt says: IF position == LONG: return balance_usd + (asset_amount * bid_price)
            # It implies raw valuation. But "Valoración PESIMISTA" usually implies liquidation value.
            # User Rule: "IF position == LONG: return balance_usd + (asset_amount * bid_price)"
            # It does NOT explicitly ask for fee deduction here, just Bid price usage.
            # I will follow the explicit logic: balance + value at bid.
            
            val_asset = qty * bid
            total_equity = cash + val_asset
            
            # Sanity check: Non-negative
            if total_equity < 0: return Decimal("0.00")
            
            return total_equity
        except:
            return Decimal("0.00")

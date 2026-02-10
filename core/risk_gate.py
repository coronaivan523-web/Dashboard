import os
import json
import logging
from typing import Tuple, Dict, Optional, Any

logger = logging.getLogger("TITAN-OMNI.RISK_GATE")

class DynamicDrawdown:
    """
    Maneja el estado de Drawdown persistente (Lazy Load).
    Archivo: data/risk_state.json
    Estructura: {"peak_equity": float, "last_update": str}
    """
    STATE_FILE = "data/risk_state.json"

    def __init__(self):
        self.peak_equity = None
        self._load_state()

    def _load_state(self):
        """Carga peak_equity de disco. Si error -> None (Fail-Closed en uso)."""
        if not os.path.exists(self.STATE_FILE):
            return 
        
        try:
            with open(self.STATE_FILE, "r") as f:
                data = json.load(f)
                self.peak_equity = data.get("peak_equity")
        except Exception as e:
            logger.critical(f"RISK STATE CORRUPT: {e}")
            # Si el archivo existe pero está corrupto, lanzamos excepción para FAIL-CLOSED arriba.
            raise RuntimeError(f"RISK_STATE_CORRUPT: {e}")

    def update(self, current_equity: float) -> float:
        """
        Actualiza peak_equity y calcula drawdown %.
        Retorna: dd_pct
        """
        # Init lazy si es primera vez
        if self.peak_equity is None:
            self.peak_equity = current_equity
            self._persist_state()
            return 0.0

        # Update Peak
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self._persist_state()

        # Calculate DD calculation
        # DD = (Peak - Current) / Peak
        if self.peak_equity <= 0: return 0.0 # Avoid div/0 logic safeguard
        
        dd_pct = ((self.peak_equity - current_equity) / self.peak_equity) * 100
        return dd_pct

    def _persist_state(self):
        """Guarda estado en disco."""
        try:
            os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)
            with open(self.STATE_FILE, "w") as f:
                json.dump({"peak_equity": self.peak_equity}, f)
        except Exception as e:
            logger.error(f"FAILED TO PERSIST RISK STATE: {e}")
            # No bloqueamos trading por falla de *escritura* de nuevo peak, 
            # pero logueamos severo. Peak en memoria sigue siendo válido.

class RiskGate:
    """
    RISK-GATE-01: Control de Riesgo Pre-Trade DETERMINISTA.
    Regla de Oro: FAIL-CLOSED (Si no se puede verificar -> NO TRADE).
    """
    
    # Defaults seguros
    MAX_DAILY_DRAWDOWN_PCT = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "2.0")) # FAIL if missing env? float() raises ValueError.
    MAX_SPREAD_PCT = float(os.getenv("MAX_SPREAD_PCT", "0.5"))

    @staticmethod
    def pre_trade_check(exchange, symbol: str, supabase_client=None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verifica condiciones de riesgo antes de permitir ejecución.
        Retorna: (ok, reason, metrics)
        """
        metrics = {}
        
        try:
            # A) CHECK SPREAD (Crítico)
            # Requerimos bid/ask frescos
            ticker = exchange.fetch_ticker(symbol)
            if not ticker or 'bid' not in ticker or 'ask' not in ticker or ticker['bid'] is None or ticker['ask'] is None:
                return False, "RISK_GATE_NO_BID_ASK", metrics
            
            bid = ticker['bid']
            ask = ticker['ask']
            mid = (bid + ask) / 2
            
            if mid == 0:
                return False, "RISK_GATE_ZERO_PRICE", metrics

            spread_pct = ((ask - bid) / mid) * 100
            metrics["spread_pct"] = round(spread_pct, 4)
            metrics["max_spread_pct"] = RiskGate.MAX_SPREAD_PCT
            
            if spread_pct > RiskGate.MAX_SPREAD_PCT:
                return False, "RISK_GATE_SPREAD_EXCEEDED", metrics

            # B) CHECK DRAWDOWN (DINAMICO REAL)
            # 1. Obtener Equity Real (USDT Balance o Portfolio Value)
            # Usamos wrapper seguro fetch_balance. Si falla -> FAIL-CLOSED.
            if not hasattr(exchange, 'fetch_balance'):
                 return False, "RISK_GATE_NO_BALANCE_METHOD", metrics
                 
            bal = exchange.fetch_balance()
            if 'total' not in bal or 'USDT' not in bal['total']:
                 # Si no hay USDT wallet, buscamos equity total estimado
                 # Para MVP v6: Requerimos USDT balance explícito
                 return False, "RISK_GATE_NO_USDT_BALANCE", metrics
            
            current_equity = float(bal['total']['USDT']) # Assumes USDT base functionality
            
            # 2. Calcular Drawdown
            dd_engine = DynamicDrawdown() # Loads state
            dd_pct = dd_engine.update(current_equity)
            
            metrics["current_equity"] = current_equity
            metrics["peak_equity"] = dd_engine.peak_equity
            metrics["dd_pct"] = round(dd_pct, 4)
            metrics["max_dd_pct"] = RiskGate.MAX_DAILY_DRAWDOWN_PCT
            metrics["drawdown_blocked"] = False
            
            if dd_pct > RiskGate.MAX_DAILY_DRAWDOWN_PCT:
                 metrics["drawdown_blocked"] = True
                 return False, f"RISK_GATE_DRAWDOWN_EXCEEDED ({dd_pct:.2f}%)", metrics

            return True, "RISK_GATE_OK", metrics

        except Exception as e:
            logger.error(f"RISK GATE ERROR: {e}")
            return False, f"RISK_GATE_ERROR_{str(e)}", metrics

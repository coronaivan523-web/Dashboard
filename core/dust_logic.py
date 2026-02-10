import logging
from typing import Tuple, Optional

logger = logging.getLogger("TITAN-OMNI.DUST_LOGIC")

class DustLogic:
    """
    DUST-LOGIC-01: Lógica de Asignación de Capital.
    Evita operaciones con capital insuficiente (Dust).
    Regla: Capital < 10 USD -> CASH (No Trade).
    """

    MIN_CAPITAL_USD = 10.0

    @staticmethod
    def evaluate_capital(capital_usd: float) -> Tuple[bool, str, str]:
        """
        Evalúa si el capital es suficiente para operar.
        Retorna: (allow_trade, decision, reason)
        """
        try:
            if capital_usd is None:
                return False, "CASH", "DUST_CAPITAL_UNKNOWN"
                
            if capital_usd < DustLogic.MIN_CAPITAL_USD:
                return False, "CASH", "DUST_CAPITAL"
            
            return True, "INVESTED", "CAPITAL_OK"
            
        except Exception as e:
            logger.error(f"DUST LOGIC ERROR: {e}")
            return False, "CASH", f"DUST_ERROR_{str(e)}"

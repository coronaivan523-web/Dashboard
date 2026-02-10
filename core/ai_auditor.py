import json
import os
import logging
import random

logger = logging.getLogger("TITAN-OMNI.AUDITOR")

class AIAuditor:
    """
    Risk Officer (Auditor) v6.0.
    Punto único de aprobación de riesgo basado en IA/Lógica.
    AI-FALLBACK-01: Implementa Fallback Explícito para Resiliencia.
    """
    def __init__(self):
        # En v6.0 simplificamos para no depender de claves externas en el core básico si no estan,
        # pero asumimos que keys existen segun reglas.
        self.last_ai_path = "UNKNOWN" # PRIMARY | FALLBACK

    def audit_intent(self, ticket, regime):
        """
        Audita un ticket de ejecución propuesto.
        Retorna: (aprobado: bool, razón: str)
        """
        logger.info(f"AUDITOR: Analizando intención {ticket.action} sobre {ticket.symbol} en régimen {regime}")
        
        # 1. Intentar IA Primaria (Stub v6.0 / Futuro LLM)
        try:
            result = self._audit_with_ai(ticket, regime)
            if result:
                self.last_ai_path = "PRIMARY"
                return result
        except Exception as e:
            logger.warning(f"AUDITOR: IA Primaria falló ({e}). Activando Fallback.")
        
        # 2. Fallback Determinista (Lógica Hard-Coded v6.0)
        self.last_ai_path = "FALLBACK"
        return self._audit_deterministic(ticket, regime)

    def _audit_with_ai(self, ticket, regime):
        """
        Stub para IA Primaria (LLM).
        En v6.0 retorna None para forzar el uso de Fallback y probar el mecanismo,
        o puede simular fallo.
        """
        # Simulamos que NO hay IA configurada aún, o que falla.
        # return None triggers fallback.
        return None

    def _audit_deterministic(self, ticket, regime):
        """Lógica de reglas duras (Fail-Safe)."""
        # Reglas Duras (Hard Rules)
        if "VOLATILE" in regime and ticket.action == "BUY":
            return False, "RIESGO_VOLATILIDAD_EXTREMA"
            
        if ticket.quantity <= 0 and ticket.action != "HOLD":
            return False, "CANTIDAD_INVALIDA"
            
        return True, "AUDIT_OK"

import os
import sys
import logging
import requests
import time
from datetime import datetime, timezone

logger = logging.getLogger("TITAN-OMNI.GOVERNANCE")

class Governance:
    """
    Gobernanza central para TITAN-OMNI v6.0.
    Responsable de verificaciones pre-vuelo y bloqueos de seguridad.
    """
    @staticmethod
    def check_environment():
        """Verifica las variables de entorno críticas y el estado del sistema."""
        trading_enabled = os.getenv("TRADING_ENABLED", "false").lower() == "true"
        
        # 1. Trading Switch
        # Strict check: Must be literal string "true"
        if trading_enabled is not True:
            logger.warning(f"GOVERNANCE: TRADING_ENABLED={trading_enabled} (Expect 'true'). Modo OBSERVADOR/SAFE.")
            return False, "TRADING_DISABLED"

        # 2. Conectividad
        try:
            requests.get("https://api.kraken.com/0/public/Time", timeout=5)
        except Exception:
            logger.critical("GOVERNANCE: Sin conexi\u00f3n a Kraken API.")
            return False, "NO_CONNECTIVITY"

        return True, "OK"

    @staticmethod
    def validate_resources():
        """Verifica recursos del sistema (simulado para este entorno)."""
        # Aquí iría la lógica de memoria/CPU si fuera necesaria
        return True

import os
import json
import uuid
import logging
import time

logger = logging.getLogger("TITAN-OMNI.CAPITAL")

class CapitalManager:
    """
    Gestor de Capital Forense v6.0.
    Responsabilidad: Segregar Capital Base de Profit y mantener estado persistente.
    Regla de Oro: NO REINVERSIÓN IMPLÍCITA.
    """
    STATE_FILE = "data/capital_state.json"

    def __init__(self, current_equity: float, wal=None):
        """
        Inicializa el gestor.
        Si no existe estado, crea un nuevo ciclo con current_equity como base.
        Si existe, carga estado.
        Raises: RuntimeError si estado corrupto (Fail-Closed).
        """
        self.cycle_id = None
        self.base_capital = 0.0
        self.realized_profit = 0.0
        self.peak_equity = 0.0 # Informativo/Forense
        self.wal = wal  # Write-Ahead Log instance
        self.state = {} # Initialize an empty state dictionary

        if os.path.exists(self.STATE_FILE):
             self._load_state()
        else:
             self._init_new_cycle(current_equity)

    def _init_new_cycle(self, equity: float):
        self.state = {
            "cycle_id": str(uuid.uuid4())[:8],
            "base_capital": float(equity),
            "realized_profit": 0.0,
            "peak_equity": float(equity),
            "updated_at": time.time()
        }
        self._persist()
        logger.info(f"NUEVO CICLO DE CAPITAL INICIADO: {self.state['cycle_id']} BASE={self.state['base_capital']}")

    def _load_state(self):
        try:
            with open(self.STATE_FILE, "r") as f:
                data = json.load(f)
                self.state = {
                    "cycle_id": data["cycle_id"],
                    "base_capital": float(data["base_capital"]),
                    "realized_profit": float(data.get("realized_profit", 0.0)),
                    "peak_equity": float(data.get("peak_equity", data["base_capital"])),
                    "updated_at": data.get("updated_at", time.time())
                }
        except Exception as e:
            logger.critical(f"CAPITAL STATE CORRUPT: {e}")
            raise RuntimeError(f"CAPITAL_STATE_CORRUPT: {e}")

    def _persist(self):
        """
        Atomic persistence of capital state.
        Uses WAL if available (Async), else Sync os.replace.
        """
        if self.state.get("cycle_id"):
             # Sync internal fields to state dict before persist if needed
             # (But we seem to use self.state dict directly in new code, let's ensure compatibility)
             pass 

        if hasattr(self, 'wal') and self.wal:
            # Async Persistence
            self.wal.write(self.STATE_FILE, self.state)
        else:
            # Sync Persistence (Legacy/Fallback)
            temp_file = self.STATE_FILE + ".tmp"
            try:
                os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)
                with open(temp_file, "w") as f:
                    json.dump(self.state, f, indent=4)
                os.replace(temp_file, self.STATE_FILE)
            except Exception as e:
                logger.error(f"FAILED TO PERSIST CAPITAL STATE: {e}")

    def update(self, current_equity: float):
        """
        Actualiza métricas con equity real.
        Calcula profit realizado (Equity - Base).
        """
        current_equity = float(current_equity)
        
        # Update Peak
        if current_equity > self.state["peak_equity"]:
            self.state["peak_equity"] = current_equity
            
        # Calc Profit (puede ser negativo si hay drawdown)
        self.state["realized_profit"] = current_equity - self.state["base_capital"]
        self.state["updated_at"] = time.time()
        
        self._persist()
        return self.state["realized_profit"]

    def get_safe_capital(self) -> float:
        """
        Retorna EL ÚNICO capital que debe usarse para sizing.
        ESTRICTAMENTE el Capital Base (sin reinversión).
        """
        return self.state["base_capital"]

    def get_state_metrics(self) -> dict:
        return {
            "cycle_id": self.state["cycle_id"],
            "base_capital": self.state["base_capital"],
            "realized_profit": self.state["realized_profit"],
            "peak_equity": self.state["peak_equity"],
            "sizing_capital": self.state["base_capital"]
        }

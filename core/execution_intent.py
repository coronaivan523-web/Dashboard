from dataclasses import dataclass, asdict
import json

@dataclass
class ExecutionTicket:
    """
    Ticket de Vuelo v6.0 (Flight Ticket).
    Estructura inmutable que define la intenci\u00f3n de ejecuci\u00f3n.
    """
    ticket_id: str
    symbol: str
    action: str # BUY, SELL, HOLD
    order_type: str # MARKET, LIMIT
    quantity: float
    limit_price: float = 0.0
    reason: str = "MANUAL"
    regime: str = "UNKNOWN"
    ai_confidence: float = 0.0
    
    def to_json(self):
        return json.dumps(asdict(self))
        
    @staticmethod
    def from_json(json_str):
        data = json.loads(json_str)
        return ExecutionTicket(**data)

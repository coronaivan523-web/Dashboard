import json
import os
import logging
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

# Configuración de Logging para Forense (separado si es necesario, pero usaremos stderr/stdout seguro)
logger = logging.getLogger("TITAN-OMNI.AUDIT")

@dataclass
class AuditRecord:
    """
    Registro Forense Inmutable de Ciclo.
    Estructura JSON-serializable.
    """
    cycle_id: str
    timestamp: str
    state: str
    symbol: Optional[str]
    market_regime: Optional[str]
    execution_intent: Optional[Dict[str, Any]]
    ai_audit_result: Optional[str]
    ai_audit_reason: Optional[str]
    action: str
    order_result: Optional[Dict[str, Any]]
    decision_facts: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

def build_audit_record(
    cycle_id: str,
    state: str,
    symbol: Optional[str] = None,
    market_regime: Optional[str] = None,
    intent: Optional[Any] = None, # ExecutionTicket object
    ai_result: Optional[str] = None,
    ai_reason: Optional[str] = None,
    action: str = "SKIP",
    order_result: Optional[Dict] = None,
    facts: List[str] = [],
    errors: List[str] = []
) -> AuditRecord:
    """Construye el AuditRecord normalizando datos."""
    
    intent_dict = None
    if intent and hasattr(intent, 'to_json'):
        # Si es ExecutionTicket
        try:
            intent_dict = json.loads(intent.to_json())
        except:
            intent_dict = str(intent)
    elif intent:
        intent_dict = intent

    return AuditRecord(
        cycle_id=cycle_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        state=state,
        symbol=symbol,
        market_regime=market_regime,
        execution_intent=intent_dict,
        ai_audit_result=ai_result,
        ai_audit_reason=ai_reason,
        action=action,
        order_result=order_result,
        decision_facts=facts,
        errors=errors
    )

def write_local_audit(record: AuditRecord, base_path: str = "data/forensics"):
    """
    Escribe el registro en archivo local (Append-Only).
    Fail-Closed: Si falla, loguea a stderr y continua.
    """
    try:
        # Asegurar directorio
        os.makedirs(base_path, exist_ok=True)
        file_path = os.path.join(base_path, "audit_log.jsonl")
        
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(record.to_json() + "\n")
            
        return file_path
    except Exception as e:
        logger.error(f"FORENSIC WRITE FAILED: {e}")
        return None

def try_write_supabase(record: AuditRecord, supabase_client):
    """
    Intento Best-Effort de escritura en Supabase.
    """
    if not supabase_client:
        return

    try:
        # Asumimos que supabase_client tiene un método genérico o específico
        if hasattr(supabase_client, 'log_audit_record'):
            supabase_client.log_audit_record(asdict(record))
        else:
            logger.warning("SupabaseClient no tiene método 'log_audit_record'. Saltando.")
    except Exception as e:
        logger.error(f"SUPABASE AUDIT FAILED: {e}")

def save_ohlcv_snapshot(
    cycle_id: str,
    state: str,
    symbol: str,
    timeframe: str,
    limit: int,
    ohlcv: List[List[Any]]
) -> Dict[str, Optional[str]]:
    """
    DATA-ORIGIN-02: Persistencia local de snapshot OHLCV.
    Retorna {path, hash} o {None, None} si falla.
    """
    try:
        # 1. Sanitizar símbolo para path
        symbol_sanitized = symbol.replace("/", "_").replace("\\", "_")
        
        # 2. Construir objeto snapshot
        timestamp = datetime.now(timezone.utc).isoformat()
        snapshot_data = {
            "cycle_id": cycle_id,
            "state": state,
            "symbol": symbol,
            "timeframe": timeframe,
            "limit": limit,
            "ohlcv": ohlcv,
            "timestamp": timestamp
        }
        
        # 3. Calcular Hash (Canonical JSON)
        json_bytes = json.dumps(snapshot_data, sort_keys=True).encode('utf-8')
        snapshot_hash = hashlib.sha256(json_bytes).hexdigest()
        snapshot_data["snapshot_hash"] = snapshot_hash
        
        # 4. Definir ruta
        base_dir = "data/forensics/ohlcv"
        os.makedirs(base_dir, exist_ok=True)
        filename = f"{cycle_id}__{state}__{symbol_sanitized}__{timeframe}__{limit}.json"
        file_path = os.path.join(base_dir, filename)
        
        # 5. Escribir archivo
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2)
            
        return {"path": file_path, "hash": snapshot_hash}
        
    except Exception as e:
        logger.error(f"SNAPSHOT FAILED ({symbol}): {e}")
        return {"path": None, "hash": None}

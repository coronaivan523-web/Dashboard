import os
from supabase import create_client, Client
from datetime import datetime, timezone

class SupabaseClient:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("CRITICAL: SUPABASE CREDENTIALS MISSING")
        self.client: Client = create_client(url, key)

    def check_log_exists(self, cycle_id):
        # Fail-Closed: Si falla la red/DB, esto lanzará excepción y detendrá el bot.
        res = self.client.table("execution_logs").select("cycle_id").eq("cycle_id", cycle_id).execute()
        return len(res.data) > 0

    def log_execution(self, cycle_id, action, reason, ai_payload=None):
        data = {
            "cycle_id": cycle_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "reason": reason,
            "ai_audit_payload": ai_payload,
            "strategy_version": "v3.8"
        }
        self.client.table("execution_logs").insert(data).execute()

    def get_latest_paper_state(self):
        # Ordenar por created_at DESC para obtener el último estado real
        res = self.client.table("paper_wallet").select("*").order("created_at", desc=True).limit(1).execute()
        if res.data:
            return res.data[0]
        return None

    def update_paper_state(self, cycle_id, cash, asset_qty, entry_price):
        data = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cash_usd": float(cash),
            "asset_qty": float(asset_qty),
            "last_entry_price": float(entry_price),
            "cycle_id": cycle_id,
            "strategy_version": "v3.8"
        }
        # Append-only: Siempre insertamos historia nueva
        self.client.table("paper_wallet").insert(data).execute()

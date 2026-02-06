import os
from supabase import create_client, Client
from datetime import datetime, timezone
from config import settings

class SupabaseClient:
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
             raise ValueError("CRITICAL: SUPABASE CREDENTIALS MISSING")
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    def check_log_exists(self, cycle_id):
        # Fail-Closed
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
        res = self.client.table("paper_wallet").select("*").order("created_at", desc=True).limit(1).execute()
        if res.data:
            return (float(res.data[0]['cash_usd']), float(res.data[0]['asset_qty']), float(res.data[0]['last_entry_price']))
        return (settings.START_CAPITAL, 0.0, 0.0)

    def insert_paper_state(self, cycle_id, cash_usd, asset_qty, last_entry_price):
        data = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cash_usd": float(cash_usd),
            "asset_qty": float(asset_qty),
            "last_entry_price": float(last_entry_price),
            "cycle_id": cycle_id,
            "strategy_version": "v3.8"
        }
        self.client.table("paper_wallet").insert(data).execute()

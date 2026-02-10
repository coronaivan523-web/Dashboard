# VERSION: 4.4.2 - PESSIMISTIC FORENSICS (HOTFIX GOBERNANZA)
import os
import sys
import json
from supabase import create_client, Client
from datetime import datetime, timezone

class SupabaseClient:
    def __init__(self):
        self.mode = os.getenv("SYSTEM_MODE", "DRY_RUN").upper()
        self.client = None
        self._init_client()

    def _init_client(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        # 1. Credential Check
        if not url or not key:
            if self.mode == "DRY_RUN":
                print(f"{json.dumps({'event': 'supabase_optional_unavailable', 'mode': self.mode, 'reason': 'MISSING_CREDS'})}")
                return
            else:
                raise ValueError("CRITICAL: SUPABASE CREDENTIALS MISSING IN PROD")

        # 2. Pooler Check
        if "6543" in url or (os.getenv("DB_PORT") and "6543" in os.getenv("DB_PORT")):
             if self.mode != "DRY_RUN":
                raise Exception("CONNECTION_UNSAFE_POOLER")
             print("WARN: Unsafe pooler detected in DRY_RUN.")

        # 3. Connection Attempt (Lazy/Safe)
        try:
            # Attempt standard creation
            self.client: Client = create_client(url, key)
        except TypeError as e:
            # Specific handling for 'proxy' arg issue in some libs
            if "proxy" in str(e):
                print(f"WARN: Supabase 'proxy' arg error. Attempting raw instantiation. ({e})")
                try:
                    # Fallback: Try instantiating Client directly if create_client wraps it badly
                    # Note: create_client is usually a wrapper globally.
                    # As a last resort, we skip Supabase in DRY_RUN if this persists.
                    if self.mode == "DRY_RUN":
                         print(f"{json.dumps({'event': 'supabase_optional_unavailable', 'mode': self.mode, 'reason': 'LIB_PROXY_ERROR'})}")
                         self.client = None
                         return
                    else:
                        raise e
                except Exception as ex:
                    if self.mode != "DRY_RUN": raise ex
            else:
                 if self.mode != "DRY_RUN": raise e
                 print(f"WARN: Supabase init error: {e}")

        except Exception as e:
            if self.mode == "DRY_RUN":
                print(f"{json.dumps({'event': 'supabase_optional_unavailable', 'mode': self.mode, 'reason': str(e)})}")
                self.client = None
            else:
                raise e

    def acquire_global_lock(self):
        if not self.client: return # No-op in DRY_RUN
        try:
            res = self.client.rpc("pg_try_advisory_lock", {"key": 87364219}).execute()
            if res.data is not True:
                sys.exit(0) 
        except Exception as e:
            print(f"LOCK ERROR: {e}")
            if self.mode != "DRY_RUN": sys.exit(1)

    def release_global_lock(self):
        if not self.client: return
        try:
            self.client.rpc("pg_advisory_unlock", {"key": 87364219}).execute()
        except:
            pass

    def close(self):
        pass

    def check_log_exists(self, cycle_id):
        if not self.client: return False
        try:
            res = self.client.table("execution_logs").select("cycle_id").eq("cycle_id", cycle_id).execute()
            return len(res.data) > 0
        except: return False

    def log_execution(self, cycle_id, action, reason, ai_payload=None):
        if not self.client: return
        try:
            data = {
                "cycle_id": cycle_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "reason": reason,
                "ai_audit_payload": ai_payload,
                "strategy_version": "v4.4.2"
            }
            self.client.table("execution_logs").insert(data).execute()
        except Exception as e:
            print(f"LOG ERROR: {e}")

    # v4.4.2: Multi-Asset Filtered Portfolio
    def get_latest_portfolio_state(self, symbol):
        if not self.client:
            return 10000.0, 0.0, 0.0 # Default Paper State
            
        try:
            res = self.client.table("paper_wallet") \
                .select("cash_usd, asset_qty, last_entry_price") \
                .eq("symbol", symbol) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            
            if res.data:
                row = res.data[0]
                return float(row['cash_usd']), float(row['asset_qty']), float(row['last_entry_price'])
        except:
            pass
            
        return 10000.0, 0.0, 0.0

    def record_paper_state(self, cycle_id, cash, asset_qty, entry_price, symbol):
        if not self.client: return
        try:
            data = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "cash_usd": float(cash),
                "asset_qty": float(asset_qty),
                "last_entry_price": float(entry_price),
                "cycle_id": cycle_id,
                "symbol": symbol,
                "strategy_version": "v4.4.2"
            }
            self.client.table("paper_wallet").insert(data).execute()
        except:
            pass

    # EXEC-AUDIT-01: Persistencia Forense Best-Effort
    def log_audit_record(self, record_dict):
        if not self.client: return
        try:
            # Intentar escribir en tabla 'audit_records' si existe, o usar 'execution_logs' fallback
            # Para v6.0 estricto, usamos una tabla dedicada o un campo JSONB en logs.
            # Asumimos tabla 'audit_trail' para no ensuciar 'execution_logs' legacy.
            self.client.table("audit_trail").insert(record_dict).execute()
        except Exception as e:
            # Silent Fail (Best Effort)
            print(f"SUPABASE AUDIT REJECTED: {e}")

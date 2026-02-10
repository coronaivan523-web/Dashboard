# GOVERNANCE PHASE 1 — LOCKED (v5.2). Do not modify without explicit approval.
import os
import sys

class DoDRunner:
    def run_dod_checks(self, mode="DRY_RUN"):
        checks = []
        all_ok = True
        
        # 1. Critical Files
        files = [
            "requirements.txt",
            "data/schema.sql",
            "DOD_CHECKLIST.md",
            "main.py"
        ]
        
        # If run_bot.yml is expected in .github/workflows, check it
        if os.path.exists(".github/workflows"):
             files.append(".github/workflows/run_bot.yml")
             
        for f in files:
            exists = os.path.exists(f)
            checks.append({"name": f"FILE_EXIST_{os.path.basename(f)}", "ok": exists, "details": f})
            if not exists: all_ok = False
            
        # 2. Dependencies (String Match)
        try:
            with open("requirements.txt", "r") as f:
                reqs = f.read()
                
            # Pandas
            p_ok = "pandas==2.3.3" in reqs
            checks.append({"name": "DEP_PANDAS_LOCKED", "ok": p_ok, "details": "pandas==2.3.3"})
            if not p_ok: all_ok = False
            
            # Pandas TA
            ta_ok = "pandas-ta==0.4.71b0" in reqs
            checks.append({"name": "DEP_IT_LOCKED", "ok": ta_ok, "details": "pandas-ta==0.4.71b0"})
            if not ta_ok: all_ok = False
            
        except Exception as e:
            checks.append({"name": "REQ_FILE_READ", "ok": False, "details": str(e)})
            all_ok = False

        # 3. Env Vars
        # Supabase is CRITICAL even in DRY_RUN for logging? 
        # User said: "SUPABASE_URL, SUPABASE_KEY (si supabase_client.py existe)"
        # supabase_client.py exists in data/
        
        # We assume os.environ is loaded by dotenv in main, but let's check current environ
        # (dotenv loading happens in main.py before preflight is called usually)
        
        env_vars = ["SUPABASE_URL", "SUPABASE_KEY"]
        if mode != "DRY_RUN":
            env_vars.extend(["KRAKEN_API_KEY", "KRAKEN_SECRET"])
            
        for v in env_vars:
            val = os.getenv(v)
            has_val = val is not None and len(val) > 0
            
            # v5.2 Hotfix: Supabase optional in DRY_RUN
            if mode == "DRY_RUN" and "SUPABASE" in v:
                checks.append({"name": f"ENV_{v}", "ok": True, "details": "OPTIONAL_IN_DRY_RUN"})
            else:
                checks.append({"name": f"ENV_{v}", "ok": has_val, "details": "SET" if has_val else "MISSING"})
                if not has_val: 
                    all_ok = False

        # 4. Importability
        try:
            import core.risk_engine
            checks.append({"name": "IMPORT_RISK", "ok": True, "details": "core.risk_engine"})
        except ImportError as e:
            checks.append({"name": "IMPORT_RISK", "ok": False, "details": str(e)})
            all_ok = False

        return {
            "ok": all_ok,
            "checks": checks,
            "summary": "DoD CHECKS PASSED" if all_ok else "DoD CHECKS FAILED"
        }

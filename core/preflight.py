# GOVERNANCE PHASE 1 — LOCKED (v5.2). Do not modify without explicit approval.
from core.dod_runner import DoDRunner
from core.governance_lock import verify_governance_phase1_lock
from core.governance import Governance

def preflight(mode="DRY_RUN"):
    """
    Executes Sanity + DoD checks + Governance Lock Check.
    Returns: (bool ok, str reason, dict report)
    FAIL-CLOSED: If any check fails, returns False immediately.
    """
    
    # 0. Governance Environment Check (Connectivity / Trading Switch)
    gov_ok, gov_reason = Governance.check_environment()
    if not gov_ok:
        return False, f"GOV_ENV_FAIL: {gov_reason}", {}

    # 1. Governance Lock Check (File Integrity)
    lock_res = verify_governance_phase1_lock()
    if not lock_res["ok"]:
         return False, "LOCK_VIOLATION: Critical files missing or altered.", lock_res
    
    # 2. Sanity (Quick Imports)
    try:
        import pandas as pd
        import ccxt
    except ImportError as e:
        return False, f"SANITY_IMPORT_FAIL: {e}", {}

    # 3. DoD Checks
    runner = DoDRunner()
    dod_results = runner.run_dod_checks(mode=mode)
    
    if not dod_results["ok"]:
        return False, "DOD_VIOLATION: Definition of Done failed.", dod_results

    # 4. Success
    return True, "OK", {"lock": lock_res, "dod": dod_results}

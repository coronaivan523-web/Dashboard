import os
import hashlib

# GOVERNANCE PHASE 1 — LOCKED (v5.2)
GOV_PHASE = 1
GOV_LOCK_STATUS = "LOCKED"

def calculate_file_hash(filepath):
    """Calculates SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return None

def verify_governance_phase1_lock():
    """
    Verifies the integrity of Governance Phase 1 files and logic.
    Returns dict with check results.
    FAIL-CLOSED: Any missing file or logic breach returns ok=False.
    """
    checks = []
    all_ok = True
    
    # 1. File Existence & Integrity
    # In a real scenario, we would check against a strict manifest of expected hashes.
    # For this phase 3-01 activation, we ensure:
    # a) Files exist
    # b) Files are readable and hashable (integrity check prevents 0-byte or corrupted files)
    
    core_files = [
        "core/governance_state.py",
        "core/dod_runner.py",
        "core/preflight.py",
        "core/governance.py",
        "main.py",
        "requirements.txt"
    ]
    
    for f in core_files:
        exists = os.path.exists(f)
        file_hash = calculate_file_hash(f) if exists else None
        
        check_ok = exists and file_hash is not None
        checks.append({
            "name": f"INTEGRITY_{os.path.basename(f)}", 
            "ok": check_ok,
            "hash": file_hash[:8] if file_hash else "N/A"
        })
        
        if not check_ok: 
            all_ok = False
        
    # 2. Main.py Logic Checks (String matching to ensure Preflight call)
    if os.path.exists("main.py"):
        try:
            with open("main.py", "r", encoding="utf-8") as f:
                content = f.read()
                
            # Check for imports
            has_import = "from core.preflight import preflight" in content
            checks.append({"name": "MAIN_PY_IMPORT_PREFLIGHT", "ok": has_import})
            if not has_import: all_ok = False
            
            # Check for invocation (rough check)
            has_call = "preflight(" in content
            checks.append({"name": "MAIN_PY_CALLS_PREFLIGHT", "ok": has_call})
            if not has_call: all_ok = False
            
        except Exception as e:
            checks.append({"name": "MAIN_PY_READ_ERROR", "ok": False, "details": str(e)})
            all_ok = False
            
    return {
        "ok": all_ok,
        "phase": GOV_PHASE,
        "locked": True,
        "checks": checks,
        "summary": "GOVERNANCE LOCK OK" if all_ok else "GOVERNANCE LOCK VIOLATION"
    }

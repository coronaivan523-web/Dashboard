import sys
import os
import shutil

# Agregamos path actual para imports
sys.path.append(os.getcwd())

from core.preflight import preflight
from core.governance_lock import verify_governance_phase1_lock

def test_governance_activation():
    results = []
    
    # MOCK ENVIRONMENT FOR TESTING
    os.environ["TRADING_ENABLED"] = "true"
    
    print("--- TEST 1: NORMAL RUN (EXPECT PASS) ---")
    try:
        ok, reason, report = preflight()
        res = "PASS" if ok else "FAIL"
        print(f"Result: {res}, Reason: {reason}")
        results.append({"case": "Normal Run", "result": res, "reason": reason})
    except Exception as e:
        print(f"EXCEPTION: {e}")
        results.append({"case": "Normal Run", "result": "EXCEPTION", "reason": str(e)})

    print("\n--- TEST 2: CRITICAL FILE MODIFIED (EXPECT FAIL) ---")
    # Rename main.py temporarily to simulate missing/tampered file
    if os.path.exists("main.py"):
        shutil.move("main.py", "main.py.bak")
        try:
            ok, reason, report = preflight()
            res = "PASS" if ok else "FAIL" # Should FAIL due to missing file/bad lock
            # EXPECTED: FAIL because verify_governance_phase1_lock checks for main.py existence
            print(f"Result: {res}, Reason: {reason}")
            results.append({"case": "File Tamper (Missing main.py)", "result": res, "reason": reason})
        except Exception as e:
             print(f"EXCEPTION: {e}")
             results.append({"case": "File Tamper", "result": "EXCEPTION", "reason": str(e)})
        finally:
            # Restore
            if os.path.exists("main.py.bak"):
                shutil.move("main.py.bak", "main.py")
    
    print("\n--- TEST 3: ENV VAR MISSING (EXPECT FAIL) ---")
    del os.environ["TRADING_ENABLED"]
    
    try:
        # Should fail check_environment inside preflight
        ok, reason, report = preflight()
        res = "PASS" if ok else "FAIL"
        print(f"Result: {res}, Reason: {reason}")
        results.append({"case": "Env Missing (TRADING_ENABLED)", "result": res, "reason": reason})
    except Exception as e:
         results.append({"case": "Env Missing", "result": "EXCEPTION", "reason": str(e)})
    finally:
        os.environ["TRADING_ENABLED"] = "true" # Restore for any subsequent logic

    return results

if __name__ == "__main__":
    test_results = test_governance_activation()
    print("\n=== SUMMARY ===")
    for r in test_results:
        print(r)

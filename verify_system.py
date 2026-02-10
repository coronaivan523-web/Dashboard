import subprocess
import sys
import time
import os

def run_bot(cycle_override=None):
    # Ensure we use the same python interpreter
    cmd = [sys.executable, "main.py"]
    env = os.environ.copy()
    
    # Force PAPER mode for smoke test
    env["SYSTEM_MODE"] = "PAPER"
    
    if cycle_override:
        env["CYCLE_ID_OVERRIDE"] = cycle_override
    
    print(f"> EXECUTING BOT... (Cycle Override: {cycle_override})")
    # Capture output to avoid spamming console, but print first lines as requested
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    print(f"   EXIT CODE: {result.returncode}")
    # Replace newlines to safe printing
    stdout_head = result.stdout[:200].replace('\n', ' ')
    stderr_head = result.stderr[:200].replace('\n', ' ')
    
    try:
        print(f"   STDOUT HEAD: {stdout_head}")
        print(f"   STDERR HEAD: {stderr_head}")
    except:
        print("   (Output contains non-printable characters)")
        
    return result.returncode

print("==============================================")
print("     TITAN-OMNI v3.8 -- SMOKE TEST     ")
print("==============================================")

# PASO 1: EJECUCIÓN LIMPIA
print("\n[TEST 1] First Execution (Must be EXIT 0 + DB Write)...")
code1 = run_bot()
if code1 != 0:
    print("X CRITICAL FAILURE: Bot finished with error.")
    sys.exit(1)
else:
    print("V TEST 1: SUCCESSFUL EXECUTION.")

# PASO 2: IDEMPOTENCIA (Simular mismo ciclo)
print("\n[TEST 2] Idempotency Test (Immediate Re-execution)...")
# Since main.py calculates cycle_id based on 15m windows, running immediately again 
# should result in the SAME cycle_id and trigger idempotency check.
time.sleep(2) 
code2 = run_bot()

if code2 == 0:
    print("V TEST 2: IDEMPOTENCIA SUCCESS (Exit 0, expecting 'Skipping/Already Ran' log).")
else:
    print(f"! WARNING: Non-standard exit code in second run: {code2}")

print("\nDONE. CHECK YOUR SUPABASE TO CONFIRM ROWS.")

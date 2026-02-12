import os
import uuid
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from . import db

app = FastAPI(docs_url=None, redoc_url=None)

FORBIDDEN_KEYWORDS = ["trade", "order", "execute", "kraken", "ccxt"]
REQUIRED_TABLES = ["investment_cycles", "cycle_events", "governance_requests"]

class CycleStartRequest(BaseModel):
    base_capital: float
    notes: Optional[str] = None

    @validator('base_capital')
    def capital_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('base_capital must be > 0')
        return v

@app.get("/healthz")
def health_check(request: Request):
    # Route Analysis
    routes = [route.path for route in app.routes]
    routes_count = len(routes)
    
    policy_violation = False
    for r in routes:
        for kw in FORBIDDEN_KEYWORDS:
            if kw in r:
                policy_violation = True
                break
    
    # DB Check
    db_ok = db.db_ping()
    
    # Table Check
    tables_status = {}
    if db_ok:
        for t in REQUIRED_TABLES:
            tables_status[t] = db.table_exists(t)
    else:
        for t in REQUIRED_TABLES:
            tables_status[t] = False

    # Status Determination
    status_val = "ok"
    if not db_ok or policy_violation:
        status_val = "degraded"
        
    response_data = {
        "status": status_val,
        "db": "ok" if db_ok else "down",
        "tables": tables_status,
        "routes_count": routes_count,
        "routes": routes
    }
    
    if policy_violation:
        response_data["policy_violation"] = True

    return JSONResponse(content=response_data, status_code=200)

@app.post("/cycles/start", status_code=201)
def start_cycle(payload: CycleStartRequest):
    # FAIL-CLOSED: Check DB connectivity
    if not db.db_ping():
         return JSONResponse(status_code=503, content={"error": "db_down"})

    conn = db.get_conn()
    if not conn:
         return JSONResponse(status_code=503, content={"error": "db_down"})

    try:
        with conn:
            with conn.cursor() as cur:
                # 1. Insert Cycle
                cur.execute("""
                    INSERT INTO investment_cycles (status, base_capital, current_capital, notes)
                    VALUES ('ACTIVE', %s, %s, %s)
                    RETURNING cycle_id, status, base_capital, current_capital, started_at, created_at
                """, (payload.base_capital, payload.base_capital, payload.notes))
                cycle = cur.fetchone()
                
                if not cycle:
                    raise Exception("Failed to create cycle")
                
                cycle_data = {
                    "cycle_id": cycle[0],
                    "status": cycle[1],
                    "base_capital": float(cycle[2]),
                    "current_capital": float(cycle[3]),
                    "started_at": str(cycle[4]) if cycle[4] else None,
                    "created_at": str(cycle[5])
                }

                # 2. Insert START Event
                event_payload = str(payload.json()) # Store as JSON string
                cur.execute("""
                    INSERT INTO cycle_events (cycle_id, event_type, payload, actor)
                    VALUES (%s, 'START', %s::jsonb, 'api')
                """, (cycle_data["cycle_id"], event_payload))
                
        # Transaction commits automatically on exit of `with conn`
        return cycle_data

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "internal_error", "details": str(e)}) # Avoid leaking internal details in prod, kept for debugging this step
    finally:
        conn.close()

@app.get("/cycles")
def list_cycles():
    if not db.db_ping():
        return JSONResponse(status_code=503, content={"error": "db_down"})
    
    rows = db.execute_query("""
        SELECT cycle_id, status, base_capital, current_capital, created_at 
        FROM investment_cycles 
        ORDER BY created_at DESC 
        LIMIT 50
    """, fetch_all=True)
    
    if rows is None: # DB error signal from execute_query
        return JSONResponse(status_code=503, content={"error": "db_down"})

    cycles = []
    for r in rows:
        cycles.append({
            "cycle_id": r[0],
            "status": r[1],
            "base_capital": float(r[2]),
            "current_capital": float(r[3]),
            "created_at": str(r[4])
        })
    return cycles

@app.get("/cycles/{cycle_id}")
def get_cycle(cycle_id: str):
    try:
        uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    if not db.db_ping():
        return JSONResponse(status_code=503, content={"error": "db_down"})

    row = db.execute_query("""
        SELECT cycle_id, status, base_capital, current_capital, realized_pnl, withdrawn_profit, created_at, started_at, finished_at, notes
        FROM investment_cycles
        WHERE cycle_id = %s
    """, (cycle_id,), fetch_one=True)

    if row is None: # Could be DB error or Not Found, execute_query semantics need refinement for 404 vs 503 distinction.
                    # Given current execute_query impl returns None on error.
                    # Let's double check if it was DB error or empty result.
                    # Re-implementation of execute_query needed to distinguish? 
                    # Actually, execute_query returns None on connection failure. 
                    # If query runs but no rows, fetchone returns None. 
                    # Ambiguity here. 
                    # Quick fix: Check db_ping() first (already done). If db_ping is true, execute_query None means 0 rows.
       pass # Logic handled below

    # To strictly distinguish, let's look at row. 
    # If execute_query failed (conn error), it returns None (or False? No, return None). 
    # If fetchone returned None (no rows), it returns None.
    # We checked db_ping() so we assume connection is OK.
    
    if row is None:
        raise HTTPException(status_code=404, detail="Cycle not found")

    return {
        "cycle_id": row[0],
        "status": row[1],
        "base_capital": float(row[2]),
        "current_capital": float(row[3]),
        "realized_pnl": float(row[4]),
        "withdrawn_profit": float(row[5]),
        "created_at": str(row[6]),
        "started_at": str(row[7]) if row[7] else None,
        "finished_at": str(row[8]) if row[8] else None,
        "notes": row[9]
    }

@app.get("/cycles/{cycle_id}/events")
def get_cycle_events(cycle_id: str):
    try:
        uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    if not db.db_ping():
        return JSONResponse(status_code=503, content={"error": "db_down"})

    # Check cycle existence first
    cycle_exists = db.execute_query("SELECT 1 FROM investment_cycles WHERE cycle_id = %s", (cycle_id,), fetch_one=True)
    if not cycle_exists:
         raise HTTPException(status_code=404, detail="Cycle not found")

    rows = db.execute_query("""
        SELECT id, ts, event_type, payload, actor
        FROM cycle_events
        WHERE cycle_id = %s
        ORDER BY ts ASC
    """, (cycle_id,), fetch_all=True)
    
    if rows is None: # Should not happen if db_ping passed and cycle exists
        return []

    events = []
    for r in rows:
        events.append({
            "id": r[0],
            "ts": str(r[1]),
            "event_type": r[2],
            # payload is already a dict/json from psycopg2 with jsonb
            "payload": r[3], 
            "actor": r[4]
        })
    return events


@app.post("/cycles/{cycle_id}/finish")
def finish_cycle(cycle_id: str):
    try:
        uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    if not db.db_ping():
        return JSONResponse(status_code=503, content={"error": "db_down"})

    conn = db.get_conn()
    if not conn:
         return JSONResponse(status_code=503, content={"error": "db_down"})

    try:
        with conn:
            with conn.cursor() as cur:
                # 1. Lock and Get Current Status
                # Use FOR UPDATE to prevent race conditions
                cur.execute("SELECT status FROM investment_cycles WHERE cycle_id = %s FOR UPDATE", (cycle_id,))
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="Cycle not found")
                
                current_status = row[0]
                
                # 2. Validate Transition (ACTIVE -> FINISHING)
                if current_status != 'ACTIVE':
                    raise HTTPException(status_code=400, detail=f"Invalid transition from {current_status} to FINISHING")
                
                # 3. Update Status
                cur.execute("UPDATE investment_cycles SET status = 'FINISHING' WHERE cycle_id = %s", (cycle_id,))
                
                # 4. Log Event
                cur.execute("""
                    INSERT INTO cycle_events (cycle_id, event_type, payload, actor)
                    VALUES (%s, 'FINISH_REQUEST', '{"previous_status": "ACTIVE"}'::jsonb, 'api')
                """, (cycle_id,))
                
        return {"cycle_id": cycle_id, "status": "FINISHING"}

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "internal_error", "details": str(e)})
    finally:
        conn.close()

@app.post("/cycles/{cycle_id}/emergency-stop")
def emergency_stop_cycle(cycle_id: str):
    try:
        uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    if not db.db_ping():
        return JSONResponse(status_code=503, content={"error": "db_down"})

    conn = db.get_conn()
    if not conn:
         return JSONResponse(status_code=503, content={"error": "db_down"})

    try:
        with conn:
            with conn.cursor() as cur:
                # 1. Lock and Get Current Status
                cur.execute("SELECT status FROM investment_cycles WHERE cycle_id = %s FOR UPDATE", (cycle_id,))
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="Cycle not found")
                
                current_status = row[0]
                
                # 2. Validate Transition (ACTIVE/FINISHING -> STOP)
                if current_status == 'STOP':
                    return {"cycle_id": cycle_id, "status": "STOP"}
                
                if current_status not in ('ACTIVE', 'FINISHING'):
                     raise HTTPException(status_code=400, detail=f"Invalid transition from {current_status} to STOP")

                # 3. Update Status
                cur.execute("UPDATE investment_cycles SET status = 'STOP' WHERE cycle_id = %s", (cycle_id,))
                
                # 4. Log Event
                payload = f'{{"previous_status": "{current_status}"}}'
                cur.execute("""
                    INSERT INTO cycle_events (cycle_id, event_type, payload, actor) 
                    VALUES (%s, 'EMERGENCY_STOP', %s::jsonb, 'api')
                """, (cycle_id, payload))
                
        return {"cycle_id": cycle_id, "status": "STOP"}

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "internal_error", "details": str(e)})
    finally:
        conn.close()

class GovernanceRequest(BaseModel):
    request_type: str
    cycle_id: Optional[str] = None
    reason: Optional[str] = None

    @validator('request_type')
    def validate_type(cls, v):
        if v not in ('START_CYCLE', 'FINISH_CYCLE', 'EMERGENCY_STOP'):
             raise ValueError('Invalid request_type')
        return v

@app.post("/requests", status_code=201)
def create_governance_request(payload: GovernanceRequest):
    if payload.cycle_id:
        try:
            uuid.UUID(payload.cycle_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

    if not db.db_ping():
        return JSONResponse(status_code=503, content={"error": "db_down"})

    conn = db.get_conn()
    if not conn:
         return JSONResponse(status_code=503, content={"error": "db_down"})

    try:
        with conn:
            with conn.cursor() as cur:
                # 1. Insert Request
                cur.execute("""
                    INSERT INTO governance_requests (request_type, cycle_id, reason, status)
                    VALUES (%s, %s, %s, 'PENDING')
                    RETURNING id, status
                """, (payload.request_type, payload.cycle_id, payload.reason))
                req = cur.fetchone()
                
                if not req:
                     raise Exception("Failed to create request")

                # 2. Log Event
                # We handle potential NULL cycle_id gracefully for event log if schema permits or if we just log generic system event (not attached to cycle).
                # The prompt asks: "INSERT event... payload includes request_type and reason".
                # If cycle_id is null, inserting into cycle_events(cycle_id) might fail if constraint exists on NOT NULL.
                # Schema check: "cycle_id uuid references investment_cycles(cycle_id)". It does NOT explicitly say NOT NULL.
                # So we try.
                
                event_payload = payload.json()
                cur.execute("""
                    INSERT INTO cycle_events (cycle_id, event_type, payload, actor)
                    VALUES (%s, 'GOVERNANCE_REQUEST', %s::jsonb, 'api')
                """, (payload.cycle_id, event_payload))
                
        return {"request_id": req[0], "status": req[1]}

    except Exception as e:
        # If constraint violation (e.g. cycle_events.cycle_id NOT NULL), return error.
        # But we want to fail closed.
        return JSONResponse(status_code=500, content={"error": "internal_error", "details": str(e)})
    finally:
        conn.close()

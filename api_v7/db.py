import os
import psycopg2
from typing import Optional

def get_conn():
    """Establishes connection to Postgres using DATABASE_URL."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return None
    try:
        conn = psycopg2.connect(dsn)
        return conn
    except Exception:
        return None

def db_ping() -> bool:
    """Checks if database is reachable."""
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            return True
    except Exception:
        return False
    finally:
        if conn:
            conn.close()

def table_exists(table_name: str) -> bool:
    """Checks if a specific table exists in the public schema."""
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            # Safe parameterized query
            cur.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table_name}",))
            result = cur.fetchone()
            return result[0] if result else False
    except Exception:
        return False
    finally:
        if conn:
            conn.close()

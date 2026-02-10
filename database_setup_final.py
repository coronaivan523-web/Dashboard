import sqlite3
import os
import logging

# Configuración
DB_NAME = "titan_brain.db"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TITAN-DB-SETUP")

def create_tables():
    if os.path.exists(DB_NAME):
        logger.warning(f"La base de datos '{DB_NAME}' ya existe. Se verificarán las tablas.")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. TABLA DE CICLOS (Governance & State)
    # Registra cada ejecución del bot ("Run Cycle").
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cycles (
        cycle_id TEXT PRIMARY KEY,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        status TEXT CHECK(status IN ('HUNTING', 'MANAGING', 'COMPLETED', 'ABORTED', 'CRASHED')),
        mode TEXT DEFAULT 'LIVE',
        meta_json TEXT -- Datos extra (versión, ip, etc)
    )
    ''')

    # 2. TABLA DE CAPITAL (Capital Silos)
    # Mantiene el estado del capital segregado por ciclo.
    # Invariante: base_capital es INMUTABLE por ciclo.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS capital_state (
        cycle_id TEXT PRIMARY KEY,
        base_capital REAL NOT NULL,
        realized_profit REAL DEFAULT 0.0,
        unrealized_profit REAL DEFAULT 0.0,
        peak_equity REAL,
        drawdown_pct REAL DEFAULT 0.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(cycle_id) REFERENCES cycles(cycle_id)
    )
    ''')

    # 3. TABLA DE TRADES (Execution Ledger)
    # Registro inmutable de operaciones.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        trade_id TEXT PRIMARY KEY,
        cycle_id TEXT,
        symbol TEXT NOT NULL,
        side TEXT CHECK(side IN ('BUY', 'SELL')),
        entry_price REAL,
        exit_price REAL,
        quantity REAL,
        pnl_realized REAL,
        status TEXT CHECK(status IN ('OPEN', 'CLOSED', 'CANCELLED', 'REJECTED')),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(cycle_id) REFERENCES cycles(cycle_id)
    )
    ''')

    # 4. TABLA DE GOBERNANZA (Locks & Signals)
    # Control maestro del sistema.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS governance (
        key TEXT PRIMARY KEY,
        value TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Inicializar Valores de Gobernanza por Defecto
    cursor.execute("INSERT OR IGNORE INTO governance (key, value) VALUES ('SYSTEM_LOCK', 'UNLOCKED')")
    cursor.execute("INSERT OR IGNORE INTO governance (key, value) VALUES ('TRADING_MODE', 'PAPER')")
    cursor.execute("INSERT OR IGNORE INTO governance (key, value) VALUES ('MIN_CAPITAL_THRESHOLD', '10.0')")

    conn.commit()
    conn.close()
    logger.info("Base de datos blindada v7.2 inicializada correctamente.")

if __name__ == "__main__":
    create_tables()

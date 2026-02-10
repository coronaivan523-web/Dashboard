import streamlit as st
import pandas as pd
import sqlite3
import os
import time
import json

# Configuración de Página
st.set_page_config(
    page_title="TITAN-OMNI Governance Dashboard v7.0",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes
DB_NAME = "titan_brain.db"

# Funciones de Acceso a Datos
def get_governance_status():
    if not os.path.exists(DB_NAME): return {}
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT key, value FROM governance", conn)
    conn.close()
    return dict(zip(df.key, df.value))

def get_recent_cycles(limit=10):
    if not os.path.exists(DB_NAME): return pd.DataFrame()
    conn = sqlite3.connect(DB_NAME)
    query = """
    SELECT c.cycle_id, c.start_time, c.status, cap.base_capital, cap.realized_profit 
    FROM cycles c 
    LEFT JOIN capital_state cap ON c.cycle_id = cap.cycle_id
    ORDER BY c.start_time DESC LIMIT ?
    """
    df = pd.read_sql(query, conn, params=(limit,))
    conn.close()
    return df

def get_performance_metrics():
    if not os.path.exists(DB_NAME): return 0, 0
    conn = sqlite3.connect(DB_NAME)
    # Total Profit
    profit = pd.read_sql("SELECT SUM(realized_profit) as total FROM capital_state", conn).iloc[0]['total']
    # Active Trades
    active = pd.read_sql("SELECT COUNT(*) as count FROM trades WHERE status='OPEN'", conn).iloc[0]['count']
    conn.close()
    return profit or 0.0, active or 0

# Sidebar - Control de Gobernanza
st.sidebar.title("🛡️ Governance Sentinel")
st.sidebar.markdown("---")
gov_status = get_governance_status()

system_lock = gov_status.get("SYSTEM_LOCK", "UNKNOWN")
trading_mode = gov_status.get("TRADING_MODE", "UNKNOWN")

st.sidebar.metric("System Lock", system_lock)
st.sidebar.metric("Execution Mode", trading_mode)

if st.sidebar.button("🔄 Refresh State"):
    st.rerun()

st.sidebar.markdown("### 🚨 Emergency Controls")
st.sidebar.warning("Physical access required to change locks.")

# Main Dashboard
st.title("TITAN-OMNI v7.0 Command Center")
st.markdown("### *Forensic Runtime Oversight & Capital Silos*")

# Top Metrics Row
col1, col2, col3, col4 = st.columns(4)
profit, active_trades = get_performance_metrics()

with col1:
    st.metric("Net Realized Profit (USDT)", f"${profit:,.2f}", delta_color="normal")
with col2:
    st.metric("Active Silos (Cycles)", "N/A") # Placeholder
with col3:
    st.metric("Active Trades", active_trades)
with col4:
    st.metric("System Health", "NOMINAL", delta="OK")

# Live Cycle Feed
st.markdown("### 🧬 Live Cycle Feed")
cycles_df = get_recent_cycles()
if not cycles_df.empty:
    st.dataframe(cycles_df, use_container_width=True)
else:
    st.info("No cycle data available yet. Waiting for bot execution...")

# Audit Evidence Viewer
st.markdown("### 🕵️ Forensic Evidence Viewer")
logs_dir = "data/forensics"
if os.path.exists(logs_dir):
    log_files = [f for f in os.listdir(logs_dir) if f.endswith(".jsonl")]
    selected_log = st.selectbox("Select Audit Log", log_files)
    if selected_log:
        with open(os.path.join(logs_dir, selected_log), "r") as f:
            lines = f.readlines()[-50:] # Last 50 lines
            st.code("".join(lines), language="json")
else:
    st.warning("Audit directory not found.")

# Wallet / Capital State
st.markdown("### 💰 Capital State (Silos)")
# Placeholder for visual breakdown of capital silos
st.info("Capital Silo visualization requires active runtime data.")

st.markdown("---")
st.caption(f"Server Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

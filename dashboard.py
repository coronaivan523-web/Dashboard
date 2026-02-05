import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import time

# --- 1. CONFIGURACIÓN DE PÁGINA (MODO CINE) ---
st.set_page_config(
    page_title="ANTIGRAVITY PRIME",
    layout="wide",
    page_icon="🦅",
    initial_sidebar_state="expanded"
)

# --- 2. ESTILO VISUAL "BLACK OBSIDIAN" (CSS HACK) ---
st.markdown("""
<style>
    /* Fondo General */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Tarjetas de Métricas (Glassmorphism) */
    div[data-testid="stMetric"] {
        background-color: #1c1f26;
        border: 1px solid #2d333b;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* Textos y Títulos */
    h1, h2, h3 {
        color: #e6e6e6;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 300;
    }
    
    /* Botones Personalizados */
    .stButton>button {
        background-color: #00D100;
        color: black;
        border-radius: 5px;
        font-weight: bold;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES DE DUMMY DATA (Para visualizar el diseño antes de conectar Binance) ---
def get_fake_market_data():
    # Simulamos datos de velas para ver el diseño
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    prices = np.random.normal(50000, 500, 100).cumsum()
    prices = prices + 50000 # Base BTC price
    
    df = pd.DataFrame({
        'Date': dates,
        'Open': prices,
        'High': prices + 50,
        'Low': prices - 50,
        'Close': prices + np.random.normal(0, 20, 100)
    })
    return df

# --- 4. LAYOUT PRINCIPAL ---

# Título y Estado
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("🦅 ANTIGRAVITY // COMMAND CENTER")
    st.caption("AI-POWERED ALGORITHMIC TRADING SYSTEM V4.0")
with col_head2:
    st.success("🟢 SISTEMA: ONLINE")
    st.info("📡 BINANCE: 14ms LATENCY")

st.markdown("---")

# Métricas Clave (Top KPI)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(label="💰 CAPITAL TOTAL (USDT)", value="$10,450.20", delta="+2.4%")
kpi2.metric(label="📊 PnL (24h)", value="+$245.00", delta="High Perf.")
kpi3.metric(label="🤖 IA TOKENS", value="450/1000", delta="Normal", delta_color="off")
kpi4.metric(label="⚡ ESTADO", value="ESPERANDO SEÑAL", delta="Standby", delta_color="off")

# --- 5. ZONA DE GRÁFICOS Y CEREBRO ---
col_chart, col_brain = st.columns([3, 1])

with col_chart:
    st.subheader("📈 MERCADO EN TIEMPO REAL (BTC/USDT)")
    
    # Generar gráfico profesional
    df = get_fake_market_data()
    fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'],
                increasing_line_color= '#00ff00', decreasing_line_color= '#ff0000')])

    fig.update_layout(
        height=500,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='#0e1117',
        plot_bgcolor='#0e1117',
        font=dict(color='white'),
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

with col_brain:
    st.subheader("🧠 CEREBRO IA (Gemini)")
    with st.container(border=True):
        st.markdown("**Último Análisis:**")
        st.info("El mercado muestra una divergencia alcista. Recomiendo esperar confirmación de ruptura en $50,200.")
        
        st.markdown("---")
        st.markdown("**Control Manual:**")
        if st.button("ANALIZAR AHORA 🔍"):
            st.write("Conectando con Gemini...")
            # Aquí conectaremos la función real más tarde
            time.sleep(1)
            st.write("✅ Análisis completado.")

# --- 6. LOGS DEL SISTEMA ---
with st.expander("📜 REGISTRO DE OPERACIONES (SYSTEM LOGS)", expanded=True):
    st.code("""
    SYNC: Reloj sincronizado con servidor Binance (+2000ms offset aplicado).
    CORE: Llaves API cargadas desde .env (Seguro).
    NET: IP 187.249.120.34 Autorizada.
    """, language="bash")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CONFIGURACIÓN")
    st.checkbox("Trading Automático", value=False)
    st.checkbox("Modo Scalping (Riesgo Alto)", value=False)
    st.slider("Stop Loss (%)", 0.5, 5.0, 1.5)
    st.markdown("---")
    st.warning("⚠️ ZONA DE PELIGRO")
    st.button("🔴 APAGADO DE EMERGENCIA")

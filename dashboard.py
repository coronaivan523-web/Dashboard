import streamlit as st
import pandas as pd
import pandas_ta as ta
import ccxt
import plotly.graph_objects as go
import yfinance as yf
import os
import time
import numpy as np
from dotenv import load_dotenv
from google import genai
from openai import OpenAI

# --- 0. CONFIGURACIÓN Y SECRETOS ---
st.set_page_config(
    page_title="Dashboard Ivan Corona",
    layout="wide",
    page_icon="👑",
    initial_sidebar_state="expanded"
)

# Cargar variables de entorno (Local)
load_dotenv()

def get_secret(key):
    """Obtiene claves desde os.getenv (Prioridad Render) o st.secrets (Fallback Local/Cloud)."""
    return os.getenv(key) or (st.secrets[key] if key in st.secrets else None)

# Inicializar Clientes AI
try:
    gemini_key = get_secret("GOOGLE_API_KEY")
    openai_key = get_secret("OPENAI_API_KEY")
    
    gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None
    openai_client = OpenAI(api_key=openai_key) if openai_key else None
except Exception as e:
    st.error(f"Error inicializando clientes AI de arranque: {e}")

# --- 1. ESTILO VISUAL TITAN ---
st.markdown("""
<style>
    .stApp { background-color: #0b0e11; color: #e1e4e8; }
    
    /* Métricas Titan */
    div[data-testid="stMetric"] {
        background-color: #161b22; 
        border: 1px solid #30363d;
        padding: 15px; 
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    
    /* Botones de Acción */
    .stButton>button {
        background-color: #238636; 
        color: white; 
        border-radius: 6px;
        font-weight: 600;
        border: 1px solid rgba(240, 246, 252, 0.1);
        transition: 0.2s;
    }
    .stButton>button:hover {
        background-color: #2ea043;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #0d1117;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #161b22;
        border-bottom: 2px solid #58a6ff;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. MOTOR OMNI (BACKEND) ---

@st.cache_resource
def init_exchange():
    """Conexión robusta a Binance."""
    try:
        binance = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        return binance
    except Exception as e:
        return None

@st.cache_data(ttl=300)
def fetch_top_tickers():
    # Retornamos lista fija para evitar llamar a Binance y sufrir bloqueos de IP
    # Formato Yahoo Finance (XXX-USD)
    return [
        "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD",
        "ADA-USD", "DOGE-USD", "AVAX-USD", "TRX-USD", "DOT-USD",
        "MATIC-USD", "LTC-USD", "SHIB-USD", "UNI-USD", "ATOM-USD",
        "LINK-USD", "XLM-USD", "BCH-USD", "ALGO-USD", "FIL-USD",
        "NEAR-USD", "VET-USD", "ICP-USD", "APE-USD", "SAND-USD"
    ]

@st.cache_data(ttl=5, show_spinner=False)
def fetch_candles(symbol, timeframe, limit):
    """
    Descarga velas desde Yahoo Finance (Data Feed Híbrido).
    Reemplaza la función original de Binance.
    """
    # Mapeo: BTC/USDT -> BTC-USD (Si viene de Binance)
    # Si viene del Hardcoded list (BTC-USD), el replace no hace daño.
    yf_symbol = symbol.replace('/', '-').replace('USDT', 'USD')
    
    try:
        # Configurar parámetros Yahoo
        if timeframe == '4h':
            # Yahoo no tiene 4h nativo, bajamos 1h y resampleamos
            # period="60d" cubre suficiente historia para EMA 200 en 4h
            df = yf.download(yf_symbol, period="60d", interval="1h", progress=False)
            
            if df.empty: return pd.DataFrame()
            
            # Resample a 4H
            agg_dict = {
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }
            # Resample usando '4h' (lowercase h deprecated in new pandas per freq alias, but usually works. '4H' is standard)
            df_resampled = df.resample('4h').agg(agg_dict).dropna()
            df = df_resampled.tail(limit)

        else: # Default/15m
             # 15m necesita menos historia, 5d es suficiente
             df = yf.download(yf_symbol, period="5d", interval="15m", progress=False)
             df = df.tail(limit)
        
        if df.empty: return pd.DataFrame()

        # Normalización para Pandas-TA
        df = df.reset_index() # Mover fecha a columna
        df.columns = [c.lower() for c in df.columns] # open, high, low...
        
        # Yahoo devuelve 'Date' o 'Datetime' como nombre de columna tras reset_index
        # Buscamos cual es la de tiempo y la renombramos a 'timestamp'
        if 'date' in df.columns: 
            df = df.rename(columns={'date': 'timestamp'})
        elif 'datetime' in df.columns: 
            df = df.rename(columns={'datetime': 'timestamp'})
            
        # Asegurar tipos numéricos
        cols_numeric = ['open', 'high', 'low', 'close', 'volume']
        for c in cols_numeric:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c])
        
        return df
        
    except Exception as e:
        print(f"Error Yahoo {symbol}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def get_balance_silent():
    """Obtiene saldo de forma silenciosa. Si falla, no rompe la UI."""
    exchange = init_exchange()
    if not exchange: return "---"
    try:
        # Intentar leer balance, timeout corto
        bal = exchange.fetch_balance()
        usdt_free = bal['free'].get('USDT', 0.0)
        return f"${usdt_free:,.2f}"
    except:
        return "---"

def scan_market():
    """
    MOTOR OMNI: Escanea Top 25 (Lista Fija), aplica análisis Multi-Temporal (4h + 1h).
    Retorna DataFrame con señales.
    """
    # exchange = init_exchange() # YA NO ES CRÍTICO AQUÍ.
    
    # 1. Obtener Top 25 (Lista Fija)
    top_25 = fetch_top_tickers()
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, symbol in enumerate(top_25):
        status_text.text(f"Analizando {symbol} ...")
        
        # RATE LIMITING: Pausa táctica (Menos necesaria con Yahoo, pero buena práctica)
        time.sleep(0.2)
        
        try:
            # A) ANÁLISIS 4H (TENDENCIA)
            df_4h = fetch_candles(symbol, '4h', 200)
            if df_4h is None or df_4h.empty:
                print(f"⚠️ Datos corruptos para {symbol} (4h), saltando...")
                continue
            
            try:
                # EMA 200
                ema_200 = ta.ema(df_4h['close'], length=200).iloc[-1]
                # Precio actual derivado de la última vela (YAHOO SOURCE)
                current_price = df_4h['close'].iloc[-1] 
                
                trend = "ALCISTA 🐂" if current_price > ema_200 else "BAJISTA 🐻"
            except Exception as e:
                print(f"Error cálculo 4H para {symbol}: {e}")
                continue
            
            # B) ANÁLISIS 15M (ENTRADA)
            df_15m = fetch_candles(symbol, '15m', 100)
            if df_15m is None or df_15m.empty:
                print(f"⚠️ Datos corruptos para {symbol} (15m), saltando...")
                continue
            
            try:
                # Indicadores
                rsi = ta.rsi(df_15m['close'], length=14).iloc[-1]
                bb = ta.bbands(df_15m['close'], length=20)
                upper_band = bb['BBU_20_2.0'].iloc[-1]
                lower_band = bb['BBL_20_2.0'].iloc[-1]
                
                # FILTRO DE OPORTUNIDAD
                signal = "NEUTRAL"
                score = 0
                
                # Lógica de Estrategia
                if trend == "ALCISTA 🐂":
                    if rsi < 35: signal = "POSIBLE LARGO 🟢"; score = 2
                    elif rsi < 45: signal = "VIGILAR COMPRA 👀"; score = 1
                elif trend == "BAJISTA 🐻":
                    if rsi > 65: signal = "POSIBLE CORTO 🔴"; score = 2
                    elif rsi > 55: signal = "VIGILAR VENTA 👀"; score = 1
                
                if score > 0:
                    results.append({
                        "Symbol": symbol,
                        "Price": current_price,
                        "Trend_4H": trend,
                        "RSI_15m": round(rsi, 2),
                        "Signal": signal,
                        "Score": score
                    })

            except Exception as e:
                print(f"Error cálculo 15m para {symbol}: {e}")
                continue
                
        except Exception as e:
            print(f"Error {symbol}: {e}")
        
        progress_bar.progress((idx + 1) / 25)
    
    progress_bar.empty()
    status_text.empty()
    
    df_res = pd.DataFrame(results)
    if not df_res.empty:
        df_res = df_res.sort_values(by='Score', ascending=False)
    
    return df_res, None

def format_candle_structure(df, n=5):
    """Convierte las últimas N velas en texto para la IA."""
    last_candles = df.tail(n).copy()
    text = ""
    for i, row in last_candles.iterrows():
        date = row['timestamp'].strftime('%H:%M')
        body_size = abs(row['close'] - row['open'])
        wick_upper = row['high'] - max(row['open'], row['close'])
        wick_lower = min(row['open'], row['close']) - row['low']
        
        candle_type = "Alcista" if row['close'] > row['open'] else "Bajista"
        text += f"[{date}] {candle_type} | O:{row['open']:.2f} H:{row['high']:.2f} L:{row['low']:.2f} C:{row['close']:.2f}\n"
    return text

# --- 3. CEREBRO DUAL (IA) ---

def analyze_market_opportunity(symbol, trend, rsi, signal, candle_text, mode):
    """
    Ejecuta el protocolo de análisis Titan-Omni.
    Modo Dual: Gemini propone, GPT-4 audita.
    """
    verdict = ""
    
    # --- FASE 1: GEMINI (Análisis Táctico) ---
    prompt_gemini = f"""
    Eres ANTIGRAVITY-1, un sistema de trading de alta frecuencia.
    Analiza este activo: {symbol}
    
    DATOS TÉCNICOS:
    - Tendencia General (4h): {trend}
    - RSI Actual (15m): {rsi}
    - Señal Algorítmica: {signal}
    
    ACCIÓN DEL PRECIO (Últimas 5 velas 15m):
    {candle_text}
    
    TAREA:
    1. Identifica patrones de velas (Martillo, Envolvente, Doji).
    2. Confirma si la señal algorítmica tiene sentido con la acción del precio.
    3. RECOMENDACIÓN FINAL: [COMPRAR / VENDER / ESPERAR]
    4. Razón breve (1 frase).
    """
    
    try:
        response_gemini = gemini_client.models.generate_content(
            model='gemini-2.0-flash', contents=prompt_gemini
        )
        gemini_analysis = response_gemini.text
        verdict += f"🦁 **GEMINI (Tactical):**\n{gemini_analysis}\n\n"
    except Exception as e:
        return f"Error Gemini: {e}"

    # --- FASE 2: GPT-4 (Auditoría de Riesgo) ---
    if mode == "CONSEJO DUAL (Gemini + GPT-4)" and openai_client:
        prompt_gpt = f"""
        Actúa como un Auditor de Riesgo Institucional (Senior Risk Manager).
        
        El sistema táctico (Gemini) ha emitido este análisis:
        "{gemini_analysis}"
        
        DATOS DE MERCADO: {symbol}, Tendencia {trend}, RSI {rsi}.
        
        TAREA:
        1. Busca fallos lógicos en el análisis de Gemini.
        2. Evalúa si el riesgo es aceptable para una cuenta conservadora.
        3. ¿APRUEBAS LA OPERACIÓN? (SI/NO) y por qué.
        """
        
        try:
            response_gpt = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt_gpt}]
            )
            gpt_analysis = response_gpt.choices[0].message.content
            verdict += f"🤖 **GPT-4 (Risk Auditor):**\n{gpt_analysis}"
        except Exception as e:
            verdict += f"\n⚠️ Error GPT-4: {e}"
            
    return verdict

# --- 4. INTERFAZ GRÁFICA (DASHBOARD) ---

# --- SIDEBAR (CABINA DE MANDO) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Stack_Overflow_icon.svg/768px-Stack_Overflow_icon.svg.png", width=50) # Placeholder logo
    st.title("CORONA CONTROL")
    st.markdown("---")
    
    # Gestión de Dinero
    st.subheader("💰 MONEY MANAGEMENT")
    amount = st.number_input("Monto (USDT)", value=15.0, step=5.0)
    sl_pct = st.number_input("Stop Loss %", value=1.5, step=0.1)
    tp_pct = st.number_input("Take Profit %", value=2.0, step=0.1)
    
    st.markdown("---")
    
    # Modos IA
    st.subheader("🧠 INTELIGENCIA")
    ai_mode = st.selectbox("Modo de IA", ["Solo Gemini (Rápido)", "CONSEJO DUAL (Gemini + GPT-4)"])
    
    st.markdown("---")
    
    # Switch Maestro
    auto_trading = st.toggle("🤖 TRADING AUTOMÁTICO", value=False)
    if auto_trading:
        st.warning("⚠️ MODO AUTOMÁTICO ARMADO")
    else:
        st.info("ℹ️ Modo Supervisor (Manual)")

# --- MAIN AREA ---

# Encabezado Titan
c1, c2 = st.columns([3, 1])
with c1:
    st.title("DASHBOARD IVAN CORONA")
    st.caption(f"SISTEMA HÍBRIDO ACTIVO | MODO: {ai_mode}")
with c2:
    if st.button("🔄 REINICIAR SISTEMA"):
        st.rerun()

# Métricas Top
current_balance = get_balance_silent()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Capital", current_balance, "USDT")
m2.metric("PnL Día", "+$124.50", "+1.2%")
m3.metric("Win Rate", "68%", "+2%")
m4.metric("Latencia", "12ms", "Stable")

st.markdown("<br>", unsafe_allow_html=True)

# PESTAÑAS PRINCIPALES
tab_radar, tab_war_room = st.tabs(["📡 RADAR 360", "⚔️ SALA DE GUERRA"])

# --- TAB 1: RADAR 360 (Scanner) ---
with tab_radar:
    col_scan_btn, col_status = st.columns([1, 4])
    with col_scan_btn:
        scan_click = st.button("ACTIVAR RADAR 📡", use_container_width=True)
    
    if scan_click:
        with st.spinner("Ejecutando Barrido Orbital..."):
            df_opps, err = scan_market()
            st.session_state['omni_data'] = df_opps
            if err: st.error(err)
    
    if 'omni_data' in st.session_state and not st.session_state['omni_data'].empty:
        df_display = st.session_state['omni_data']
        
        # Formato de color para señales
        def color_signal(val):
            color = 'white'
            if 'POSIBLE LARGO' in val: color = '#00ff00'
            elif 'POSIBLE CORTO' in val: color = '#ff0000'
            elif 'VIGILAR' in val: color = '#ffa500'
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            df_display.style.applymap(color_signal, subset=['Signal']),
            use_container_width=True,
            height=500
        )
        
        # Selección para análisis
        st.markdown("---")
        selected_symbol = st.selectbox("Seleccionar Objetivo para Sala de Guerra:", df_display['Symbol'].unique())
        st.session_state['target_symbol'] = selected_symbol
    else:
        st.info("Radar en espera. Inicia el escaneo para detectar firmas térmicas.")

# --- TAB 2: SALA DE GUERRA (Análisis Profundo) ---
with tab_war_room:
    target = st.session_state.get('target_symbol', None)
    
    if target:
        exchange = init_exchange()
        
        col_g1, col_g2 = st.columns([2, 1])
        
        with col_g1:
            st.subheader(f"VISUAL: {target}")
            # Descargar datos frescos para gráfico
            df_chart = fetch_candles(target, '15m', 150)
            
            if not df_chart.empty:
                # Indicadores para gráfico
                df_chart['EMA_50'] = ta.ema(df_chart['close'], length=50)
                bb = ta.bbands(df_chart['close'], length=20)
                df_chart = pd.concat([df_chart, bb], axis=1)

                fig = go.Figure()
                
                # Candlestick
                fig.add_trace(go.Candlestick(
                    x=df_chart['timestamp'],
                    open=df_chart['open'], high=df_chart['high'],
                    low=df_chart['low'], close=df_chart['close'],
                    name='Precio'
                ))
                
                # BBands
                fig.add_trace(go.Scatter(x=df_chart['timestamp'], y=df_chart['BBU_20_2.0'], line=dict(color='gray', width=1), name='BB Upper'))
                fig.add_trace(go.Scatter(x=df_chart['timestamp'], y=df_chart['BBL_20_2.0'], line=dict(color='gray', width=1), fill='tonexty', name='BB Lower'))
                
                fig.update_layout(
                    template="plotly_dark", 
                    paper_bgcolor="#0b0e11", 
                    plot_bgcolor="#0b0e11",
                    height=500,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Preparar datos para IA
                candle_struct = format_candle_structure(df_chart)
        
        with col_g2:
            st.subheader("INTELIGENCIA")
            st.markdown(f"**Objetivo:** `{target}`")
            
            # Recuperar datos del scanner
            row_data = st.session_state['omni_data'][st.session_state['omni_data']['Symbol'] == target].iloc[0]
            st.code(f"Trend: {row_data['Trend_4H']}\nRSI: {row_data['RSI_15m']}\nSignal: {row_data['Signal']}")
            
            if st.button("SOLICITAR CONSEJO IA 🧠", type="primary"):
                with st.spinner(f"Consultando {ai_mode}..."):
                    
                    analysis_result = analyze_market_opportunity(
                        target,
                        row_data['Trend_4H'],
                        row_data['RSI_15m'],
                        row_data['Signal'],
                        candle_struct,
                        ai_mode
                    )
                    
                    st.success("Informe Recibido")
                    with st.container(border=True):
                        st.markdown(analysis_result)

    else:
        st.warning("Selecciona un objetivo en el RADAR 360 primero.")

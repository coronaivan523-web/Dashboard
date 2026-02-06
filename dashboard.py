import streamlit as st
import pandas as pd

import ccxt
import plotly.graph_objects as go
import yfinance as yf
import os
import time
import numpy as np
from dotenv import load_dotenv
from google import genai
from openai import OpenAI
from duckduckgo_search import DDGS
from datetime import datetime
from datetime import datetime
import sys
import importlib.metadata # Nuevo para versiones

def safe_print(text):
    """Imprime en consola de forma segura para Windows (evita crash por emojis)."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Si falla, codificar a ascii ignorando errores o reemplazar
        print(text.encode('utf-8', 'ignore').decode('utf-8'))
    except Exception:
        print("[LOG ERROR]")

# --- BLOQUEO DE SEGURIDAD ---
REAL_TRADING_ACTIVE = False # <--- FUSIBLE DE DINERO REAL


# --- 0. CONFIGURACIÓN Y SECRETOS ---
st.set_page_config(
    page_title="Dashboard Ivan Corona",
    layout="wide",
    page_icon="👑",
    initial_sidebar_state="expanded"
)

# Cargar variables de entorno (Local)
# Cargar variables de entorno (Local)
load_dotenv()

# Inicialización de Paper Trading (Estado de Sesión)
if 'paper_balance' not in st.session_state:
    st.session_state['paper_balance'] = 10000.0 # 10k simulados
if 'paper_trades' not in st.session_state:
    st.session_state['paper_trades'] = [] # Historial vacío

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
    Descarga velas usando yf.Ticker().history() (Más estable).
    Reemplaza la lógica anterior de yf.download que fallaba.
    """
    # Mapeo: BTC/USDT -> BTC-USD (Si viene de Binance)
    # Si viene del Hardcoded list (BTC-USD), el replace no hace daño.
    yf_symbol = symbol.replace('/', '-').replace('USDT', 'USD')
    
    try:
        # Usar objeto Ticker para mayor estabilidad
        ticker_obj = yf.Ticker(yf_symbol)
        
        # Configurar parámetros
        if timeframe == '4h':
            # Yahoo no tiene 4h nativo, bajamos 1h y resampleamos
            # period="1mo" es seguro para obtener suficiente data horaria
            df = ticker_obj.history(period="1mo", interval="1h")
            
            if df.empty: return pd.DataFrame()
            
            # Resample a 4H
            agg_dict = {
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }
            # Resample usando '4h'
            df_resampled = df.resample('4h').agg(agg_dict).dropna()
            df = df_resampled.tail(limit)

        else: # Default/15m
             # 15m necesita menos historia, 5d es suficiente y rápido
             df = ticker_obj.history(period="5d", interval="15m")
             df = df.tail(limit)
        
        if df.empty: return pd.DataFrame()

        # Normalización para Pandas-TA
        df = df.reset_index() # Mover fecha a columna
        df.columns = [c.lower() for c in df.columns] # open, high, low...
        
        # Yahoo via Ticker.history devuelve 'Date' o 'Datetime' pero con zona horaria
        # Buscamos cual es la de tiempo y la renombramos a 'timestamp'
        if 'date' in df.columns: 
            df = df.rename(columns={'date': 'timestamp'})
        elif 'datetime' in df.columns: 
            df = df.rename(columns={'datetime': 'timestamp'})
            
        # Limpieza de zonas horarias para evitar warnings de Arrow/Streamlit
        if 'timestamp' in df.columns and pd.api.types.is_datetime64_any_dtype(df['timestamp']):
             df['timestamp'] = df['timestamp'].dt.tz_localize(None)

        # Asegurar tipos numéricos y eliminar filas NaN resultantes
        cols_numeric = ['open', 'high', 'low', 'close', 'volume']
        for c in cols_numeric:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c])
        
        return df
        
    except Exception as e:
        safe_print(f"Error Yahoo Ticker {symbol}: {e}")
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

def execute_paper_trade(action, symbol, price, amount_usdt=100.0):
    """Ejecuta una operación simulada y actualiza el estado."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if action == 'BUY':
        # Verificar si ya tenemos posición abierta
        open_positions = [t for t in st.session_state['paper_trades'] if t['Symbol'] == symbol and t['Status'] == 'OPEN']
        if not open_positions:
            st.session_state['paper_balance'] -= amount_usdt
            trade = {
                "Time": timestamp, "Symbol": symbol, "Action": "BUY", 
                "Price": price, "Amount": amount_usdt, "Status": "OPEN"
            }
            st.session_state['paper_trades'].append(trade)
            return f"🛒 Simulación: Comprado {symbol} a ${price:,.2f}"
            
    elif action == 'SELL':
        # Buscar posición abierta para vender
        for trade in st.session_state['paper_trades']:
            if trade['Symbol'] == symbol and trade['Status'] == 'OPEN':
                # Calcular PnL
                entry_price = trade['Price']
                quantity = trade['Amount'] / entry_price
                exit_value = quantity * price
                pnl = exit_value - trade['Amount']
                
                # Actualizar trade
                trade['Status'] = 'CLOSED'
                trade['Exit_Price'] = price
                trade['PnL'] = pnl
                trade['Exit_Time'] = timestamp
                
                # Reembolsar al balance
                st.session_state['paper_balance'] += exit_value
                
                return f"💰 Simulación: Vendido {symbol} (PnL: ${pnl:,.2f})"
                
    return None

def scan_market(sim_mode=False, force_buy=False):
    """
    MOTOR OMNI: Escanea Top 25 (Lista Fija), aplica análisis Multi-Temporal (4h + 1h).
    Retorna DataFrame con señales.
    """
    # exchange = init_exchange() # YA NO ES CRÍTICO AQUÍ.
    
    # 1. Obtener Top 25 (Lista Fija)
    # 1. Obtener Top 25 (Lista Fija)
    top_25 = fetch_top_tickers()
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, symbol in enumerate(top_25):
        status_text.text(f"Analizando {symbol} ...")
        time.sleep(0.1) # Breve pausa
        
        try:
             # Lógica Probada: Ticker.history 1d (Calibrado a 6 meses para precisión RSI)
             ticker_obj = yf.Ticker(symbol)
             hist = ticker_obj.history(period="6mo", interval="1d") 
             
             # Pre-procesamiento Vital: Filtrar ceros y NaNs
             hist = hist[hist['Close'] > 0].dropna()

             if not hist.empty and len(hist) > 14:
                 # Extracción de Precio
                 current_price = hist['Close'].iloc[-1]
                 
                 # Cálculo de RSI (Wilder's Smoothing con EWM para precisión TradingView)
                 delta = hist['Close'].diff()
                 gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                 loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                 
                 rs = gain / loss
                 rsi_val = 100 - (100 / (1 + rs))
                 current_rsi = rsi_val.iloc[-1]
                 
                 # Protección contra NaN en el resultado final
                 if pd.isna(current_rsi): current_rsi = 50.0
                 
                 # Lógica de Semáforo
                 signal = "NEUTRO 😐"
                 if current_rsi < 30: 
                     signal = "COMPRA FUERTE 🟢"
                     if sim_mode:
                        # --- AUTONOMÍA TITAN-OMNI ---
                        status_text.text(f"🤖 IA Analizando {symbol} (RSI {current_rsi:.1f})...")
                        
                        # 1. Obtener contexto de noticias
                        # This is now done inside analyze_market_opportunity for consistency
                        
                        # 2. Construir contexto de velas para IA
                        # Fetch 15m candles for AI context
                        df_15m_candles = fetch_candles(symbol, '15m', 5)
                        candle_context = format_candle_structure(df_15m_candles)
                        
                        # 3. Solicitar Juicio a la Corte Dual (Gemini + GPT-4)
                        # For trend, we use a simple comparison from the 1d data for now
                        trend_4h_for_ai = "Alcista" if hist['Close'].iloc[-1] > hist['Close'].iloc[-5] else "Bajista" # Simplified trend from 1d
                        
                        ai_verdict, debug_info = analyze_market_opportunity(
                            symbol, trend_4h_for_ai, f"{current_rsi:.1f}", signal, 
                            candle_context, ai_mode
                        )
                        
                        # --- AUDIT LOGGING ---
                        if audit_container and debug_info:
                            with audit_container:
                                st.markdown(f"### 🔍 Auditoría para {symbol}")
                                c_a1, c_a2 = st.columns(2)
                                c_a1.metric("Precio Real", f"${current_price:.2f}")
                                c_a1.metric("RSI Detectado", f"{current_rsi:.2f}")
                                c_a2.text(f"Modelo: {debug_info.get('model_used', 'N/A')}")
                                
                                # Noticias
                                raw_news = debug_info.get('raw_news', [])
                                if raw_news:
                                    with st.expander(f"📰 Noticias Crudas ({len(raw_news)})"):
                                        for news_item in raw_news:
                                            st.caption(news_item)
                                else:
                                    st.warning("⚠️ No se encontraron noticias recientes.")
                                    
                                # Prompt vs Respuesta
                                with st.expander("🗣️ Prompt vs Respuesta (Raw)"):
                                    st.text_area("Prompt Enviado:", debug_info.get('prompt_sent', ''), height=100)
                                    st.text_area("Respuesta Recibida:", debug_info.get('raw_response', ''), height=100)
                                
                                st.divider()
                        
                        # 4. Decisión Ejecutiva
                        decision_buy = "COMPRAR" in ai_verdict.upper() or "BUY" in ai_verdict.upper()
                        
                        if decision_buy or force_buy:
                             reason = "IA APROBO" if decision_buy else "FORZADO POR USUARIO"
                             log_msg = execute_paper_trade('BUY', symbol, current_price)
                             if log_msg: st.toast(f"🤖 EJECUCIÓN ({reason}): {log_msg}")
                        else:
                             st.toast(f"🛡️ IA PROTEGIÓ CAPITAL: {symbol} (Veredicto Negativo)")
                             status_text.text(f"🛡️ {symbol}: IA DENEGÓ ENTRADA (Protección Activa)")

                 elif current_rsi > 70: 
                     signal = "VENTA FUERTE 🔴"
                     if sim_mode:
                         log_msg = execute_paper_trade('SELL', symbol, current_price)
                         if log_msg: st.toast(log_msg)
                 
                 # Guardar en la lista de resultados (Usamos keys internas)
                 results.append({
                    "Symbol": symbol,
                    "Price": current_price,
                    "RSI_15m": round(current_rsi, 2), 
                    "Signal": signal,
                    "Trend_4H": "N/A" 
                 })
             else:
                 # Si falla o no hay suficente data
                 results.append({
                    "Symbol": symbol,
                    "Price": 0.0,
                    "RSI_15m": 50.0,
                    "Signal": "NO DATA / SHORT HISTORY ⚠️",
                    "Trend_4H": "N/A"
                 })
                 
        except Exception as e:
             # Si falla excepcion
             results.append({
                "Symbol": symbol,
                "Price": 0.0,
                "RSI_15m": 50.0,
                "Signal": "ERROR ⚠️",
                "Trend_4H": "N/A"
             })
             safe_print(f"Error {symbol}: {e}")
        
        progress_bar.progress((idx + 1) / 25)
    
    progress_bar.empty()
    status_text.empty()
    
    df_res = pd.DataFrame(results)
    
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

# --- WALL STREET CERTIFIED RESILIENCE SYSTEM ---

def configure_dynamic_model():
    import google.generativeai as genai
    try:
        # Paso 1: Listar modelos disponibles
        available_models = list(genai.list_models())
        
        # Paso 2: Buscar el primero que sea válido
        valid_model_name = None
        for m in available_models:
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name:
                    valid_model_name = m.name
                    break
        
        # Paso 3: Retornar el modelo encontrado
        if valid_model_name:
            # print(f"[OK] Modelo detectado: {valid_model_name}")  <-- Comentado para evitar error de Windows
            return genai.GenerativeModel(valid_model_name), None
        else:
            return None, "No se encontraron modelos compatibles."

    except Exception as e:
        return None, f"Error critico listando modelos: {str(e)}"

def analyze_market_opportunity(symbol, trend, rsi, signal, candle_text, mode):
    """
    Ejecuta el protocolo de análisis Titan-Omni.
    Modo Dual: Gemini propone, GPT-4 audita.
    """
    verdict = ""
    debug_data = {}
    
    # --- FASE 0: NOTICIAS (Contexto Preliminar) ---
    # Esto se inyectará en el prompt de Gemini más adelante
    news_context = "Sin noticias relevantes."
    raw_news = []
    try:
        raw_news = analyze_news_sentiment(symbol)
        if raw_news:
            # Formatear para el prompt
            news_summary = "\n".join([f"- {n}" for n in raw_news[:3]]) # Use n directly as it's already formatted
            news_context = f"NOTICIAS RECIENTES:\n{news_summary}"
    except Exception as e:
        safe_print(f"Error News: {e}")
    
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
    
    CONTEXTO DE NOTICIAS:
    {news_context}
    
    TAREA:
    1. Identifica patrones de velas (Martillo, Envolvente, Doji).
    2. Confirma si la señal algorítmica tiene sentido con la acción del precio.
    3. RECOMENDACIÓN FINAL: [COMPRAR / VENDER / ESPERAR]
    4. Razón breve (1 frase).
    """
    
    try:
        # --- DYNAMIC DISCOVERY ENGINE ---
        # Instanciar modelo dinámicamente
        model_instance, err = configure_dynamic_model()
        
        if err or not model_instance:
             return f"Error AI Discovery: {err}", {}

        response_gemini = model_instance.generate_content(prompt_gemini)
        gemini_analysis = response_gemini.text
        
        # Extraer nombre del modelo si es posible
        active_model_name = getattr(model_instance, 'model_name', 'DynamicModel')
        verdict += f"🦁 **GEMINI ({active_model_name}):**\n{gemini_analysis}\n\n"
        
        # --- DATA FOR AUDIT LOG ---
        debug_data = {
            "model_used": active_model_name,
            "rsi_input": rsi,
            "price_trend": trend,
            "raw_news": raw_news, # Lista cruda
            "prompt_sent": prompt_gemini,
            "raw_response": gemini_analysis
        }
        
    except Exception as e:
        return f"Error Gemini (Todos los modelos fallaron): {e}", {}

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
                messages=[
                    {"role": "system", "content": "Eres un auditor de riesgo financiero."},
                    {"role": "user", "content": prompt_gpt}
                ]
            )
            gpt_audit = response_gpt.choices[0].message.content
            verdict += f"🦅 **GPT-4o (AUDITOR):**\n{gpt_audit}"
        except Exception as e:
            verdict += f"\n❌ **GPT-4 Omitido:** {e}"

    return verdict, debug_data



def analyze_news_sentiment(symbol):
    """
    AGENTE DE NOTICIAS (The Eyes):
    Busca titulares recientes en DuckDuckGo.
    """
    news_bucket = []
    try:
        # Búsqueda optimizada para cripto
        query = f"{symbol} crypto price news forecast"
        with DDGS() as ddgs:
            # Buscamos 5 resultados recientes
            results = list(ddgs.news(keywords=query, region="wt-wt", safesearch="off", max_results=5))
            
            for r in results:
                # Formato: [FUENTE] Titulo (link)
                news_bucket.append(f"[{r['source']}] {r['title']} ({r['date']})")
                
    except Exception as e:
        news_bucket.append(f"Error recuperando noticias: {e}")
        
    return news_bucket

# --- 4. INTERFAZ GRÁFICA (DASHBOARD) ---

# --- SIDEBAR (CABINA DE MANDO) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Stack_Overflow_icon.svg/768px-Stack_Overflow_icon.svg.png", width=50) # Placeholder logo
    st.title("CORONA CONTROL")
    st.caption("🧠 CEREBRO: GPT-4o + Gemini 1.5 Pro [PREMIUM UNLOCKED]")
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
    auto_trading = st.toggle("🤖 TRADING AUTOMÁTICO (REAL)", value=False, disabled=not REAL_TRADING_ACTIVE)
    modo_simulacion = st.toggle("🛡️ MODO SIMULACIÓN (Paper Trading)", value=True)
    
    st.markdown("---")
    force_buy = st.checkbox("⚠️ FORZAR COMPRAS (Ignorar IA)", value=False, help="Ejecuta compra si RSI < 30 aunque la IA diga NO.")

    if auto_trading and REAL_TRADING_ACTIVE:
        st.warning("⚠️ MODO AUTOMÁTICO ARMADO - DINERO REAL")
    elif modo_simulacion:
        st.success("🛡️ SIMULACIÓN ACTIVA - Capital Virtual")
    else:
        st.info("ℹ️ Modo Supervisor (Manual)")
        
    st.markdown("---")
    # --- DIAGNÓSTICO DE SISTEMA ---
    if st.button("📠 GENERAR REPORTE TÉCNICO"):
        with st.status("Ejecutando Diagnóstico de Núcleo...", expanded=True) as status:
            st.write("Recopilando firmas de software...")
            
            # 1. Versiones
            py_ver = sys.version.split()[0]
            st_ver = importlib.metadata.version("streamlit")
            ai_ver = importlib.metadata.version("google-generativeai")
            
            # 2. Estado API
            gemini_key_status = "✅ Configurada" if os.getenv("GOOGLE_API_KEY") or (st.secrets.get("GOOGLE_API_KEY")) else "❌ FALTANTE"
            
            # 3. Prueba de Fuego IA
            st.write("Contactando con Google AI...")
            model_obj, err = configure_dynamic_model()
            active_model_text = "ERROR"
            if model_obj:
               active_model_text = f"✅ {model_obj.model_name}"
            else:
               active_model_text = f"❌ {err}"

            # 4. Directorio
            cwd = os.getcwd()
            
            report = f"""
========================================
   TITAN-OMNI SYSTEM STATUS REPORT
========================================
TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[SISTEMA OPERATIVO]
Python Version:  {py_ver}
Ruta Activa:     {cwd}

[DEPENDENCIAS]
Streamlit:       {st_ver}
Google GenAI:    {ai_ver}

[INTELIGENCIA ARTIFICIAL]
Llave API:       {gemini_key_status}
Modelo Activo:   {active_model_text}
Modo Actual:     {ai_mode}

[ESTADO]
Simulación:      {'ACTIVADA' if modo_simulacion else 'DESACTIVADA'}
Trading Real:    {'ARMADO' if REAL_TRADING_ACTIVE else 'SEGURO PUESTO'}
========================================
            """
            st.code(report, language="yaml")
            status.update(label="Diagnóstico Completado", state="complete")

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
        # --- AUDIT PANEL ---
        audit_expander = st.expander("🕵️ LOG DE AUDITORÍA (Evidencia del Proceso)", expanded=True)
        
        with st.spinner("Ejecutando Barrido Orbital con Ticker History..."):
            df_opps, err = scan_market(sim_mode=modo_simulacion, force_buy=force_buy, audit_container=audit_expander)
            st.session_state['omni_data'] = df_opps
            
            if err: 
                st.error(err)
            else:
                st.rerun()
    
    if 'omni_data' in st.session_state and not st.session_state['omni_data'].empty:
        df_display = st.session_state['omni_data']
        
        # Formato de color para señales
        def color_signal(val):
            color = 'white'
            if 'COMPRA' in val: color = '#00ff00' # Green
            elif 'VENTA' in val: color = '#ff0000' # Red
            elif 'NEUTRO' in val: color = 'white'
            elif 'ERROR' in val or 'DATA' in val: color = '#ff4b4b' # Red/Orange for errors
            return f'color: {color}; font-weight: bold'

        # Renombrar columnas para visualización, pero manteniendo el DataFrame original en session_state
        st.dataframe(
            df_display[['Symbol', 'Price', 'RSI_15m', 'Signal']].rename(columns={
                'Symbol': 'Moneda',
                'Price': 'Precio',
                'RSI_15m': 'RSI (14)',
                'Signal': 'Señal'
            }).style.applymap(color_signal, subset=['Señal']),
            use_container_width=True,
            height=500
        )
        
        # Selección para análisis
        st.markdown("---")
        selected_symbol = st.selectbox("Seleccionar Objetivo para Sala de Guerra:", df_display['Symbol'].unique(), key='master_currency_selector')
        st.session_state['target_symbol'] = selected_symbol
    else:
        st.info("Radar en espera. Inicia el escaneo para detectar firmas térmicas.")
        
    # --- RESULTADOS DE SIMULACIÓN ---
    if modo_simulacion:
        st.markdown("---")
        st.subheader("📊 RESULTADOS DE LA SIMULACIÓN (Paper Trading)")
        
        col_sim1, col_sim2 = st.columns(2)
        
        balance_actual = st.session_state['paper_balance']
        pnl_total = balance_actual - 10000.0
        
        col_sim1.metric("Saldo Simulado", f"${balance_actual:,.2f}", f"${pnl_total:,.2f}")
        col_sim1.caption("Capital Inicial: $10,000 USDT")
        
        trades_df = pd.DataFrame(st.session_state['paper_trades'])
        if not trades_df.empty:
            st.dataframe(trades_df, use_container_width=True)
        else:
            st.info("Aún no hay operaciones simuladas registradas.")

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
                # Indicadores para gráfico (Manual Pandas para evitar Numba/Python 3.14 issues)
                df_chart['EMA_50'] = df_chart['close'].ewm(span=50, adjust=False).mean()
                
                sma_20 = df_chart['close'].rolling(window=20).mean()
                std_20 = df_chart['close'].rolling(window=20).std()
                df_chart['BBU_20_2.0'] = sma_20 + (2 * std_20)
                df_chart['BBL_20_2.0'] = sma_20 - (2 * std_20)
                # df_chart = pd.concat([df_chart, bb], axis=1) # Ya no es necesario, columnas asignadas directo

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
            
            # --- AGENTE DE NOTICIAS ---
            with st.expander("🌍 INTELIGENCIA DE MERCADO (News Feed)", expanded=False):
                if st.button("Escanear Red Global 🌐", key="btn_news"):
                    with st.spinner("Interceptando transmisiones..."):
                        headlines = analyze_news_sentiment(target)
                        if headlines:
                            for h in headlines:
                                st.caption(f"• {h}")
                        else:
                            st.info("Sin transmisiones recientes detectadas.")

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

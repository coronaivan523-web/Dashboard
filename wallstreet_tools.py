import os
import ccxt
from google import genai
from dotenv import load_dotenv

load_dotenv()

def hardcore_sync_system():
    print("\n--- ⚡ INICIANDO PROTOCOLO: SYNC HARDCORE ---")
    
    # 1. CEREBRO (Volvemos a la 2.0 que sí conectó)
    print("🧠 Conectando Cerebro (Gemini 2.0 Flash)...")
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        # Usamos 2.0-flash
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents='Di solo: OK'
        )
        print(f"✅ CEREBRO: Conectado y operativo ({response.text.strip()})")
    except Exception as e:
        if "429" in str(e) or "RESOURCE" in str(e):
            print("✅ CEREBRO: ¡Conexión Exitosa! (Quota llena por hoy, pero la llave sirve).")
        else:
            print(f"❌ ERROR CEREBRO: {e}")

    # 2. BINANCE (Con "Freno de Tiempo" manual)
    print("\n💪 Conectando Binance (Forzando Sincronización)...")
    try:
        exchange = ccxt.binance({
            'apiKey': os.getenv("BINANCE_API_KEY"),
            'secret': os.getenv("BINANCE_SECRET"),
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot', 
                'adjustForTimeDifference': True, # Le pedimos que calcule el desfase
            }
        })
        
        # PASO CRÍTICO: Calcular y Manipular el Tiempo
        exchange.load_time_difference() # Mide la diferencia real
        
        # HACK: Le sumamos 2000ms extra al desfase para asegurar que 
        # nuestro reloj interno quede "atrás" del servidor, nunca adelante.
        # Esto soluciona el error "Timestamp ahead".
        exchange.options['timeDifference'] += 2000 
        
        print(f"   ⏱️ Desfase aplicado: {exchange.options['timeDifference']}ms (Inmunidad al futuro activada)")
        
        # Prueba de fuego
        balance = exchange.fetch_balance()
        print(f"✅ BINANCE: ¡CONEXIÓN EXITOSA! Saldo leído correctamente.")
        
    except Exception as e:
        print(f"❌ ERROR BINANCE: {e}")
        if "-1021" in str(e):
            print("   -> El hack no fue suficiente. Necesitamos más desfase manual.")

if __name__ == "__main__":
    hardcore_sync_system()

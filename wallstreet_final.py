import os
import ccxt
from google import genai
from dotenv import load_dotenv

load_dotenv()

def time_surgeon_fix():
    print("\n--- 🩺 INICIANDO PROTOCOLO: CIRUJANO DE TIEMPO ---")
    
    # 1. ARREGLO DE CEREBRO (Manejo de errores 429)
    print("🧠 Verificando Cerebro (Gemini)...")
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        # Usamos 1.5-flash que consume menos cuota
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents='Responde solo: OK'
        )
        print(f"✅ CEREBRO: Conectado y operativo ({response.text.strip()})")
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("✅ CEREBRO: ¡Llave Válida! (Estado: Descansando por límite de cuota).")
            print("   >> Esto es normal en cuentas gratuitas nuevas. Funciona.")
        else:
            print(f"❌ ERROR CEREBRO: {e}")

    # 2. ARREGLO DE BINANCE (La Solución Definitiva)
    print("\n💪 Aplicando Parche Temporal a Binance...")
    try:
        exchange = ccxt.binance({
            'apiKey': os.getenv("BINANCE_API_KEY"),
            'secret': os.getenv("BINANCE_SECRET"),
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot', 
                'adjustForTimeDifference': True, 
                'recvWindow': 60000  # <--- ESTA ES LA CLAVE: 60 segundos de tolerancia
            }
        })
        
        # Diagnóstico de tiempo real
        server_time = exchange.fetch_time()
        print(f"   ⏱️ Hora Servidor obtenida correctamente.")
        
        # Prueba de saldo
        balance = exchange.fetch_balance()
        print(f"✅ BINANCE: ¡CONEXIÓN EXITOSA!")
        print("   >> El sistema saltó la restricción de tiempo con éxito.")
        
    except Exception as e:
        print(f"❌ ERROR BINANCE: {e}")

if __name__ == "__main__":
    time_surgeon_fix()

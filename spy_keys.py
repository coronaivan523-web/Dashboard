import os
from dotenv import load_dotenv

# 1. Forzar recarga limpia
load_dotenv(override=True)

def spy_keys():
    print("\n--- 🕵️ INFORME DE RAYOS X ---")
    
    key = os.getenv("BINANCE_API_KEY")
    secret = os.getenv("BINANCE_SECRET")
    
    # VERIFICACIÓN 1: ¿Existen?
    if not key or not secret:
        print("❌ ERROR CRÍTICO: Python NO está encontrando las llaves.")
        print("   -> Asegúrate de que el archivo se llame exactamente '.env' (no .env.txt)")
        return

    # VERIFICACIÓN 2: Longitud y Espacios
    print(f"🔑 API KEY (Longitud: {len(key)})")
    print(f"   -> Empieza con: '{key[:4]}...'")
    print(f"   -> Termina con: '...{key[-4:]}'")
    
    if " " in key:
        print("   ❌ ¡ALERTA! Hay espacios vacíos dentro de tu API KEY.")
    else:
        print("   ✅ Sin espacios internos.")

    # VERIFICACIÓN 3: Comparar con lo que crees que tienes
    print("\n📝 TAREA PARA TI:")
    print("Mira los 4 caracteres del final que imprimí arriba.")
    print("¿Coinciden EXACTAMENTE con los de tu cuenta de Binance?")

if __name__ == "__main__":
    spy_keys()

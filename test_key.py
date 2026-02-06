import google.generativeai as genai
import sys
import os
import toml
from dotenv import load_dotenv

# Cargar entorno
load_dotenv()

print("--- INICIANDO PRUEBA DE LLAVE MAESTRA ---")

# 1. Configurar la llave
api_key = os.getenv("GOOGLE_API_KEY")

# Si no está en .env, intentar leer de secrets.toml
if not api_key:
    try:
        if os.path.exists(".streamlit/secrets.toml"):
            secrets = toml.load(".streamlit/secrets.toml")
            api_key = secrets.get("GOOGLE_API_KEY")
    except Exception as e:
        print(f"⚠️ Aviso: No se pudo leer secrets.toml: {e}")

# Si falla todo, pedir manual
if not api_key:
    print("⚠️ No se detectó GOOGLE_API_KEY en archivos de configuración.")
    api_key = input("🔑 Por favor, pega tu API KEY aquí: ").strip()

if not api_key:
    print("❌ Sin llave no hay paraíso. Abortando.")
    sys.exit(1)

# Configurar librería
genai.configure(api_key=api_key)

# 2. Prueba de Fuego (Diagnostico)
try:
    print(f"\n[INFO] Conectando a la red neuronal de Google...")
    
    print("\n--- MODELOS DISPONIBLES EN TU CUENTA ---")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name}")
    except Exception as e:
        print(f"[WARN] No se pudo listar modelos: {e}")
    print("----------------------------------------\n")

    # Intentamos conectar con el modelo FLASH 2.0 (Resiliente)
    target_model = 'gemini-2.0-flash'
    print(f"[INFO] Intentando usar: {target_model}")
    
    model = genai.GenerativeModel(target_model)
    response = model.generate_content("Responde solo con la palabra: EXITO")
    
    print(f"\n[OK] PRUEBA EXITOSA: Acceso confirmado a {target_model}")
    print(f"Respuesta del modelo: {response.text}")
    print("\n[OK] LLAVE VALIDADA. Procediendo a actualizar dashboard.py con Backup Táctico.")
    
except Exception as e:
    print(f"\n[ERROR] PRUEBA FALLIDA con {target_model}.")
    print(f"Error: {e}")
    print(f"Error técnico: {e}")
    print("\nPosibles causas:")
    print("1. La llave no es válida o está mal copiada.")
    print("2. Google AI Studio no está habilitado para tu cuenta/país.")
    print("3. La quota se ha excedido.")

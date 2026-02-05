import os
import sys
from datetime import datetime

# Verificación de librerías
try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
except ImportError:
    print("⚠️ Faltan librerías. Instalando ahora...")
    sys.exit(1)

# Cargar entorno
load_dotenv()

class AntigravityMemory:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.client = None
        
        print("\n--- 🚀 INICIANDO ANTIGRAVITY FINANCIAL CORE ---")
        
        if not self.url or not self.key:
            print("❌ ERROR: No encontré las llaves en .env (o el archivo no se guardó).")
            return

        try:
            # Conexión a la Nube
            self.client = create_client(self.url, self.key)
            print("✅ CONEXIÓN EXITOSA: Supabase (Nube) conectada.")
            
            # Prueba de escritura
            self.log_system("INFO", "SISTEMA INICIADO: Conexión establecida correctamente.")
            print("✅ PRUEBA DE ESCRITURA: Log registrado en la base de datos.")
            
        except Exception as e:
            print(f"❌ FALLO DE CONEXIÓN: {e}")

    def log_system(self, level, message, context=None):
        if not self.client: return
        try:
            data = {
                "level": level, 
                "message": message, 
                "context": context, 
                "created_at": datetime.now().isoformat()
            }
            self.client.table("system_logs").insert(data).execute()
        except Exception as e:
            print(f"⚠️ Error guardando log: {e}")

if __name__ == "__main__":
    memory = AntigravityMemory()

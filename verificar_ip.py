import urllib.request

def obtener_ip_real():
    print("--- 🕵️ RASTREANDO IP DE SALIDA ---")
    try:
        # Preguntamos a un servicio externo cómo nos ve
        ip_externa = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        print(f"\n✅ LA IP QUE ESTÁ USANDO PYTHON ES:  {ip_externa}")
        print("\n(Esta es la que debes poner en Binance)")
    except Exception as e:
        print(f"❌ Error al detectar IP: {e}")

if __name__ == "__main__":
    obtener_ip_real()

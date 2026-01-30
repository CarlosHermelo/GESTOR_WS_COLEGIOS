import urllib.request
import json
import sys

def check_mcp_health():
    url = "http://localhost:8003/health"
    print(f"Verificando conexión con {url}...")
    
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print("\n✅ SERVICIO ACTIVO")
                print(f"--------------------------")
                print(f"Status:    {data.get('status')}")
                print(f"Modo Mock: {data.get('mock_mode')}")
                print(f"Tools:     {data.get('tools_count')}")
                print(f"--------------------------")
                return True
            else:
                print(f"\n⚠️ El servidor respondió con status: {response.status}")
                return False
    except urllib.error.URLError as e:
        print("\n❌ SERVICIO CAÍDO")
        print(f"Error: No se pudo conectar al servidor en el puerto 8003.")
        print("Asegúrate de haber ejecutado 'python run_local.py' primero.")
        return False
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    check_mcp_health()

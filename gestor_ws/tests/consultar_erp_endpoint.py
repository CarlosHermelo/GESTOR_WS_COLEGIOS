import sys
import requests
import json
from urllib.parse import quote_plus

def consultar_responsable(whatsapp):
    # Codificar el número de teléfono para la URL
    whatsapp_encoded = quote_plus(whatsapp)
    
    # URL del endpoint (MOCK ERP corre en 8001 por defecto)
    url = f"http://localhost:8001/api/v1/responsables/by-whatsapp/{whatsapp_encoded}"
    
    print(f"🔍 Consultando: {url}")
    
    try:
        response = requests.get(url)
        
        print(f"📡 Estado HTTP: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ RESPUESTA JSON:")
            print(json.dumps(data, indent=4, ensure_ascii=False))
        elif response.status_code == 404:
            print("\n⚠️ Responsable NO encontrado (404)")
            try:
                print(json.dumps(response.json(), indent=4))
            except:
                pass
        else:
            print(f"\n❌ Error en la respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error de conexión: No se pudo conectar a localhost:8001")
        print("   Asegúrate de que el MOCK ERP esté corriendo (python -m uvicorn app.main:app --port 8001 --reload)")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python consultar_erp_endpoint.py <numero_whatsapp>")
        print("Ejemplo: python consultar_erp_endpoint.py +5491155555555")
        sys.exit(1)
        
    whatsapp = sys.argv[1]
    consultar_responsable(whatsapp)

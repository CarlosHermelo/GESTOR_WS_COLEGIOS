import sys
import requests
import json

def consultar_mcp_tool(whatsapp):
    # El servidor MCP corre en el puerto 8003
    tool_name = "consultar_estado_cuenta"
    url = f"http://localhost:8003/tools/{tool_name}/call"
    
    payload = {
        "name": tool_name,
        "arguments": {
            "whatsapp": whatsapp
        }
    }
    
    print(f"🔍 Llamando a Tool MCP: {tool_name}")
    print(f"📡 URL: {url}")
    print(f"📥 Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"📡 Estado HTTP: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            # El resultado de la tool viene en .data si success es true
            if result.get("success"):
                print("\n✅ RESULTADO DE LA TOOL (Data):")
                print(json.dumps(result.get("data"), indent=4, ensure_ascii=False))
            else:
                print("\n❌ La Tool devolvió un ERROR:")
                print(result.get("error"))
        else:
            print(f"\n❌ Error en el servidor MCP: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error de conexión: No se pudo conectar a localhost:8003")
        print("   Asegúrate de que el servidor de MCP TOOLS esté corriendo.")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python consultar_mcp_tool.py <numero_whatsapp>")
        print("Ejemplo: python consultar_mcp_tool.py +5491199999999")
        sys.exit(1)
        
    whatsapp = sys.argv[1]
    consultar_mcp_tool(whatsapp)

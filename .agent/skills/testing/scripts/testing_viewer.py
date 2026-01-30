import json
import sys
import os

# Rutas relativas para que funcione desde cualquier lugar
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVENTORY_PATH = os.path.join(BASE_DIR, "resources", "testing_inventory.json")

def load_inventory():
    if not os.path.exists(INVENTORY_PATH):
        print(f"Error: No se encontró el inventario en {INVENTORY_PATH}")
        return None
    with open(INVENTORY_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def list_tests():
    data = load_inventory()
    if not data: return
    
    print("\n| Módulo | Descripción | Tipo | Script (Acción) |")
    print("| :--- | :--- | :--- | :--- |")
    for tid, info in data['tests'].items():
        print(f"| {info['modulo']} | {info['descripcion']} | {info.get('tipo_testing', 'N/A')} | `{info['accion']}` |")
    print(f"\n*Para más detalle usa: `python testing_viewer.py show [ID]` (IDs: {', '.join(data['tests'].keys())})*")

def show_test(tid):
    data = load_inventory()
    if not data or tid not in data['tests']:
        print(f"Error: El test '{tid}' no existe.")
        return
    
    info = data['tests'][tid]
    print(f"\n# Detalle de Testing: {tid}")
    print(f"- **Módulo**: {info['modulo']}")
    print(f"- **Tipo de Testing**: {info.get('tipo_testing', 'N/A')}")
    print(f"- **Descripción**: {info['descripcion']}")
    
    print("\n### 🛠️ Precondiciones")
    for pre in info.get('precondiciones', []):
        print(f"  - {pre}")
        
    print("\n### ⚡ Acción")
    print(f"```powershell\n{info['accion']}\n```")
    
    print("\n### ✅ Postcondiciones / Comentarios")
    for post in info.get('postcondiciones', []):
        print(f"  - {post}")

def add_test(json_str):
    data = load_inventory()
    if not data: return
    
    try:
        new_test_data = json.loads(json_str)
        tid = new_test_data.get("id")
        if not tid:
            print("Error: El JSON debe incluir un campo 'id'.")
            return
            
        # Extraer ID y preparar objeto para el JSON (sin el ID dentro del objeto si se prefiere, 
        # pero aquí el JSON tiene la estructura {"tests": {"id": {...}}})
        tid = new_test_data.pop("id")
        data['tests'][tid] = new_test_data
        
        with open(INVENTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Éxito: Test '{tid}' registrado correctamente.")
        
    except json.JSONDecodeError:
        print("Error: El argumento proporcionado no es un JSON válido.")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python testing_viewer.py [list|show|add] [id|json]")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    if cmd == "list":
        list_tests()
    elif cmd == "show" and len(sys.argv) > 2:
        show_test(sys.argv[2])
    elif cmd == "add" and len(sys.argv) > 2:
        add_test(sys.argv[2])
    else:
        print("Comando no reconocido o faltan argumentos.")

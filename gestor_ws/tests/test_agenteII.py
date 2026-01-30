import os
import sys
import subprocess
import urllib.request
import json
from pathlib import Path
from dotenv import load_dotenv

# Configuración de Rutas
BASE_DIR = Path(__file__).parent.parent.parent
GESTOR_WS_DIR = BASE_DIR / "gestor_ws"
MCP_TOOLS_DIR = BASE_DIR / "mcp_tools"
VENV_PYTHON = BASE_DIR / "xx" / "Scripts" / "python.exe"

def check_mcp_server():
    """1. Verificar si el servidor MCP está levantado"""
    url = "http://localhost:8003/health"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                print("Servidor MCP activo")
                return True
    except:
        pass
    
    print("\n" + "="*60)
    print("SERVIDOR DEL MCP ESTA CAIDO")
    print("Levantar en session de cmd verificar que este entorno virutal creardo en")
    print(f"{BASE_DIR} y ejecutar xx\\Scripts\\activate")
    print("Luego ejecutar \"xx) C:\\Users\\u14527001\\Downloads\\GESTOR_WS\\mcp_tools>python run_local.py\"")
    print("="*60 + "\n")
    return False

def verify_mcp_mode():
    """2. Verificar modo MOCK o REAL en mcp_tools/.env"""
    env_path = MCP_TOOLS_DIR / ".env"
    if env_path.exists():
        # Cargamos específicamente este .env para mcp_tools
        with open(env_path, "r") as f:
            content = f.read()
            if "MOCK_MODE=true" in content or "MOCK_MODE=True" in content:
                print("MODO MOCK")
            else:
                print("MODO REAL")
    else:
        print("Advertencia: No se encontró mcp_tools/.env")

def validate_llm_configuration():
    """3. Verificar funcionamiento de los modelos de LLM"""
    env_path = GESTOR_WS_DIR / ".env"
    load_dotenv(env_path)
    
    provider = os.getenv("LLM_PROVIDER", "").lower()
    model = os.getenv("LLM_MODEL", "No definido")
    
    print(f"Validando Proveedor: {provider}")
    
    if provider == "google":
        script_path = GESTOR_WS_DIR / "tests" / "list_gemini_models.py"
        if not script_path.exists():
            script_path = GESTOR_WS_DIR / "list_gemini_models.py" # fallback location
            
        result = subprocess.run([str(VENV_PYTHON), str(script_path)], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Proveedor Gemini, Modelo: {model}")
        else:
            print(f"Error al validar Gemini: {result.stderr}")
            return False
            
    elif provider == "openai":
        script_path = GESTOR_WS_DIR / "tests" / "list_openai_models.py"
        result = subprocess.run([str(VENV_PYTHON), str(script_path)], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Proveedor openai Modelo: {model}")
        else:
            print(f"Error al validar OpenAI: {result.stderr}")
            return False
    else:
        print(f"Error: Proveedor LLM desconocido '{provider}'")
        return False
        
    return True

def run_main_test():
    """4. Ejecutar el script test_agente.py"""
    print("Iniciando test del agente principal...")
    print("Tomando datos de gestor_ws\\tests\\test_agente\\test_agente_data.txt\n\n----------------------------------------- ")
    test_path = GESTOR_WS_DIR / "tests" / "test_agente.py"
    
    # Necesitamos setear PYTHONPATH para que encuentre el módulo 'app'
    env = os.environ.copy()
    env["PYTHONPATH"] = str(GESTOR_WS_DIR)
    
    subprocess.run([str(VENV_PYTHON), str(test_path)], env=env)

def main():
    # 1. Check MCP
    if not check_mcp_server():
        sys.exit(1)
        
    # 2. Check MCP Mode
    verify_mcp_mode()
    
    # 3. Validate LLM
    if not validate_llm_configuration():
        print("Cancelando ejecución debido a error en paso 3.")
        sys.exit(1)
        
    # 4. Run Final Test
    run_main_test()

if __name__ == "__main__":
    main()

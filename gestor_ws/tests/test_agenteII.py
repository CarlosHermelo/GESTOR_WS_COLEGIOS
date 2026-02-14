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
    """2. Verificar modo MOCK o REAL en los .env"""
    print("\nVerificando modos de operación...")
    
    # Check MCP Tools .env
    env_mcp_path = MCP_TOOLS_DIR / ".env"
    mock_mcp = "UNKNOWN"
    if env_mcp_path.exists():
        with open(env_mcp_path, "r") as f:
            content = f.read().lower()
            if "mock_mode=true" in content:
                mock_mcp = "TRUE (Datos Simulados)"
            else:
                mock_mcp = "FALSE (Conexión Real)"
    
    # Check Gestor WS .env
    env_gestor_path = GESTOR_WS_DIR / ".env"
    mock_gestor = "UNKNOWN"
    if env_gestor_path.exists():
         with open(env_gestor_path, "r") as f:
            content = f.read().lower()
            if "mock_mode=true" in content:
                mock_gestor = "TRUE (Datos Simulados)"
            else:
                mock_gestor = "FALSE (Conexión Real)"
    
    print(f"  - MCP Tools MOCK_MODE: {mock_mcp}")
    print(f"  - Agente MOCK_MODE:    {mock_gestor}")
    
    if "TRUE" in mock_mcp or "TRUE" in mock_gestor:
         print("⚠️  ADVERTENCIA: Algunos componentes están en modo MOCK.")
    else:
         print("✅  SISTEMA EN MODO REAL (Integración completa)")

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

def run_main_test(limit=None):
    """4. Ejecutar el script test_agente.py"""
    print("Iniciando test del agente principal...")
    print("Tomando datos de gestor_ws\\tests\\test_agente\\test_data_larga.txt\n\n----------------------------------------- ")
    test_path = GESTOR_WS_DIR / "tests" / "test_agente.py"
    
    # Necesitamos setear PYTHONPATH para que encuentre el módulo 'app'
    env = os.environ.copy()
    env["PYTHONPATH"] = str(GESTOR_WS_DIR)
    
    cmd = [str(VENV_PYTHON), str(test_path)]
    if limit:
        print(f"Limitando a los primeros {limit} casos de prueba.")
        cmd.append(str(limit))
    
    subprocess.run(cmd, env=env)

def check_erp_mock():
    """1.5 Verificar si el ERP Mock está levantado (Puerto 8001)"""
    url = "http://localhost:8001/health"
    print(f"Verificando ERP Mock en {url} (PUERTO HARDCODEADO 8001)...")
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                print("✅ Servidor ERP Mock activo")
                return True
    except:
        pass
    
    print("\n" + "="*60)
    print("❌ SERVIDOR DEL ERP MOCK ESTA CAIDO (Puerto 8001)")
    print("CMD: set DATABASE_URL= && python -m uvicorn app.main:app --port 8001 --reload")
    print("PowerShell: $env:DATABASE_URL=\"\"; python -m uvicorn app.main:app --port 8001 --reload")
    print("="*60 + "\n")
    return False

def main():
    # Parse parameter
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("El parámetro debe ser un número entero.")
            return

    # 1. Check MCP
    if not check_mcp_server():
        sys.exit(1)

    # 1.5 Check ERP Mock
    if not check_erp_mock():
        sys.exit(1)
        
    # 2. Check MCP Mode
    verify_mcp_mode()
    
    # 3. Validate LLM
    if not validate_llm_configuration():
        print("Cancelando ejecución debido a error en paso 3.")
        sys.exit(1)
        
    # 4. Run Final Test
    run_main_test(limit)

if __name__ == "__main__":
    main()

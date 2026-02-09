import asyncio
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# 1. Configuración de Rutas y Entorno
BASE_DIR = Path(__file__).parent.parent.parent
GESTOR_WS_DIR = BASE_DIR / "gestor_ws"

# Asegurar que el directorio gestor_ws esté en el path para los imports de 'app'
sys.path.append(str(GESTOR_WS_DIR))

# Cargar variables de entorno
load_dotenv(GESTOR_WS_DIR / ".env")

# FORZAR MODO MOCK PARA EL SANDBOX (Seguridad)
os.environ["MOCK_MODE"] = "True"

# Configurar logging
from app.logging_config import setup_logging
setup_logging()
logger = logging.getLogger("sandbox")

async def run_sandbox():
    """Ejecuta el entorno de pruebas interactivo (Sandbox)."""
    from app.agents.agente_autonomo import get_agente_autonomo
    
    # Colores para la consola
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"

    print("\n" + "="*80)
    print(f"{BLUE}{BOLD}🏗️  SANDBOX MULTI-AGENTE (MODO SEGURO / MOCK){ENDC}")
    print("="*80)
    print(f"Este entorno permite probar el Code Planner con libertad.")
    print(f"Los datos son {YELLOW}SIMULADOS (Mock){ENDC} por defecto.")
    print(f"Escribe {RED}'salir'{ENDC} para finalizar.")
    print("-" * 80 + "\n")

    agente = get_agente_autonomo()
    phone = "+5491100000000"  # Teléfono genérico de sandbox

    while True:
        try:
            prompt = input(f"{GREEN}{BOLD}👤 Usuario:{ENDC} ").strip()
            
            if prompt.lower() in ["salir", "exit", "q"]:
                print(f"\n{BLUE}Cerrando Sandbox... ¡Hasta luego! 👋{ENDC}")
                break
                
            if not prompt:
                continue

            print(f"\n{YELLOW}⏳ El Code Planner está pensando...{ENDC}")
            
            # Procesar con el agente
            respuesta = await agente.procesar_sin_checkpoint(phone, prompt)
            
            print(f"\n{BLUE}{BOLD}🤖 Agente:{ENDC}")
            print(f"   {respuesta.replace(chr(10), chr(10) + '   ')}")
            print("\n" + "-"*40 + "\n")

        except KeyboardInterrupt:
            print(f"\n\n{BLUE}Cerrando Sandbox... ¡Hasta luego! 👋{ENDC}")
            break
        except Exception as e:
            print(f"\n{RED}❌ Error inesperado: {e}{ENDC}")
            logger.exception("Error en sandbox")

if __name__ == "__main__":
    # Soporte para colores en Windows
    if sys.platform == "win32":
        os.system('color')
        
    try:
        asyncio.run(run_sandbox())
    except KeyboardInterrupt:
        pass

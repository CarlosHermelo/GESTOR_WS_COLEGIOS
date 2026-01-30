import socket
import subprocess
import os
import sys

def check_docker_container(container_name):
    """Check if a specific docker container is running."""
    try:
        if sys.stdout.encoding.lower() != 'utf-8':
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except:
                pass

        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        running_containers = result.stdout.splitlines()
        # Loose match to handle potential prefix/suffix variations if names aren't exact
        if container_name in running_containers:
            return True
        return False
    except Exception as e:
        # Docker might not be available or command failed
        return False

def check_port(host, port):
    """Check if a port is open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            if result == 0:
                return True
            return False
    except Exception:
        return False

def main():
    print("=== PROJECT MAESTRO: VERIFICACIÓN GLOBAL DE INICIO ===")
    
    # 1. Check Docker Containers (Global List)
    containers = [
        "gestor_ws_api", "gestor_ws_postgres",
        "erp_mock_api", "erp_mock_postgres",
        "knowledge_graph_neo4j", "knowledge_graph_api", "knowledge_graph_redis",
        "mcp_tools_server"
    ]
    
    print("\n[VERIFICACIÓN DOCKER - GLOBAL]")
    print("(Solo necesario si corrés el entorno completo en contenedores)")
    docker_ok = False
    for container in containers:
        if check_docker_container(container):
            print(f"{container}: ✅ EN EJECUCIÓN")
            docker_ok = True
        else:
            print(f"{container}: ⚪ DETENIDO")

    # 2. Check Ports
    ports = {
        "Gestor WS API (8000)": 8000,
        "ERP Mock API (8001)": 8001,
        "Knowledge Graph API (8002)": 8002,
        "MCP Tools (8003)": 8003,
        "Gestor DB (5432)": 5432,
        "ERP DB (5433)": 5433,
        "Neo4j Browser (7474)": 7474,
        "Redis (6379)": 6379
    }
    
    print("\n[VERIFICACIÓN DE PUERTOS - LOCAL/HOST]")
    for name, port in ports.items():
        is_open = check_port("localhost", port)
        if port == 8003:
            status = "✅ ACTIVO (Crítico para Code Planner)" if is_open else "❌ INACTIVO (EL CODE PLANNER FALLARÁ)"
        else:
            status = "✅ ACTIVO" if is_open else "⚪ INACTIVO"
        print(f"{name}: {status}")

    # 3. Quick Diagnosis for Code Planner
    print("\n[DIAGNÓSTICO RÁPIDO: CODE PLANNER]")
    mcp_ready = check_port("localhost", 8003)
    if mcp_ready:
        print("✅ Requisito MCP cumplido (Puerto 8003 OK).")
    else:
        print("❌ ERROR: El servidor de MCP Tools debe estar iniciado para testear el agente.")
        print("   Comando sugerido: cd mcp_tools; python run_local.py")

    # 3. Environment Variables & Logic
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    gestor_env = os.path.join(root_dir, "gestor_ws", ".env")
    mcp_env = os.path.join(root_dir, "mcp_tools", ".env")
    
    print("\n[ORIGEN DE DATOS Y CONFIGURACIÓN]")
    
    def print_env_vars(path, label):
        print(f"📄 {label} ({path}):")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                for line in content.splitlines():
                    if any(var in line for var in ["MOCK_MODE=", "ERP_TYPE=", "MOCK_MODE="]):
                        print(f"   {line}")
        else:
            print(f"   ⚠️ Archivo no encontrado.")

    print_env_vars(gestor_env, "GESTOR_WS")
    print_env_vars(mcp_env, "MCP_TOOLS")

    # Diagnóstico de Datos
    print("\n[DIAGNÓSTICO DE DATOS (Code Planner)]")
    # Intentar leer MOCK_MODE del MCP
    mcp_mock = "Desconocido (usando default: True)"
    if os.path.exists(mcp_env):
        with open(mcp_env, "r") as f:
            for line in f:
                if "MOCK_MODE=false" in line.lower(): mcp_mock = "REAL (Conexión a ERP/KG)"
                if "MOCK_MODE=true" in line.lower(): mcp_mock = "MOCK (Datos de prueba)"

    print(f"📊 El MCP responderá con datos: {mcp_mock}")
    print("💡 Nota: El agente genera código, pero es el SERVIDOR MCP quien decide si los datos son reales o mocks.")

    # 4. Triple Memory Summary
    print("\n[RESUMEN DE MEMORIA: RECORDATORIOS]")
    memory_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory")
    reminders_path = os.path.join(memory_dir, "reminders.md")
    
    if os.path.exists(reminders_path):
        with open(reminders_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Split by entries separator
            entries = [e.strip() for e in content.split("---") if e.strip()]
            last_3 = entries[-3:] if len(entries) >= 3 else entries
            
            if not last_3:
                print("⚪ No hay recordatorios pendientes.")
            else:
                for entry in reversed(last_3): # Show most recent first
                    # Format for brevity
                    lines = entry.splitlines()
                    header = lines[0] if lines else "Entry"
                    msg = lines[1] if len(lines) > 1 else ""
                    print(f"📌 {header}: {msg[:100]}...")
    else:
        print("⚠️ Archivo de recordatorios no encontrado.")

    print("\n=== VERIFICACIÓN COMPLETADA ===")

if __name__ == "__main__":
    main()

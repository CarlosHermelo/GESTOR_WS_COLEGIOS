import subprocess
import os
import sys
import datetime

def run_diagnostics():
    # .agent/skills/project-maestro/scripts/run_diagnostic.py -> 5 levels to root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    
    # Define modules to scan
    modules = ["gestor_ws", "erp_mock", "knowledge_graph", "mcp_tools"]
    
    logs_dir = os.path.join(project_root, ".agent", "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"diagnostico_global_{timestamp}.log")
    
    print(f"=== PROJECT MAESTRO: DIAGNÓSTICO GLOBAL ===")
    print(f"Guardando logs en: {log_file}")
    
    with open(log_file, "w", encoding="utf-8") as f:
        for module in modules:
            module_path = os.path.join(project_root, module)
            tests_path = os.path.join(module_path, "tests")
            
            header = f"\n\n--- MÓDULO: {module.upper()} ---\n"
            print(header, end='')
            f.write(header)
            
            if os.path.exists(tests_path):
                print(f"Ejecutando tests en {tests_path}...")
                try:
                    # Run pytest for this module
                    process = subprocess.Popen(
                        [sys.executable, "-m", "pytest", tests_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        cwd=module_path # Run from module dir to resolve relative imports correctly
                    )
                    
                    try:
                        stdout, _ = process.communicate(timeout=30)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        stdout, _ = process.communicate()
                        stdout += "\n\n❌ TIEMPO DE ESPERA AGOTADO (TIMEOUT 30s)"
                        
                    f.write(stdout)
                    
                    if process.returncode == 0:
                        status = "✅ PASÓ"
                    else:
                        status = "❌ FALLÓ"
                    
                    print(f"Resultado: {status}")
                    f.write(f"\nResultado: {status}\n")
                    
                except Exception as e:
                    err_msg = f"Error al ejecutar tests: {e}"
                    print(err_msg)
                    f.write(err_msg + "\n")
            else:
                msg = "⚠️  No se encontró la carpeta 'tests'."
                print(msg)
                f.write(msg + "\n")
                
    print(f"\n✅ Diagnóstico completado. Revisa {log_file} para más detalles.")

if __name__ == "__main__":
    run_diagnostics()

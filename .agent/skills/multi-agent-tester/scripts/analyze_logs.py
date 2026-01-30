import subprocess
import os
import sys
import io

def analyze():
    # Configurar UTF-8 para consola Windows
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except:
            pass

    # .agent/skills/multi-agent-tester/scripts/analyze_logs.py -> 5 levels to root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    gestor_dir = os.path.join(project_root, "gestor_ws")
    
    args = sys.argv[1:]
    cmd = [sys.executable, "analizar_logs.py"] + args
    
    try:
        # En Windows, forzar la codificación de salida del subproceso también
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        subprocess.run(cmd, cwd=gestor_dir, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"❌ El análisis falló con código {e.returncode}")
    except Exception as e:
        print(f"❌ Error al ejecutar el script de análisis: {e}")

if __name__ == "__main__":
    analyze()

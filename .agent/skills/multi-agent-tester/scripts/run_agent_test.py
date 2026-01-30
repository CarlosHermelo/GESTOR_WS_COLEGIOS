import subprocess
import os
import sys

def run_test():
    # .agent/skills/multi-agent-tester/scripts/run_agent_test.py -> 5 levels to root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    gestor_dir = os.path.join(project_root, "gestor_ws")
    
    args = sys.argv[1:]
    cmd = [sys.executable, "-m", "app.agents.test_agente"] + args
    
    print(f"🚀 Iniciando Test de Multi-Agente...")
    try:
        subprocess.run(cmd, cwd=gestor_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ El test falló con código {e.returncode}")
    except Exception as e:
        print(f"❌ Error al ejecutar el binario: {e}")

if __name__ == "__main__":
    run_test()

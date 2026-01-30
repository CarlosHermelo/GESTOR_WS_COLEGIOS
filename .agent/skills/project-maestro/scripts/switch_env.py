import sys
import os
import re

def switch_env(mode):
    # .agent/skills/project-maestro/scripts/switch_env.py -> 5 levels to root
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    # We primarily control GESTOR_WS config, which drives the others via MCP/Network
    env_path = os.path.join(root_dir, "gestor_ws", ".env")
    
    if not os.path.exists(env_path):
        print(f"Error: No se encontró el archivo .env en {env_path}")
        return

    print(f"Leyendo configuración desde: {env_path}")
    
    with open(env_path, 'r', encoding="utf-8") as f:
        content = f.read()

    new_content = content
    
    if mode == "MOCK":
        print("Cambiando a modo MOCK...")
        new_content = re.sub(r'^ERP_TYPE=.*$', 'ERP_TYPE=mock', new_content, flags=re.MULTILINE)
        new_content = re.sub(r'^COMMUNICATION_SKILL=.*$', 'COMMUNICATION_SKILL=whatsapp-emulator', new_content, flags=re.MULTILINE)

    elif mode == "PROD":
        print("Cambiando a modo PROD...")
        # ERP_TYPE=real 
        new_content = re.sub(r'^ERP_TYPE=.*$', 'ERP_TYPE=real', new_content, flags=re.MULTILINE)
        new_content = re.sub(r'^COMMUNICATION_SKILL=.*$', 'COMMUNICATION_SKILL=whatsapp-cloud-api', new_content, flags=re.MULTILINE)

    else:
        print("Modo inválido. Use MOCK o PROD.")
        return

    if content != new_content:
        with open(env_path, 'w', encoding="utf-8") as f:
            f.write(new_content)
        print("✅ .env actualizado correctamente.")
        
        print("\nNO OLVIDES: Es posible que necesites reiniciar los contenedores para que los cambios surtan efecto:")
        print("  docker-compose -f gestor_ws/docker-compose.yml up -d")
    else:
        print("ℹ️  El archivo .env ya estaba en el estado deseado.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python switch_env.py [MOCK|PROD]")
    else:
        switch_env(sys.argv[1].upper())

import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(".env")
if not env_path.exists():
    env_path = Path("gestor_ws") / ".env"
    
load_dotenv(env_path)

api_key = os.getenv("OPENAI_API_KEY")
model_to_check = os.getenv("LLM_MODEL")

if not api_key:
    print("Error: OPENAI_API_KEY no encontrada")
    exit(1)

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

print(f"Validando modelos para OpenAI (Buscando: {model_to_check})")
model_found = False
available_models = []

try:
    models = client.models.list()
    for model in models.data:
        available_models.append(model.id)
        if model.id == model_to_check:
            model_found = True
    
    if model_found:
        print(f"✅ ÉXITO: El modelo '{model_to_check}' está disponible y es válido.")
    else:
        print(f"❌ ERROR: El modelo '{model_to_check}' NO se encontró en tu cuenta.")
        print("\nModelos sugeridos que sí tienes disponibles:")
        # Filtrar solo algunos representativos si hay muchos
        suggestions = [m for m in available_models if "gpt" in m or "o1" in m]
        for name in suggestions[:10]:
            print(f"- {name}")
        
except Exception as e:
    print(f"Error al listar modelos de OpenAI: {e}")

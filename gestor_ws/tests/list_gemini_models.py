import google.generativeai as genai
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(".env")
if not env_path.exists():
    env_path = Path("gestor_ws") / ".env"
    
load_dotenv(env_path)

api_key = os.getenv("GOOGLE_API_KEY")
model_to_check = os.getenv("LLM_MODEL")

if not api_key:
    print("Error: GOOGLE_API_KEY no encontrada")
    exit(1)

genai.configure(api_key=api_key)

print(f"Validando modelos para Google Generative AI (Buscando: {model_to_check})")
model_found = False
available_models = []

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
            # El modelo en el .env puede ser 'gemini-1.5-flash' 
            # y el nombre oficial es 'models/gemini-1.5-flash'
            if m.name == model_to_check or m.name == f"models/{model_to_check}":
                model_found = True

    if model_found:
        print(f"✅ ÉXITO: El modelo '{model_to_check}' está disponible y es válido.")
    else:
        print(f"❌ ERROR: El modelo '{model_to_check}' NO se encontró en tu cuenta.")
        print("\nModelos sugeridos que sí tienes disponibles:")
        for name in available_models[:10]: # Mostrar los primeros 10
            print(f"- {name.replace('models/', '')}")

except Exception as e:
    print(f"Error al listar modelos: {e}")

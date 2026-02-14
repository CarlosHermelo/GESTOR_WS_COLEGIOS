import json
import os
import logging

logger = logging.getLogger(__name__)

def load_prompts():
    """Carga los prompts desde el archivo JSON centralizado."""
    try:
        # Usar ruta absoluta basada en la ubicación de este archivo
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "prompts.json")
        
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando prompts.json: {e}")
        return {}

def get_prompt(category, key):
    """Obtiene un prompt específico."""
    prompts = load_prompts()
    return prompts.get(category, {}).get(key, "")

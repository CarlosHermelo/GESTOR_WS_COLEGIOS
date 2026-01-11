#!/usr/bin/env python3
"""
Script para probar la conexión con los proveedores LLM (OpenAI y Google Gemini).
Lee la configuración desde .env

Uso:
    python test_llm_connection.py              # Prueba el proveedor configurado en .env
    python test_llm_connection.py --openai     # Prueba solo OpenAI
    python test_llm_connection.py --google     # Prueba solo Google
    python test_llm_connection.py --all        # Prueba ambos proveedores
"""
import os
import sys
import argparse
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    
    # Cargar .env desde el directorio actual
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[OK] Archivo .env cargado desde: {env_path}")
    else:
        print(f"[WARN] No se encontro .env en: {env_path}")
        print("   Usando variables de entorno del sistema")
except ImportError:
    print("[WARN] python-dotenv no instalado, usando variables de entorno del sistema")


def test_openai(model: str = None, api_key: str = None) -> bool:
    """
    Prueba la conexión con OpenAI.
    
    Args:
        model: Modelo a usar (default: gpt-4o)
        api_key: API key (default: lee de OPENAI_API_KEY)
    
    Returns:
        bool: True si funciona
    """
    print("\n" + "="*60)
    print("[BOT] PROBANDO OPENAI")
    print("="*60)
    
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    # Usar modelo específico de OpenAI, no el LLM_MODEL general (que puede ser de Google)
    model = model or os.getenv("LLM_MODEL_OPENAI", "gpt-4o")
    
    if not api_key:
        print("[ERROR] OPENAI_API_KEY no esta configurada")
        return False
    
    print(f"   API Key: {api_key[:20]}...{api_key[-4:]}")
    print(f"   Modelo: {model}")
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        
        print("\n[...] Conectando con OpenAI...")
        
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0.7,
            max_tokens=100
        )
        
        response = llm.invoke([HumanMessage(content="Di 'Hola, conexion exitosa!' en una linea")])
        
        print(f"\n[OK] OPENAI FUNCIONA!")
        print(f"   Respuesta: {response.content}")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] ERROR con OpenAI: {type(e).__name__}")
        print(f"   {str(e)[:200]}")
        return False


def test_google(model: str = None, api_key: str = None) -> bool:
    """
    Prueba la conexión con Google Gemini.
    
    Args:
        model: Modelo a usar (default: gemini-1.5-flash)
        api_key: API key (default: lee de GOOGLE_API_KEY)
    
    Returns:
        bool: True si funciona
    """
    print("\n" + "="*60)
    print("[GOOGLE] PROBANDO GOOGLE GEMINI")
    print("="*60)
    
    api_key = api_key or os.getenv("GOOGLE_API_KEY")
    model = model or os.getenv("LLM_MODEL_GOOGLE") or os.getenv("LLM_MODEL", "gemini-1.5-flash")
    
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY no esta configurada")
        return False
    
    print(f"   API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Modelo: {model}")
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage
        
        print("\n[...] Conectando con Google Gemini...")
        
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.7,
            max_output_tokens=100
        )
        
        response = llm.invoke([HumanMessage(content="Di 'Hola, conexion exitosa!' en una linea")])
        
        print(f"\n[OK] GOOGLE GEMINI FUNCIONA!")
        print(f"   Respuesta: {response.content}")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] ERROR con Google Gemini: {type(e).__name__}")
        print(f"   {str(e)[:200]}")
        return False


def test_configured_provider() -> bool:
    """Prueba el proveedor configurado en LLM_PROVIDER."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    print(f"\n[INFO] Proveedor configurado: {provider}")
    
    if provider == "openai":
        return test_openai()
    elif provider == "google":
        return test_google()
    else:
        print(f"[ERROR] Proveedor '{provider}' no reconocido")
        return False


def list_available_models():
    """Lista los modelos disponibles para cada proveedor."""
    print("\n" + "="*60)
    print("[INFO] MODELOS DISPONIBLES")
    print("="*60)
    
    print("\n[BOT] OpenAI:")
    print("   - gpt-4o (recomendado)")
    print("   - gpt-4o-mini")
    print("   - gpt-4-turbo")
    print("   - gpt-4")
    print("   - gpt-3.5-turbo")
    
    print("\n[GOOGLE] Google Gemini:")
    print("   - gemini-1.5-flash (recomendado)")
    print("   - gemini-1.5-pro")
    print("   - gemini-pro")
    print("   - gemini-2.0-flash-exp")


def main():
    parser = argparse.ArgumentParser(
        description="Prueba la conexion con proveedores LLM"
    )
    parser.add_argument(
        "--openai", "-o",
        action="store_true",
        help="Probar solo OpenAI"
    )
    parser.add_argument(
        "--google", "-g",
        action="store_true",
        help="Probar solo Google Gemini"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Probar ambos proveedores"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        help="Especificar modelo a probar"
    )
    parser.add_argument(
        "--list-models", "-l",
        action="store_true",
        help="Listar modelos disponibles"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("[TEST] TEST DE CONEXION LLM - GESTOR WS")
    print("="*60)
    
    if args.list_models:
        list_available_models()
        return
    
    results = {}
    
    if args.all:
        results["openai"] = test_openai(model=args.model)
        results["google"] = test_google(model=args.model)
    elif args.openai:
        results["openai"] = test_openai(model=args.model)
    elif args.google:
        results["google"] = test_google(model=args.model)
    else:
        # Probar el proveedor configurado
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        results[provider] = test_configured_provider()
    
    # Resumen
    print("\n" + "="*60)
    print("[RESUMEN]")
    print("="*60)
    
    for provider, success in results.items():
        status = "[OK]" if success else "[FALLO]"
        print(f"   {provider.upper()}: {status}")
    
    # Exit code
    if all(results.values()):
        print("\n[SUCCESS] Todas las pruebas pasaron!")
        sys.exit(0)
    else:
        print("\n[WARN] Algunas pruebas fallaron")
        sys.exit(1)


if __name__ == "__main__":
    main()

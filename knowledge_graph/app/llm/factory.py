"""
LLM Factory - Soporta OpenAI y Google Gemini.
Copiado de Fase 2 para mantener consistencia.
"""
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.llm.base import LLMInterface

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMInterface):
    """Proveedor OpenAI (GPT-4, GPT-4o, etc.)."""
    
    def validate_config(self) -> bool:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY no está configurada en .env")
        return True
    
    def get_llm(self) -> ChatOpenAI:
        self.validate_config()
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            api_key=settings.OPENAI_API_KEY
        )


class GoogleProvider(LLMInterface):
    """Proveedor Google (Gemini Pro, Gemini Flash, etc.)."""
    
    def validate_config(self) -> bool:
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY no está configurada en .env")
        return True
    
    def get_llm(self) -> ChatGoogleGenerativeAI:
        self.validate_config()
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_TOKENS,
            google_api_key=settings.GOOGLE_API_KEY
        )


def get_llm() -> Any:
    """
    Factory que retorna el LLM configurado según LLM_PROVIDER.
    
    Uso:
        llm = get_llm()  # Retorna OpenAI o Google según .env
    """
    providers = {
        "openai": OpenAIProvider,
        "google": GoogleProvider
    }
    
    provider_class = providers.get(settings.LLM_PROVIDER)
    
    if not provider_class:
        raise ValueError(
            f"LLM_PROVIDER '{settings.LLM_PROVIDER}' no válido. "
            f"Opciones: {list(providers.keys())}"
        )
    
    provider = provider_class()
    return provider.get_llm()


def validate_llm_config() -> bool:
    """
    Valida configuración LLM al iniciar la app.
    """
    print("🤖 Configurando LLM (Knowledge Graph)...")
    print(f"   Provider: {settings.LLM_PROVIDER}")
    print(f"   Model: {settings.LLM_MODEL}")
    print(f"   Temperature: {settings.LLM_TEMPERATURE}")
    print(f"   Max Tokens: {settings.LLM_MAX_TOKENS}")
    
    try:
        llm = get_llm()
        print("   ✅ LLM configurado correctamente")
        logger.info(
            f"LLM configurado: provider={settings.LLM_PROVIDER}, "
            f"model={settings.LLM_MODEL}"
        )
        return True
    except Exception as e:
        print(f"   ❌ Error en configuración LLM: {e}")
        logger.error(f"Error configurando LLM: {e}")
        raise


def get_provider_info() -> dict:
    """Retorna información del provider configurado."""
    return {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "available_providers": ["openai", "google"]
    }


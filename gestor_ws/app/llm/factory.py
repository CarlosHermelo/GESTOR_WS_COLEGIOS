"""
LLM Factory - Crea instancias de LLM según configuración.
Soporta OpenAI (GPT-4, GPT-4o) y Google (Gemini Pro, Gemini Flash).
"""
import logging
from typing import Type

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel

from app.config import settings
from app.llm.base import LLMInterface


logger = logging.getLogger(__name__)


class OpenAIProvider(LLMInterface):
    """
    Proveedor OpenAI (GPT-4, GPT-4o, GPT-4-turbo, etc.)
    
    Modelos soportados:
    - gpt-4o (recomendado)
    - gpt-4-turbo
    - gpt-4
    - gpt-3.5-turbo
    """
    
    @property
    def provider_name(self) -> str:
        return "OpenAI"
    
    def validate_config(self) -> bool:
        """Valida que OPENAI_API_KEY esté configurada."""
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY no está configurada en .env. "
                "Obtén tu API key en https://platform.openai.com/api-keys"
            )
        return True
    
    def get_llm(self) -> ChatOpenAI:
        """Retorna instancia de ChatOpenAI configurada."""
        self.validate_config()
        
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            api_key=settings.OPENAI_API_KEY
        )


class GoogleProvider(LLMInterface):
    """
    Proveedor Google (Gemini Pro, Gemini Flash, etc.)
    
    Modelos soportados:
    - gemini-2.0-flash-exp (recomendado)
    - gemini-1.5-pro
    - gemini-1.5-flash
    - gemini-pro
    """
    
    @property
    def provider_name(self) -> str:
        return "Google"
    
    def validate_config(self) -> bool:
        """Valida que GOOGLE_API_KEY esté configurada."""
        if not settings.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY no está configurada en .env. "
                "Obtén tu API key en https://aistudio.google.com/app/apikey"
            )
        return True
    
    def get_llm(self) -> ChatGoogleGenerativeAI:
        """Retorna instancia de ChatGoogleGenerativeAI configurada."""
        self.validate_config()
        
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_TOKENS,
            google_api_key=settings.GOOGLE_API_KEY
        )


# Registro de providers disponibles
PROVIDERS: dict[str, Type[LLMInterface]] = {
    "openai": OpenAIProvider,
    "google": GoogleProvider,
}


def get_llm() -> BaseChatModel:
    """
    Factory que retorna el LLM configurado según LLM_PROVIDER.
    
    Lee la configuración de settings y retorna la instancia
    apropiada (OpenAI o Google Gemini).
    
    Returns:
        BaseChatModel: Instancia del LLM configurado
        
    Raises:
        ValueError: Si LLM_PROVIDER no es válido
        
    Uso:
        llm = get_llm()  # Retorna OpenAI o Google según .env
        response = await llm.ainvoke("Hola!")
    """
    provider_class = PROVIDERS.get(settings.LLM_PROVIDER)
    
    if not provider_class:
        available = list(PROVIDERS.keys())
        raise ValueError(
            f"LLM_PROVIDER '{settings.LLM_PROVIDER}' no válido. "
            f"Opciones disponibles: {available}"
        )
    
    provider = provider_class()
    return provider.get_llm()


def validate_llm_config() -> BaseChatModel:
    """
    Valida configuración LLM al iniciar la aplicación.
    Imprime información de diagnóstico y retorna el LLM si es válido.
    
    Returns:
        BaseChatModel: Instancia del LLM si la configuración es válida
        
    Raises:
        ValueError: Si hay errores de configuración
    """
    print("🤖 Configurando LLM...")
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
        return llm
    except ValueError as e:
        print(f"   ❌ Error en configuración LLM: {e}")
        logger.error(f"Error configurando LLM: {e}")
        raise
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        logger.error(f"Error inesperado configurando LLM: {e}")
        raise


def get_provider_info() -> dict:
    """
    Retorna información sobre el provider LLM actual.
    Útil para endpoints de health/status.
    
    Returns:
        dict: Información del provider configurado
    """
    return {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "available_providers": list(PROVIDERS.keys())
    }


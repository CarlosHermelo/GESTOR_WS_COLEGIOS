"""
Configuración centralizada del Gestor WS.
Usa pydantic-settings para cargar variables de entorno.
"""
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""
    
    # ============== DATABASE ==============
    DATABASE_URL: str = "postgresql+asyncpg://gestor_user:gestor_pass@localhost:5432/gestor_ws"
    
    # ============== ERP ==============
    ERP_TYPE: str = "mock"
    MOCK_ERP_URL: str = "http://localhost:8001"
    
    # ============== LLM ==============
    LLM_PROVIDER: Literal["openai", "google"] = "openai"
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4000
    
    # ============== API KEYS ==============
    OPENAI_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    
    # ============== WHATSAPP ==============
    WHATSAPP_TOKEN: str = "dummy_token"
    WHATSAPP_PHONE_NUMBER_ID: str = "dummy_id"
    WHATSAPP_VERIFY_TOKEN: str = "mi_token_secreto"
    
    # ============== API ==============
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()


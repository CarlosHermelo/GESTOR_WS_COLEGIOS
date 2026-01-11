"""
Configuración del ERP Mock usando Pydantic Settings.
Carga variables de entorno de forma segura.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""
    
    # Base de datos
    database_url: str = "postgresql+asyncpg://erp_user:erp_pass@postgres:5432/erp_mock"
    
    # URL del servicio Gestor WS para webhooks
    gestor_ws_url: str = "http://host.docker.internal:8000"
    
    # Puerto de la API
    api_port: int = 8001
    
    # Configuración de webhooks
    webhook_max_retries: int = 3
    webhook_base_delay: float = 1.0  # segundos
    
    # Configuración de logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna una instancia cacheada de Settings.
    Usar lru_cache evita releer el .env en cada llamada.
    """
    return Settings()


# Instancia global para importación directa
settings = get_settings()


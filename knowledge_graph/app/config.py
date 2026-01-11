"""
Configuración del Knowledge Graph.
Comparte configuración LLM con Fase 2.
"""
from typing import Literal, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración del sistema."""
    
    # PostgreSQL (Gestor WS)
    DATABASE_URL: str = "postgresql+asyncpg://gestor_user:gestor_pass@postgres:5432/gestor_ws"
    
    # Neo4j
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password123"
    
    # ERP Mock
    MOCK_ERP_URL: str = "http://erp_mock:8000"
    
    # Gestor WS
    GESTOR_WS_URL: str = "http://gestor_ws:8000"
    
    # LLM Configuration (compartido con Fase 2)
    LLM_PROVIDER: Literal["openai", "google"] = "google"
    LLM_MODEL: str = "gemini-2.0-flash-exp"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4000
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    
    # API
    API_PORT: int = 8002
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


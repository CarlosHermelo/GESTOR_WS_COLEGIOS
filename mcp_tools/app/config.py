"""
Configuración del MCP Tools Server.
"""
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración cargada desde variables de entorno."""
    
    # ============== MODO DE OPERACIÓN ==============
    MOCK_MODE: bool = True
    
    # ============== SERVICIOS EXTERNOS ==============
    ERP_URL: str = "http://localhost:8001"
    KNOWLEDGE_GRAPH_URL: str = "http://localhost:8002"
    GESTOR_WS_URL: str = "http://localhost:8000"
    
    # ============== DATABASE ==============
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/mcp_tools.db"
    
    # ============== LLM ==============
    LLM_PROVIDER: Literal["openai", "google"] = "google"
    LLM_MODEL: str = "gemini-2.0-flash-exp"
    GOOGLE_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    
    # ============== SERVER ==============
    HOST: str = "0.0.0.0"
    PORT: int = 8003
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

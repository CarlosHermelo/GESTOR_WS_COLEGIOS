import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.config import settings

def setup_logging():
    """Configura logging estructurado para archivos y consola."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Handlers: consola + archivo
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # File handler para logs generales
    file_handler = RotatingFileHandler(
        log_dir / "gestor_ws.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(file_handler)
    
    # File handler específico para token usage (JSON)
    class TokenUsageFilter(logging.Filter):
        def filter(self, record):
            return "TOKEN_USAGE" in record.getMessage()
    
    token_handler = RotatingFileHandler(
        log_dir / "token_usage.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8"
    )
    token_handler.setFormatter(logging.Formatter(log_format))
    token_handler.addFilter(TokenUsageFilter())
    handlers.append(token_handler)
    
    # Configuración global
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        handlers=handlers,
        force=True  # Sobrescribe configuraciones previas
    )
    
    # Reducir verbosidad de librerías externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    logging.info("Logging configurado (Archivos + Consola)")

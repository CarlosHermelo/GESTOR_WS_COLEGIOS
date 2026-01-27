"""
Gestor WS - API Principal
Sistema de Gestión de Cobranza por WhatsApp
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, close_db, check_db_connection
from app.llm.factory import validate_llm_config, get_provider_info
from app.adapters.mock_erp_adapter import get_erp_client, close_erp_client
from app.services.whatsapp_service import close_whatsapp_service
from app.api import webhooks_erp_router, webhooks_whatsapp_router, admin_router


# ============== LOGGING ==============

def setup_logging():
    """Configura logging estructurado."""
    import os
    from pathlib import Path
    from logging.handlers import RotatingFileHandler
    
    log_format = (
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
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
    # Solo captura logs que contienen "TOKEN_USAGE"
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
    
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        handlers=handlers
    )
    
    # Reducir verbosidad de librerías externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


# ============== LIFESPAN ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación.
    Inicializa servicios al arrancar, los cierra al parar.
    """
    logger.info("🚀 Iniciando Gestor WS...")
    
    try:
        # 1. Validar configuración LLM
        validate_llm_config()
        
        # 2. Inicializar base de datos
        logger.info("📦 Conectando a base de datos...")
        await init_db()
        
        if await check_db_connection():
            logger.info("   ✅ Base de datos conectada")
        else:
            logger.warning("   ⚠️ No se pudo verificar conexión a BD")
        
        # 3. Verificar conexión ERP
        logger.info("🔗 Verificando conexión con ERP...")
        erp = get_erp_client()
        if await erp.health_check():
            logger.info(f"   ✅ ERP conectado ({settings.MOCK_ERP_URL})")
        else:
            logger.warning(f"   ⚠️ ERP no disponible ({settings.MOCK_ERP_URL})")
        
        logger.info("✅ Gestor WS iniciado correctamente")
        logger.info(f"📡 API disponible en puerto {settings.API_PORT}")
        
    except Exception as e:
        logger.error(f"❌ Error iniciando Gestor WS: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("🛑 Deteniendo Gestor WS...")
    
    await close_erp_client()
    await close_whatsapp_service()
    await close_db()
    
    logger.info("👋 Gestor WS detenido")


# ============== APP ==============

app = FastAPI(
    title="Gestor WS",
    description="Sistema de Gestión de Cobranza por WhatsApp",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(webhooks_erp_router)
app.include_router(webhooks_whatsapp_router)
app.include_router(admin_router)


# ============== ENDPOINTS BASE ==============

@app.get("/", include_in_schema=False)
async def root():
    """Redirecciona a documentación."""
    return {
        "service": "Gestor WS",
        "version": "2.0.0",
        "description": "Sistema de Gestión de Cobranza por WhatsApp",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """
    Health check del servicio.
    Retorna estado del sistema y configuración LLM.
    """
    # Verificar BD
    db_ok = await check_db_connection()
    
    # Verificar ERP
    erp = get_erp_client()
    erp_ok = await erp.health_check()
    
    # Info LLM
    llm_info = get_provider_info()
    
    status = "healthy" if (db_ok and erp_ok) else "degraded"
    
    return {
        "status": status,
        "service": "gestor_ws",
        "version": "2.0.0",
        "components": {
            "database": "connected" if db_ok else "disconnected",
            "erp": "connected" if erp_ok else "disconnected"
        },
        "llm": {
            "provider": llm_info["provider"],
            "model": llm_info["model"]
        },
        "config": {
            "erp_url": settings.MOCK_ERP_URL,
            "whatsapp_simulation": settings.WHATSAPP_TOKEN.startswith("dummy")
        }
    }


@app.get("/health/llm")
async def health_llm():
    """
    Health check específico del LLM.
    Útil para verificar que el provider está configurado.
    """
    try:
        from app.llm.factory import get_llm
        
        llm = get_llm()
        llm_info = get_provider_info()
        
        return {
            "status": "ok",
            "provider": llm_info["provider"],
            "model": llm_info["model"],
            "temperature": llm_info["temperature"],
            "max_tokens": llm_info["max_tokens"],
            "available_providers": llm_info["available_providers"]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_MODEL
        }


@app.get("/health/erp")
async def health_erp():
    """
    Health check específico del ERP.
    """
    try:
        erp = get_erp_client()
        is_healthy = await erp.health_check()
        
        return {
            "status": "ok" if is_healthy else "error",
            "url": settings.MOCK_ERP_URL,
            "type": settings.ERP_TYPE
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "url": settings.MOCK_ERP_URL
        }




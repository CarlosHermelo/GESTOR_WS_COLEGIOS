"""
Knowledge Graph API - Servicio de Analytics
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.neo4j_client import neo4j_client
from app.llm.factory import validate_llm_config, get_provider_info
from app.api.reportes import router as reportes_router


# ============== LOGGING ==============

def setup_logging():
    """Configura logging estructurado."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Reducir verbosidad
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


# ============== LIFESPAN ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación."""
    logger.info("🚀 Iniciando Knowledge Graph API...")
    
    try:
        # 1. Validar configuración LLM (opcional - solo warning si falla)
        try:
            validate_llm_config()
        except ValueError as e:
            logger.warning(f"⚠️ LLM no configurado: {e}")
            logger.warning("   Las funciones de enriquecimiento LLM no estarán disponibles")
            logger.warning("   Configure GOOGLE_API_KEY o OPENAI_API_KEY en .env")
        
        # 2. Conectar a Neo4j
        logger.info("📦 Conectando a Neo4j...")
        await neo4j_client.connect()
        
        if await neo4j_client.health_check():
            logger.info(f"   ✅ Neo4j conectado ({settings.NEO4J_URI})")
        else:
            logger.warning("   ⚠️ Neo4j no responde correctamente")
        
        logger.info("✅ Knowledge Graph API iniciado correctamente")
        logger.info(f"📡 API disponible en puerto {settings.API_PORT}")
        
    except Exception as e:
        logger.error(f"❌ Error iniciando Knowledge Graph API: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("🛑 Deteniendo Knowledge Graph API...")
    await neo4j_client.close()
    logger.info("👋 Knowledge Graph API detenido")


# ============== APP ==============

app = FastAPI(
    title="Knowledge Graph API",
    description="Sistema de Analytics con Neo4j para análisis predictivo de mora y deserción",
    version="1.0.0",
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
app.include_router(reportes_router)


# ============== ENDPOINTS BASE ==============

@app.get("/", include_in_schema=False)
async def root():
    """Redirecciona a documentación."""
    return {
        "service": "Knowledge Graph API",
        "version": "1.0.0",
        "description": "Sistema de Analytics con Neo4j",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """Health check del servicio."""
    neo4j_ok = await neo4j_client.health_check()
    llm_info = get_provider_info()
    
    status = "healthy" if neo4j_ok else "degraded"
    
    return {
        "status": status,
        "service": "knowledge_graph",
        "version": "1.0.0",
        "components": {
            "neo4j": "connected" if neo4j_ok else "disconnected"
        },
        "llm": {
            "provider": llm_info["provider"],
            "model": llm_info["model"]
        }
    }


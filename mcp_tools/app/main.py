"""
MCP Tools Server - FastAPI Application.
Expone herramientas via REST API y protocolo MCP.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any

from app.config import settings
from app.mcp.server import mcp_server
from app.mcp.registry import registry

# Importar tools para que se registren
from app.tools import erp_tools, admin_tools, kg_tools, notif_tools

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle del servidor."""
    logger.info("=" * 60)
    logger.info("MCP Tools Server iniciando...")
    logger.info(f"Modo MOCK: {settings.MOCK_MODE}")
    logger.info(f"Tools registradas: {len(registry.list_tools())}")
    
    # Listar tools por categoría
    for cat in ["erp", "admin", "kg", "notif"]:
        tools = registry.list_tools(category=cat)
        if tools:
            logger.info(f"  [{cat}]: {[t.name for t in tools]}")
    
    # Configurar modo mock
    mcp_server.set_mock_mode(settings.MOCK_MODE)
    
    logger.info("=" * 60)
    
    yield
    
    logger.info("MCP Tools Server detenido")


app = FastAPI(
    title="MCP Tools Server",
    description="Servidor de herramientas centralizado para agentes LLM",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MODELOS
# ============================================================

class MCPRequest(BaseModel):
    """Request MCP JSON-RPC."""
    jsonrpc: str = "2.0"
    method: str
    params: dict = {}
    id: Optional[str] = None


class ToolCallRequest(BaseModel):
    """Request simplificada para llamar una tool."""
    name: str
    arguments: dict = {}


class ToolResponse(BaseModel):
    """Response de una tool."""
    success: bool
    data: Any = None
    error: Optional[str] = None


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mcp_tools",
        "mock_mode": settings.MOCK_MODE,
        "tools_count": len(registry.list_tools())
    }


@app.get("/tools")
async def list_tools(category: Optional[str] = None):
    """Lista todas las herramientas disponibles."""
    tools = registry.list_tools(category=category)
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "parameters": t.parameters
            }
            for t in tools
        ],
        "count": len(tools)
    }


@app.get("/tools/{tool_name}")
async def get_tool_schema(tool_name: str):
    """Obtiene el schema de una herramienta específica."""
    tool = registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    return {
        "name": tool.name,
        "description": tool.description,
        "category": tool.category,
        "parameters": tool.parameters
    }


@app.post("/tools/{tool_name}/call", response_model=ToolResponse)
async def call_tool(tool_name: str, request: ToolCallRequest):
    """Ejecuta una herramienta directamente."""
    if request.name != tool_name:
        request.name = tool_name
    
    result = await registry.call_tool(
        name=tool_name,
        arguments=request.arguments,
        use_mock=settings.MOCK_MODE
    )
    
    return ToolResponse(**result)


@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """
    Endpoint MCP JSON-RPC.
    
    Métodos soportados:
    - tools/list: Lista herramientas
    - tools/call: Ejecuta herramienta
    - tools/schema: Obtiene schema
    - ping: Health check
    """
    response = await mcp_server.handle_request(request.model_dump())
    return response


# ============================================================
# ENDPOINTS DE TESTING
# ============================================================

@app.post("/test/mock/{enabled}")
async def set_mock_mode(enabled: bool):
    """Activa/desactiva modo mock para testing."""
    mcp_server.set_mock_mode(enabled)
    return {"mock_mode": enabled}


@app.get("/test/categories")
async def list_categories():
    """Lista las categorías de tools disponibles."""
    tools = registry.list_tools()
    categories = list(set(t.category for t in tools))
    return {"categories": categories}


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )

"""
MCP Client - Cliente para conectarse al MCP Tools Server.
Permite que el agente autónomo use las tools de forma dinámica.
"""
import logging
from typing import Optional, Any
from dataclasses import dataclass
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ToolSchema:
    """Schema de una herramienta MCP."""
    name: str
    description: str
    parameters: dict
    category: str


@dataclass
class ToolResult:
    """Resultado de ejecutar una herramienta."""
    success: bool
    data: Any
    error: Optional[str] = None


class MCPClient:
    """
    Cliente para comunicarse con el MCP Tools Server.
    
    Uso:
        client = MCPClient()
        
        # Listar tools disponibles
        tools = await client.list_tools()
        
        # Ejecutar una tool
        result = await client.call_tool("consultar_estado_cuenta", {"whatsapp": "+54..."})
    """
    
    def __init__(
        self,
        base_url: str = None,
        timeout: float = 30.0,
        mock_mode: bool = None
    ):
        """
        Inicializa el cliente MCP.
        
        Args:
            base_url: URL del MCP server. Si no se especifica, usa MCP_TOOLS_URL de settings.
            timeout: Timeout para requests.
            mock_mode: Si usar modo local mock (sin conectar al servidor).
        """
        self.base_url = (base_url or getattr(settings, 'MCP_TOOLS_URL', 'http://localhost:8003')).rstrip("/")
        self.timeout = timeout
        self.mock_mode = mock_mode if mock_mode is not None else getattr(settings, 'MOCK_MODE', True)
        self._client: Optional[httpx.AsyncClient] = None
        self._tools_cache: Optional[list[ToolSchema]] = None
        
        logger.info(f"MCPClient inicializado - URL: {self.base_url}, Mock: {self.mock_mode}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea el cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client
    
    async def close(self):
        """Cierra el cliente."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def ping(self) -> bool:
        """Verifica si el servidor está disponible."""
        try:
            client = await self._get_client()
            response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "method": "ping",
                "params": {},
                "id": "ping"
            })
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"MCP Server no disponible: {e}")
            return False
    
    async def list_tools(self, category: str = None, force_refresh: bool = False) -> list[ToolSchema]:
        """
        Lista las herramientas disponibles.
        
        Args:
            category: Filtrar por categoría (erp, admin, kg, notif)
            force_refresh: Forzar recarga del cache
        
        Returns:
            Lista de ToolSchema con las herramientas disponibles
        """
        if self._tools_cache and not force_refresh and not category:
            return self._tools_cache
        
        try:
            client = await self._get_client()
            params = {}
            if category:
                params["category"] = category
            
            response = await client.get("/tools", params=params)
            response.raise_for_status()
            
            data = response.json()
            tools = [
                ToolSchema(
                    name=t["name"],
                    description=t["description"],
                    parameters=t["parameters"],
                    category=t["category"]
                )
                for t in data.get("tools", [])
            ]
            
            if not category:
                self._tools_cache = tools
            
            logger.info(f"Tools cargadas desde MCP: {len(tools)}")
            return tools
            
        except Exception as e:
            logger.error(f"Error listando tools: {e}")
            return []
    
    async def get_tool_schema(self, name: str) -> Optional[ToolSchema]:
        """
        Obtiene el schema de una herramienta específica.
        
        Args:
            name: Nombre de la tool
        
        Returns:
            ToolSchema o None si no existe
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/tools/{name}")
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            data = response.json()
            
            return ToolSchema(
                name=data["name"],
                description=data["description"],
                parameters=data["parameters"],
                category=data["category"]
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo schema de {name}: {e}")
            return None
    
    async def call_tool(self, name: str, arguments: dict = None) -> ToolResult:
        """
        Ejecuta una herramienta.
        
        Args:
            name: Nombre de la tool a ejecutar
            arguments: Argumentos para la tool
        
        Returns:
            ToolResult con el resultado
        """
        arguments = arguments or {}
        
        try:
            client = await self._get_client()
            response = await client.post(f"/tools/{name}/call", json={
                "name": name,
                "arguments": arguments
            })
            response.raise_for_status()
            
            data = response.json()
            
            return ToolResult(
                success=data.get("success", False),
                data=data.get("data"),
                error=data.get("error")
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error llamando tool {name}: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Error llamando tool {name}: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
    
    async def call_tool_mcp(self, name: str, arguments: dict = None) -> ToolResult:
        """
        Ejecuta una herramienta usando el protocolo MCP JSON-RPC.
        
        Args:
            name: Nombre de la tool
            arguments: Argumentos
        
        Returns:
            ToolResult
        """
        arguments = arguments or {}
        
        try:
            client = await self._get_client()
            response = await client.post("/mcp", json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments
                },
                "id": f"call-{name}"
            })
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                return ToolResult(
                    success=False,
                    data=None,
                    error=data["error"].get("message", "Unknown error")
                )
            
            result = data.get("result", {})
            return ToolResult(
                success=result.get("success", False),
                data=result.get("data"),
                error=result.get("error")
            )
            
        except Exception as e:
            logger.error(f"Error MCP llamando tool {name}: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
    
    def get_tools_for_llm(self, tools: list[ToolSchema] = None) -> list[dict]:
        """
        Convierte las tools al formato esperado por LLM (OpenAI/Langchain).
        
        Args:
            tools: Lista de tools. Si no se especifica, usa el cache.
        
        Returns:
            Lista de dicts en formato OpenAI function calling
        """
        tools = tools or self._tools_cache or []
        
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters
                }
            }
            for t in tools
        ]


# Singleton global
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Obtiene el cliente MCP singleton."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def call_mcp_tool(name: str, arguments: dict = None) -> ToolResult:
    """
    Función de conveniencia para llamar una tool.
    
    Args:
        name: Nombre de la tool
        arguments: Argumentos
    
    Returns:
        ToolResult
    """
    client = get_mcp_client()
    return await client.call_tool(name, arguments)

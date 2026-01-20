"""
MCP Server - Implementación del protocolo MCP sobre HTTP.
"""
import logging
from typing import Optional, Any
from dataclasses import dataclass

from app.mcp.registry import ToolRegistry, registry

logger = logging.getLogger(__name__)


@dataclass
class MCPRequest:
    """Request MCP estándar."""
    jsonrpc: str = "2.0"
    method: str = ""
    params: dict = None
    id: Optional[str] = None


@dataclass 
class MCPResponse:
    """Response MCP estándar."""
    jsonrpc: str = "2.0"
    result: Any = None
    error: Optional[dict] = None
    id: Optional[str] = None
    
    def to_dict(self) -> dict:
        response = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        if self.error:
            response["error"] = self.error
        else:
            response["result"] = self.result
        return response


class MCPServer:
    """
    Servidor MCP que expone herramientas via JSON-RPC.
    
    Métodos soportados:
    - tools/list: Lista todas las herramientas disponibles
    - tools/call: Ejecuta una herramienta
    - tools/schema: Obtiene el schema de una herramienta
    """
    
    def __init__(self, registry: ToolRegistry = None):
        self.registry = registry or ToolRegistry()
        self.use_mock = False
        logger.info("MCPServer inicializado")
    
    def set_mock_mode(self, enabled: bool):
        """Activa/desactiva modo mock."""
        self.use_mock = enabled
        logger.info(f"Modo mock: {'activado' if enabled else 'desactivado'}")
    
    async def handle_request(self, request: dict) -> dict:
        """
        Procesa una request MCP.
        
        Args:
            request: Request JSON-RPC
            
        Returns:
            dict: Response JSON-RPC
        """
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "tools/list":
                result = await self._handle_list_tools(params)
            elif method == "tools/call":
                result = await self._handle_call_tool(params)
            elif method == "tools/schema":
                result = await self._handle_get_schema(params)
            elif method == "ping":
                result = {"status": "pong"}
            else:
                return MCPResponse(
                    error={"code": -32601, "message": f"Method not found: {method}"},
                    id=request_id
                ).to_dict()
            
            return MCPResponse(result=result, id=request_id).to_dict()
            
        except Exception as e:
            logger.error(f"Error procesando request: {e}")
            return MCPResponse(
                error={"code": -32603, "message": str(e)},
                id=request_id
            ).to_dict()
    
    async def _handle_list_tools(self, params: dict) -> dict:
        """Lista todas las herramientas."""
        category = params.get("category")
        tools = self.registry.list_tools(category=category)
        
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
    
    async def _handle_call_tool(self, params: dict) -> dict:
        """Ejecuta una herramienta."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return {
                "success": False,
                "error": "Tool name required",
                "data": None
            }
        
        result = await self.registry.call_tool(
            name=tool_name,
            arguments=arguments,
            use_mock=self.use_mock
        )
        
        return result
    
    async def _handle_get_schema(self, params: dict) -> dict:
        """Obtiene el schema de una herramienta."""
        tool_name = params.get("name")
        
        if tool_name:
            tool = self.registry.get_tool(tool_name)
            if not tool:
                return {"error": f"Tool '{tool_name}' not found"}
            
            return {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "category": tool.category
            }
        
        # Si no se especifica nombre, retornar todos los schemas
        return {
            "schemas": self.registry.get_tools_schema()
        }


# Instancia global del servidor
mcp_server = MCPServer(registry)

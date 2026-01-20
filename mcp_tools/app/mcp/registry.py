"""
Tool Registry - Registro centralizado de herramientas MCP.
"""
import logging
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from functools import wraps
import inspect

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definición de una herramienta MCP."""
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable
    category: str = "general"
    requires_auth: bool = False
    mock_response: Optional[dict] = None


class ToolRegistry:
    """
    Registro global de herramientas MCP.
    
    Uso:
        registry = ToolRegistry()
        
        @registry.tool(category="erp")
        async def consultar_estado_cuenta(whatsapp: str) -> dict:
            '''Consulta estado de cuenta del responsable.'''
            ...
    """
    
    _instance: Optional["ToolRegistry"] = None
    _tools: dict[str, ToolDefinition] = {}
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance
    
    def tool(
        self,
        name: Optional[str] = None,
        category: str = "general",
        requires_auth: bool = False,
        mock_response: Optional[dict] = None
    ) -> Callable:
        """
        Decorador para registrar una herramienta.
        
        Args:
            name: Nombre de la tool (usa el nombre de la función si no se especifica)
            category: Categoría (erp, admin, kg, notif)
            requires_auth: Si requiere autenticación
            mock_response: Respuesta mock para testing
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            
            # Extraer parámetros del signature
            sig = inspect.signature(func)
            parameters = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                
                param_type = "string"  # Default
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == float:
                        param_type = "number"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif param.annotation == dict:
                        param_type = "object"
                    elif param.annotation == list:
                        param_type = "array"
                
                parameters["properties"][param_name] = {"type": param_type}
                
                if param.default == inspect.Parameter.empty:
                    parameters["required"].append(param_name)
            
            # Crear definición
            tool_def = ToolDefinition(
                name=tool_name,
                description=func.__doc__ or f"Tool: {tool_name}",
                parameters=parameters,
                handler=func,
                category=category,
                requires_auth=requires_auth,
                mock_response=mock_response
            )
            
            self._tools[tool_name] = tool_def
            logger.info(f"Tool registrada: {tool_name} (categoria: {category})")
            
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            
            return wrapper
        
        return decorator
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Obtiene una herramienta por nombre."""
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> list[ToolDefinition]:
        """Lista todas las herramientas, opcionalmente filtradas por categoría."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools
    
    def get_tools_schema(self) -> list[dict]:
        """Retorna el schema de todas las tools en formato MCP/OpenAI."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "category": t.category
            }
            for t in self._tools.values()
        ]
    
    async def call_tool(
        self,
        name: str,
        arguments: dict,
        use_mock: bool = False
    ) -> dict:
        """
        Ejecuta una herramienta.
        
        Args:
            name: Nombre de la tool
            arguments: Argumentos para la tool
            use_mock: Si usar respuesta mock
            
        Returns:
            dict: Resultado de la tool
        """
        tool_def = self.get_tool(name)
        
        if not tool_def:
            return {
                "success": False,
                "error": f"Tool '{name}' no encontrada",
                "data": None
            }
        
        # Usar mock si está habilitado y disponible
        if use_mock and tool_def.mock_response:
            logger.info(f"[MOCK] Ejecutando tool: {name}")
            return {
                "success": True,
                "error": None,
                "data": tool_def.mock_response
            }
        
        try:
            logger.info(f"Ejecutando tool: {name} con args: {arguments}")
            result = await tool_def.handler(**arguments)
            
            return {
                "success": True,
                "error": None,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando tool {name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }


# Singleton global
registry = ToolRegistry()

# Decorador conveniente
def tool(
    name: Optional[str] = None,
    category: str = "general",
    requires_auth: bool = False,
    mock_response: Optional[dict] = None
) -> Callable:
    """Decorador global para registrar tools."""
    return registry.tool(
        name=name,
        category=category,
        requires_auth=requires_auth,
        mock_response=mock_response
    )

"""
Tools disponibles para el MCP Server.
Cada módulo registra sus tools automáticamente al importarse.
"""
from app.tools import erp_tools
from app.tools import admin_tools
from app.tools import kg_tools
from app.tools import notif_tools

__all__ = ["erp_tools", "admin_tools", "kg_tools", "notif_tools"]

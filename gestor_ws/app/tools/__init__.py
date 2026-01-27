"""
Herramientas para agentes LLM.
"""
from app.tools.consultar_erp import get_erp_tools
from app.tools.tickets import get_ticket_tools
from app.tools.notificaciones import get_notification_tools

__all__ = [
    "get_erp_tools",
    "get_ticket_tools",
    "get_notification_tools"
]




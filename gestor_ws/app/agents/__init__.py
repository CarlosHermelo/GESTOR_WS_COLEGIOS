"""
Módulo de Agentes para procesamiento de mensajes.

Arquitectura de 3 capas:
1. Router: Clasificación por keywords (sin LLM)
2. Asistente: Consultas simples con LLM + herramientas
3. Coordinador: Casos complejos con LangGraph
"""
from app.agents.router import MessageRouter, RouteType
from app.agents.asistente import AsistenteVirtual
from app.agents.coordinador import AgenteAutonomo

__all__ = [
    "MessageRouter",
    "RouteType",
    "AsistenteVirtual",
    "AgenteAutonomo"
]


"""
Módulo de Agentes para procesamiento de mensajes.

ARQUITECTURA CODE PLANNER:
- El LLM genera código Python que invoca herramientas MCP
- Flujo: Planner → Executor → Reflector → Responder
"""
from app.agents.agente_autonomo import (
    AgenteAutonomo,
    get_agente_autonomo
)
from app.agents.states import (
    CodePlannerState,
    AgentState,  # Alias
    create_empty_code_planner_state,
    create_empty_agent_state  # Alias
)

__all__ = [
    "AgenteAutonomo",
    "get_agente_autonomo",
    "CodePlannerState",
    "AgentState",
    "create_empty_code_planner_state",
    "create_empty_agent_state"
]

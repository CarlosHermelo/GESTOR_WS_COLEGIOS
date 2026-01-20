"""
Módulo de Agentes para procesamiento de mensajes.

NUEVA ARQUITECTURA (agente_autonomo.py):
- Agente Jerárquico de 2 capas con Planning JSON
- Manager Jefe → Especialistas (Financiero, Administrativo, Institucional)
- Dynamic Replanning y Checkpointing para HITL

LEGACY (deprecado, importar directamente si se necesita):
- router.py, asistente.py, coordinador.py
"""
# Nueva arquitectura jerárquica
from app.agents.agente_autonomo import (
    AgenteAutonomo,
    get_agente_autonomo
)
from app.agents.states import (
    AgentState,
    MasterPlan,
    SpecialistReport,
    SpecialistType,
    IntentType
)

__all__ = [
    # Nueva arquitectura
    "AgenteAutonomo",
    "get_agente_autonomo",
    "AgentState",
    "MasterPlan",
    "SpecialistReport",
    "SpecialistType",
    "IntentType",
]




"""
Especialistas del Agente Autónomo.
Subgrafos modulares para tareas específicas.
"""
from app.agents.specialists.financiero import FinancieroSubgraph
from app.agents.specialists.administrativo import AdministrativoSubgraph
from app.agents.specialists.institucional import InstitucionalSubgraph

__all__ = [
    "FinancieroSubgraph",
    "AdministrativoSubgraph",
    "InstitucionalSubgraph",
]

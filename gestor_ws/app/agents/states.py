"""
Estados y Contratos para el Agente Autónomo (Code Planner).
Define la estructura de datos que fluye a través del grafo.
"""
from typing import TypedDict, Optional, Any


class CodePlannerState(TypedDict):
    """
    Estado global del Code Planner Agent.
    """
    # Entrada
    phone_number: str
    mensaje_original: str
    user_context: Optional[dict]
    
    # Código generado por el Planner
    generated_code: str
    code_reasoning: str
    
    # Ejecución
    execution_result: Optional[Any]
    execution_error: Optional[str]
    correction_count: int
    max_corrections: int
    
    # Iteraciones del Planner (para evitar loops infinitos)
    planner_iterations: int
    
    # Reflexión
    reflection_valid: bool
    reflection_reason: str
    
    # Resultado Final
    final_response: Optional[str]
    
    # Memoria
    memory_context: dict
    
    # Control de errores globales
    error: Optional[str]
    
    # Métricas de ejecución por nodo
    metrics: dict  # { "planner": {"latency": 1.2, "tokens": 1500}, ... }


# Alias para compatibilidad
AgentState = CodePlannerState


def create_empty_code_planner_state(
    phone_number: str,
    mensaje: str,
    user_context: Optional[dict] = None
) -> CodePlannerState:
    """Crea un estado inicial para el Code Planner."""
    return CodePlannerState(
        phone_number=phone_number,
        mensaje_original=mensaje,
        user_context=user_context,
        generated_code="",
        code_reasoning="",
        execution_result=None,
        execution_error=None,
        correction_count=0,
        max_corrections=3,
        planner_iterations=0,
        reflection_valid=False,
        reflection_reason="",
        final_response=None,
        memory_context={},
        error=None,
        metrics={}
    )


# Alias para compatibilidad
def create_empty_agent_state(
    phone_number: str,
    mensaje: str,
    user_context: Optional[dict] = None
) -> CodePlannerState:
    """Alias para create_empty_code_planner_state."""
    return create_empty_code_planner_state(phone_number, mensaje, user_context)

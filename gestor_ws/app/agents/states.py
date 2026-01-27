"""
Estados y Contratos JSON para el Agente Autónomo Jerárquico.
Define las estructuras de datos que fluyen entre Manager y Especialistas.
"""
from typing import TypedDict, Optional, Literal, Any
from enum import Enum


class SpecialistType(str, Enum):
    """Tipos de especialistas disponibles."""
    FINANCIERO = "financiero"
    ADMINISTRATIVO = "administrativo"
    INSTITUCIONAL = "institucional"


class IntentType(str, Enum):
    """Intenciones detectadas en la consulta."""
    CONSULTA_FINANCIERA = "consulta_financiera"
    SOLICITUD_PAGO = "solicitud_pago"
    CONFIRMACION_PAGO = "confirmacion_pago"
    RECLAMO = "reclamo"
    SOLICITUD_BAJA = "solicitud_baja"
    PLAN_PAGO = "plan_pago"
    CONSULTA_INSTITUCIONAL = "consulta_institucional"
    SALUDO = "saludo"
    OTRO = "otro"


# ============================================================
# CONTRATOS JSON - Comunicación entre capas
# ============================================================

class StepPlan(TypedDict):
    """Un paso individual en el MasterPlan."""
    specialist: str  # SpecialistType value
    goal: str        # Descripción de la meta
    params: dict     # Parámetros específicos para el especialista
    priority: int    # Orden de ejecución (menor = primero)


class MasterPlan(TypedDict):
    """
    Plan maestro generado por el Manager Jefe.
    Define la estrategia de alto nivel para resolver la consulta.
    """
    intent: str                     # IntentType value
    confidence: float               # 0.0 - 1.0
    steps: list[StepPlan]           # Pasos a ejecutar
    requires_hitl: bool             # Requiere aprobación humana
    reasoning: str                  # Explicación del plan


class ActionPlan(TypedDict):
    """Una acción específica en el SubPlan."""
    tool: str           # Nombre de la herramienta
    params: dict        # Parámetros para la herramienta
    description: str    # Descripción de la acción


class SubPlan(TypedDict):
    """
    Plan táctico generado por un Especialista.
    Detalla las acciones técnicas a ejecutar.
    """
    specialist: str             # SpecialistType value
    goal_received: str          # Meta recibida del Manager
    actions: list[ActionPlan]   # Acciones a ejecutar
    reasoning: str              # Explicación del sub-plan


class SpecialistReport(TypedDict):
    """
    Reporte generado por un Especialista tras ejecutar su SubPlan.
    Se envía de vuelta al grafo principal.
    """
    specialist: str         # SpecialistType value
    success: bool           # Si logró cumplir la meta
    data: dict              # Datos obtenidos/generados
    summary: str            # Resumen en lenguaje natural
    error: Optional[str]    # Mensaje de error si falló
    requires_replan: bool   # Si necesita que el Manager replanifique


# ============================================================
# ESTADO DEL AGENTE - Grafo Principal
# ============================================================

class AgentState(TypedDict):
    """
    Estado global del Agente Autónomo.
    Fluye a través del grafo principal.
    """
    # Entrada
    phone_number: str
    mensaje_original: str
    
    # Contexto del usuario (del ERP)
    user_context: Optional[dict]
    
    # Plan estratégico
    master_plan: Optional[MasterPlan]
    
    # Ejecución
    current_step_index: int
    specialist_reports: list[SpecialistReport]
    
    # Control de flujo
    needs_replan: bool
    replan_count: int
    max_replans: int
    
    # Resultado
    final_response: Optional[str]
    
    # Memoria
    memory_context: dict
    
    # Errores
    error: Optional[str]


# ============================================================
# ESTADO DEL ESPECIALISTA - Subgrafos
# ============================================================

class SpecialistState(TypedDict):
    """
    Estado interno de un Especialista (subgrafo).
    """
    # Del grafo principal
    phone_number: str
    goal: str
    params: dict
    user_context: Optional[dict]
    
    # Plan táctico
    sub_plan: Optional[SubPlan]
    
    # Ejecución
    current_action_index: int
    action_results: list[dict]
    
    # Resultado
    report: Optional[SpecialistReport]
    
    # Error handling
    error: Optional[str]


# ============================================================
# ESTADO DEL CODE PLANNER - Nueva arquitectura
# ============================================================

class CodePlannerState(TypedDict):
    """
    Estado para el agente Code Planner.
    El LLM genera código Python que invoca herramientas MCP.
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
    
    # Resultado
    final_response: Optional[str]
    
    # Memoria
    memory_context: dict
    
    # Control
    error: Optional[str]


# ============================================================
# FUNCIONES HELPER
# ============================================================

def create_empty_agent_state(
    phone_number: str,
    mensaje: str
) -> AgentState:
    """Crea un estado inicial vacío para el agente."""
    return AgentState(
        phone_number=phone_number,
        mensaje_original=mensaje,
        user_context=None,
        master_plan=None,
        current_step_index=0,
        specialist_reports=[],
        needs_replan=False,
        replan_count=0,
        max_replans=3,
        final_response=None,
        memory_context={},
        error=None
    )


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
        error=None
    )


def create_empty_specialist_state(
    phone_number: str,
    goal: str,
    params: dict,
    user_context: Optional[dict] = None
) -> SpecialistState:
    """Crea un estado inicial para un especialista."""
    return SpecialistState(
        phone_number=phone_number,
        goal=goal,
        params=params,
        user_context=user_context,
        sub_plan=None,
        current_action_index=0,
        action_results=[],
        report=None,
        error=None
    )


def create_specialist_report(
    specialist: str,
    success: bool,
    data: dict,
    summary: str,
    error: Optional[str] = None,
    requires_replan: bool = False
) -> SpecialistReport:
    """Factory para crear reportes de especialistas."""
    return SpecialistReport(
        specialist=specialist,
        success=success,
        data=data,
        summary=summary,
        error=error,
        requires_replan=requires_replan
    )


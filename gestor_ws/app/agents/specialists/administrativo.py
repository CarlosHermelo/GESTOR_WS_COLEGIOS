"""
Especialista Administrativo - Subgrafo para escalamientos y tickets.
Maneja: reclamos, solicitudes de baja, planes de pago, consultas complejas.
"""
import json
import logging
from typing import Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from app.llm.factory import get_llm
from app.agents.states import (
    SpecialistState,
    SpecialistReport,
    SubPlan,
    ActionPlan,
    SpecialistType,
    create_specialist_report,
)


logger = logging.getLogger(__name__)


class AdministrativoSubgraph:
    """
    Subgrafo del Especialista Administrativo.
    
    Responsabilidades:
    - Crear tickets de escalamiento
    - Gestionar reclamos
    - Procesar solicitudes de baja
    - Solicitar planes de pago
    - Consultas que requieren intervención humana
    """
    
    # Categorías de tickets soportadas
    CATEGORIAS = {
        "plan_pago": "Solicitud de plan de pagos",
        "reclamo": "Reclamo o queja",
        "baja": "Solicitud de baja",
        "consulta_admin": "Consulta administrativa general",
        "info_autoridades": "Solicitud de información de autoridades"
    }
    
    def __init__(self):
        """Inicializa el especialista administrativo."""
        self.llm = get_llm()
        self.graph = self._build_graph()
        
        logger.info("AdministrativoSubgraph inicializado")
    
    def _build_graph(self) -> StateGraph:
        """Construye el subgrafo del especialista."""
        workflow = StateGraph(SpecialistState)
        
        # Nodos
        workflow.add_node("planificar", self._planificar)
        workflow.add_node("ejecutar_accion", self._ejecutar_accion)
        workflow.add_node("generar_reporte", self._generar_reporte)
        
        # Punto de entrada
        workflow.set_entry_point("planificar")
        
        # Edges
        workflow.add_edge("planificar", "ejecutar_accion")
        workflow.add_conditional_edges(
            "ejecutar_accion",
            self._hay_mas_acciones,
            {
                "continuar": "ejecutar_accion",
                "finalizar": "generar_reporte"
            }
        )
        workflow.add_edge("generar_reporte", END)
        
        return workflow.compile()
    
    async def _planificar(self, state: SpecialistState) -> SpecialistState:
        """
        Genera el SubPlan táctico basado en la meta recibida.
        """
        goal = state["goal"]
        params = state.get("params", {})
        
        prompt = f"""Eres el Especialista Administrativo de un colegio.
Tu tarea es planificar cómo resolver esta meta:

META: {goal}
PARÁMETROS: {json.dumps(params, ensure_ascii=False)}

Herramientas disponibles:
1. crear_ticket - Crea un ticket de escalamiento para atención humana
   Categorías: plan_pago, reclamo, baja, consulta_admin, info_autoridades
2. buscar_ticket - Busca información de un ticket existente
3. clasificar_prioridad - Determina la prioridad del caso (baja, media, alta)

Responde SOLO con JSON válido (sin markdown):
{{
    "actions": [
        {{"tool": "nombre_herramienta", "params": {{}}, "description": "qué hace"}}
    ],
    "reasoning": "por qué elegiste estas acciones"
}}
"""
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = self._clean_json_response(response.content)
            plan_data = json.loads(content)
            
            state["sub_plan"] = SubPlan(
                specialist=SpecialistType.ADMINISTRATIVO.value,
                goal_received=goal,
                actions=plan_data.get("actions", []),
                reasoning=plan_data.get("reasoning", "")
            )
            state["current_action_index"] = 0
            
            logger.info(f"SubPlan administrativo: {len(plan_data.get('actions', []))} acciones")
            
        except Exception as e:
            logger.error(f"Error planificando: {e}")
            # Plan por defecto: crear ticket de consulta
            categoria = params.get("categoria", "consulta_admin")
            state["sub_plan"] = SubPlan(
                specialist=SpecialistType.ADMINISTRATIVO.value,
                goal_received=goal,
                actions=[
                    ActionPlan(
                        tool="crear_ticket",
                        params={
                            "categoria": categoria,
                            "motivo": goal,
                            "prioridad": "media"
                        },
                        description=f"Crear ticket de {categoria}"
                    )
                ],
                reasoning="Plan por defecto ante error de planificación"
            )
            state["current_action_index"] = 0
        
        return state
    
    async def _ejecutar_accion(self, state: SpecialistState) -> SpecialistState:
        """
        Ejecuta la acción actual del SubPlan.
        """
        sub_plan = state.get("sub_plan")
        if not sub_plan or not sub_plan.get("actions"):
            state["error"] = "No hay acciones para ejecutar"
            return state
        
        idx = state["current_action_index"]
        actions = sub_plan["actions"]
        
        if idx >= len(actions):
            return state
        
        action = actions[idx]
        tool_name = action.get("tool", "")
        params = action.get("params", {})
        
        logger.info(f"Ejecutando acción {idx + 1}/{len(actions)}: {tool_name}")
        
        result = {"tool": tool_name, "success": False, "data": None, "error": None}
        
        try:
            if tool_name == "crear_ticket":
                result["data"] = await self._tool_crear_ticket(
                    phone_number=state["phone_number"],
                    categoria=params.get("categoria", "consulta_admin"),
                    motivo=params.get("motivo", state["goal"]),
                    prioridad=params.get("prioridad", "media"),
                    user_context=state.get("user_context")
                )
                result["success"] = True
                
            elif tool_name == "buscar_ticket":
                result["data"] = await self._tool_buscar_ticket(
                    params.get("ticket_id", "")
                )
                result["success"] = True
                
            elif tool_name == "clasificar_prioridad":
                result["data"] = await self._tool_clasificar_prioridad(
                    params.get("motivo", state["goal"])
                )
                result["success"] = True
            else:
                result["error"] = f"Herramienta desconocida: {tool_name}"
                
        except Exception as e:
            logger.error(f"Error ejecutando {tool_name}: {e}")
            result["error"] = str(e)
        
        # Guardar resultado
        if "action_results" not in state or state["action_results"] is None:
            state["action_results"] = []
        state["action_results"].append(result)
        
        # Avanzar índice
        state["current_action_index"] = idx + 1
        
        return state
    
    def _hay_mas_acciones(self, state: SpecialistState) -> str:
        """Decide si hay más acciones por ejecutar."""
        sub_plan = state.get("sub_plan")
        if not sub_plan or not sub_plan.get("actions"):
            return "finalizar"
        
        idx = state["current_action_index"]
        total = len(sub_plan["actions"])
        
        if idx < total:
            return "continuar"
        return "finalizar"
    
    async def _generar_reporte(self, state: SpecialistState) -> SpecialistState:
        """
        Genera el SpecialistReport final.
        """
        action_results = state.get("action_results", [])
        
        # Verificar si todas las acciones fueron exitosas
        all_success = all(r.get("success", False) for r in action_results)
        
        # Combinar datos
        combined_data = {}
        for r in action_results:
            if r.get("data"):
                combined_data[r["tool"]] = r["data"]
        
        # Generar resumen
        if all_success and combined_data:
            summary = self._format_admin_summary(combined_data, state["goal"])
            error = None
        else:
            summary = "No se pudo completar la gestión administrativa."
            errors = [r.get("error") for r in action_results if r.get("error")]
            error = "; ".join(errors) if errors else "Error desconocido"
        
        state["report"] = create_specialist_report(
            specialist=SpecialistType.ADMINISTRATIVO.value,
            success=all_success,
            data=combined_data,
            summary=summary,
            error=error,
            requires_replan=not all_success
        )
        
        return state
    
    # ============================================================
    # HERRAMIENTAS (Tools)
    # ============================================================
    
    async def _tool_crear_ticket(
        self,
        phone_number: str,
        categoria: str,
        motivo: str,
        prioridad: str = "media",
        user_context: Optional[dict] = None
    ) -> dict:
        """Crea un ticket de escalamiento."""
        import uuid
        from app.config import settings
        
        # MODO MOCK: Simular ticket sin BD
        if settings.MOCK_MODE:
            ticket_id = str(uuid.uuid4())
            logger.info(f"[MOCK] Ticket creado: {ticket_id}")
            
            return {
                "created": True,
                "ticket_id": ticket_id,
                "categoria": categoria,
                "prioridad": prioridad,
                "mensaje": self._get_mensaje_ticket(categoria, ticket_id[:8])
            }
        
        # MODO REAL: Usar BD PostgreSQL
        from app.models.tickets import Ticket
        from app.database import async_session_maker
        
        try:
            # Extraer IDs del contexto si existen
            erp_alumno_id = "desconocido"
            erp_responsable_id = None
            
            if user_context:
                if user_context.get("alumnos"):
                    erp_alumno_id = user_context["alumnos"][0].get("id", "desconocido")
                erp_responsable_id = user_context.get("responsable_id")
            
            async with async_session_maker() as session:
                ticket = Ticket.crear(
                    erp_alumno_id=erp_alumno_id,
                    erp_responsable_id=erp_responsable_id,
                    categoria=categoria,
                    motivo=motivo,
                    contexto={
                        "phone_number": phone_number,
                        "origen": "agente_autonomo",
                        "timestamp": datetime.now().isoformat()
                    },
                    prioridad=prioridad
                )
                
                session.add(ticket)
                await session.commit()
                await session.refresh(ticket)
                
                ticket_id = str(ticket.id)
                
                logger.info(f"Ticket creado: {ticket_id}")
                
                return {
                    "created": True,
                    "ticket_id": ticket_id,
                    "categoria": categoria,
                    "prioridad": prioridad,
                    "mensaje": self._get_mensaje_ticket(categoria, ticket_id[:8])
                }
                
        except Exception as e:
            logger.error(f"Error creando ticket: {e}")
            return {
                "created": False,
                "error": str(e)
            }
    
    async def _tool_buscar_ticket(self, ticket_id: str) -> dict:
        """Busca información de un ticket existente."""
        from sqlalchemy import select
        from uuid import UUID
        from app.models.tickets import Ticket
        from app.database import async_session_maker
        
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Ticket).where(Ticket.id == UUID(ticket_id))
                )
                ticket = result.scalar_one_or_none()
                
                if not ticket:
                    return {"found": False, "message": "Ticket no encontrado"}
                
                return {
                    "found": True,
                    "ticket_id": str(ticket.id),
                    "categoria": ticket.categoria,
                    "estado": ticket.estado,
                    "prioridad": ticket.prioridad,
                    "motivo": ticket.motivo,
                    "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                    "respuesta_admin": ticket.respuesta_admin
                }
                
        except Exception as e:
            logger.error(f"Error buscando ticket: {e}")
            return {"found": False, "error": str(e)}
    
    async def _tool_clasificar_prioridad(self, motivo: str) -> dict:
        """Clasifica la prioridad de un caso usando LLM."""
        prompt = f"""Clasifica la prioridad de este caso:

MOTIVO: {motivo}

Prioridades:
- baja: Consultas generales, sin urgencia
- media: Solicitudes normales, tiempo razonable
- alta: Urgencias, reclamos graves, temas legales

Responde SOLO con JSON: {{"prioridad": "baja|media|alta", "razon": "breve explicación"}}
"""
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = self._clean_json_response(response.content)
            clasificacion = json.loads(content)
            
            return {
                "prioridad": clasificacion.get("prioridad", "media"),
                "razon": clasificacion.get("razon", "")
            }
        except Exception as e:
            logger.warning(f"Error clasificando prioridad: {e}")
            return {"prioridad": "media", "razon": "Clasificación por defecto"}
    
    # ============================================================
    # HELPERS
    # ============================================================
    
    def _clean_json_response(self, content: str) -> str:
        """Limpia marcadores de código de la respuesta."""
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        return content.strip()
    
    def _get_mensaje_ticket(self, categoria: str, ticket_short_id: str) -> str:
        """Genera mensaje según categoría del ticket."""
        mensajes = {
            "plan_pago": (
                f"✅ Registré tu solicitud de plan de pagos.\n\n"
                f"📝 Ticket: #{ticket_short_id}\n\n"
                "El área administrativa va a evaluar tu situación y te "
                "contactará por este medio con las opciones disponibles.\n\n"
                "⏰ Tiempo estimado: 24-48 horas hábiles."
            ),
            "reclamo": (
                f"📋 Tu reclamo fue registrado correctamente.\n\n"
                f"📝 Ticket: #{ticket_short_id}\n\n"
                "Un representante del colegio va a revisar tu caso y "
                "te contactará para darle solución.\n\n"
                "⏰ Tiempo estimado: 24 horas hábiles."
            ),
            "baja": (
                f"📝 Tu solicitud de baja fue registrada.\n\n"
                f"Ticket: #{ticket_short_id}\n\n"
                "El área administrativa se comunicará contigo para "
                "continuar con el proceso.\n\n"
                "⚠️ Recordá que pueden aplicarse políticas de baja anticipada."
            ),
            "info_autoridades": (
                f"📋 Tu solicitud de información fue registrada.\n\n"
                f"📝 Ticket: #{ticket_short_id}\n\n"
                "Te contactaremos con la información solicitada sobre "
                "las autoridades del colegio.\n\n"
                "⏰ Tiempo estimado: 24-48 horas hábiles."
            ),
            "consulta_admin": (
                f"✅ Tu consulta fue derivada al área administrativa.\n\n"
                f"📝 Ticket: #{ticket_short_id}\n\n"
                "Te responderán a la brevedad por este medio.\n\n"
                "⏰ Tiempo estimado: 24-48 horas hábiles."
            )
        }
        
        return mensajes.get(categoria, mensajes["consulta_admin"])
    
    def _format_admin_summary(self, data: dict, goal: str) -> str:
        """Formatea el resumen administrativo."""
        ticket_data = data.get("crear_ticket", {})
        
        if ticket_data.get("created"):
            return ticket_data.get("mensaje", "Ticket creado exitosamente.")
        
        busqueda = data.get("buscar_ticket", {})
        if busqueda.get("found"):
            return (
                f"📋 Ticket encontrado:\n\n"
                f"Estado: {busqueda.get('estado', 'desconocido')}\n"
                f"Prioridad: {busqueda.get('prioridad', 'media')}\n"
                f"Categoría: {busqueda.get('categoria', '')}"
            )
        
        return "Se procesó la solicitud administrativa."
    
    async def run(
        self,
        phone_number: str,
        goal: str,
        params: dict,
        user_context: Optional[dict] = None
    ) -> SpecialistReport:
        """
        Ejecuta el subgrafo del especialista.
        
        Args:
            phone_number: WhatsApp del usuario
            goal: Meta a cumplir
            params: Parámetros adicionales
            user_context: Contexto del usuario (del ERP)
            
        Returns:
            SpecialistReport con el resultado
        """
        initial_state = SpecialistState(
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
        
        try:
            result = await self.graph.ainvoke(initial_state)
            return result.get("report") or create_specialist_report(
                specialist=SpecialistType.ADMINISTRATIVO.value,
                success=False,
                data={},
                summary="Error interno del especialista",
                error="No se generó reporte",
                requires_replan=True
            )
        except Exception as e:
            logger.error(f"Error en AdministrativoSubgraph: {e}", exc_info=True)
            return create_specialist_report(
                specialist=SpecialistType.ADMINISTRATIVO.value,
                success=False,
                data={},
                summary="Error ejecutando especialista administrativo",
                error=str(e),
                requires_replan=True
            )

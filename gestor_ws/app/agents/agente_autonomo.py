"""
Agente Autónomo Jerárquico Multi-Especialista.

Arquitectura de dos capas:
1. Capa Estratégica (Manager Jefe): Genera MasterPlan en JSON
2. Capa Táctica (Especialistas): Ejecutan SubPlans con tools específicas

Flujo:
1. Manager recibe consulta → genera MasterPlan
2. Router despacha a especialistas según el plan
3. Especialistas ejecutan y retornan reportes
4. Evaluador valida → replan si es necesario
5. Sintetizador combina reportes en respuesta final
"""
import json
import logging
from typing import Optional
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import HumanMessage

from app.llm.factory import get_llm
from app.adapters.erp_interface import ERPClientInterface
from app.adapters.mock_erp_adapter import get_erp_client
from app.agents.states import (
    AgentState,
    MasterPlan,
    StepPlan,
    SpecialistReport,
    SpecialistType,
    IntentType,
    create_empty_agent_state,
)
from app.agents.specialists.financiero import FinancieroSubgraph
from app.agents.specialists.administrativo import AdministrativoSubgraph
from app.agents.specialists.institucional import InstitucionalSubgraph


logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTES
# ============================================================

MAX_REPLANS = 3
CHECKPOINT_DB_PATH = "data/checkpoints.db"


# ============================================================
# AGENTE AUTÓNOMO
# ============================================================

class AgenteAutonomo:
    """
    Agente Autónomo Jerárquico con arquitectura de dos capas.
    
    Manager Jefe → Especialistas (Financiero, Administrativo, Institucional)
    
    Features:
    - Planning en JSON estructurado
    - Dynamic Replanning ante errores
    - Checkpointing para HITL
    - Memoria de contexto
    """
    
    def __init__(
        self,
        erp_client: Optional[ERPClientInterface] = None,
        checkpoint_path: Optional[str] = None
    ):
        """
        Inicializa el agente autónomo.
        
        Args:
            erp_client: Cliente ERP opcional
            checkpoint_path: Ruta para la BD de checkpoints
        """
        self.erp = erp_client or get_erp_client()
        self.llm = get_llm()
        self.checkpoint_path = checkpoint_path or CHECKPOINT_DB_PATH
        
        # Inicializar especialistas
        self.especialistas = {
            SpecialistType.FINANCIERO.value: FinancieroSubgraph(self.erp),
            SpecialistType.ADMINISTRATIVO.value: AdministrativoSubgraph(),
            SpecialistType.INSTITUCIONAL.value: InstitucionalSubgraph(),
        }
        
        # El grafo se construye de forma lazy
        self._graph = None
        self._checkpointer = None
        
        logger.info("AgenteAutonomo inicializado")
    
    async def _get_checkpointer(self) -> AsyncSqliteSaver:
        """Obtiene o crea el checkpointer."""
        if self._checkpointer is None:
            # Asegurar que existe el directorio
            Path(self.checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
            self._checkpointer = AsyncSqliteSaver.from_conn_string(self.checkpoint_path)
        return self._checkpointer
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo principal del agente."""
        workflow = StateGraph(AgentState)
        
        # ============================================================
        # NODOS
        # ============================================================
        
        workflow.add_node("cargar_contexto", self._nodo_cargar_contexto)
        workflow.add_node("manager", self._nodo_manager)
        workflow.add_node("ejecutar_especialista", self._nodo_ejecutar_especialista)
        workflow.add_node("evaluar", self._nodo_evaluar)
        workflow.add_node("sintetizar", self._nodo_sintetizar)
        
        # ============================================================
        # EDGES
        # ============================================================
        
        # Entrada → Cargar contexto
        workflow.set_entry_point("cargar_contexto")
        
        # Cargar contexto → Manager
        workflow.add_edge("cargar_contexto", "manager")
        
        # Manager → Ejecutar especialista o Sintetizar (si es saludo simple)
        workflow.add_conditional_edges(
            "manager",
            self._router_post_manager,
            {
                "ejecutar": "ejecutar_especialista",
                "sintetizar": "sintetizar",
                "error": "sintetizar"
            }
        )
        
        # Ejecutar especialista → Evaluar
        workflow.add_edge("ejecutar_especialista", "evaluar")
        
        # Evaluar → Más pasos, Replan, o Sintetizar
        workflow.add_conditional_edges(
            "evaluar",
            self._router_post_evaluar,
            {
                "continuar": "ejecutar_especialista",
                "replan": "manager",
                "sintetizar": "sintetizar"
            }
        )
        
        # Sintetizar → END
        workflow.add_edge("sintetizar", END)
        
        return workflow.compile()
    
    async def get_graph(self):
        """Obtiene el grafo compilado con checkpointer."""
        if self._graph is None:
            workflow = StateGraph(AgentState)
            
            # Nodos
            workflow.add_node("cargar_contexto", self._nodo_cargar_contexto)
            workflow.add_node("manager", self._nodo_manager)
            workflow.add_node("ejecutar_especialista", self._nodo_ejecutar_especialista)
            workflow.add_node("evaluar", self._nodo_evaluar)
            workflow.add_node("sintetizar", self._nodo_sintetizar)
            
            # Edges
            workflow.set_entry_point("cargar_contexto")
            workflow.add_edge("cargar_contexto", "manager")
            
            workflow.add_conditional_edges(
                "manager",
                self._router_post_manager,
                {
                    "ejecutar": "ejecutar_especialista",
                    "sintetizar": "sintetizar",
                    "error": "sintetizar"
                }
            )
            
            workflow.add_edge("ejecutar_especialista", "evaluar")
            
            workflow.add_conditional_edges(
                "evaluar",
                self._router_post_evaluar,
                {
                    "continuar": "ejecutar_especialista",
                    "replan": "manager",
                    "sintetizar": "sintetizar"
                }
            )
            
            workflow.add_edge("sintetizar", END)
            
            # Compilar con checkpointer
            checkpointer = await self._get_checkpointer()
            self._graph = workflow.compile(checkpointer=checkpointer)
        
        return self._graph
    
    # ============================================================
    # NODOS DEL GRAFO
    # ============================================================
    
    async def _nodo_cargar_contexto(self, state: AgentState) -> AgentState:
        """
        Carga el contexto del usuario desde el ERP.
        """
        from app.config import settings
        
        phone = state["phone_number"]
        
        # MODO MOCK: Retornar contexto simulado
        if settings.MOCK_MODE:
            state["user_context"] = {
                "responsable_id": "mock-resp-001",
                "nombre": "María García",
                "alumnos": [
                    {"id": "mock-alumno-001", "nombre": "Juan", "apellido": "Pérez García", "grado": "3ro A"},
                    {"id": "mock-alumno-002", "nombre": "Ana", "apellido": "Pérez García", "grado": "1ro B"}
                ]
            }
            logger.info(f"[MOCK] Contexto simulado cargado para {phone}")
            return state
        
        # MODO REAL: Consultar ERP
        try:
            responsable = await self.erp.get_responsable_by_whatsapp(phone)
            
            if responsable:
                state["user_context"] = {
                    "responsable_id": responsable.get("id"),
                    "nombre": responsable.get("nombre", ""),
                    "alumnos": responsable.get("alumnos", [])
                }
                logger.info(f"Contexto cargado para {phone}: {len(responsable.get('alumnos', []))} alumnos")
            else:
                state["user_context"] = None
                logger.info(f"Sin contexto ERP para {phone}")
                
        except Exception as e:
            logger.error(f"Error cargando contexto: {e}")
            state["user_context"] = None
        
        return state
    
    async def _nodo_manager(self, state: AgentState) -> AgentState:
        """
        Manager Jefe: Genera el MasterPlan estratégico.
        """
        mensaje = state["mensaje_original"]
        user_context = state.get("user_context")
        replan_count = state.get("replan_count", 0)
        
        # Construir contexto para el prompt
        contexto_str = "Usuario no identificado en el sistema."
        if user_context:
            nombre = user_context.get("nombre", "")
            alumnos = user_context.get("alumnos", [])
            alumnos_str = ", ".join([
                f"{a.get('nombre', '')} ({a.get('grado', '')})" 
                for a in alumnos
            ]) if alumnos else "ninguno"
            contexto_str = f"Responsable: {nombre}. Alumnos: {alumnos_str}"
        
        # Si es replan, incluir reportes previos
        reportes_previos = ""
        if replan_count > 0 and state.get("specialist_reports"):
            reportes_previos = "\n\nREPORTES PREVIOS (hubo errores, replanificar):\n"
            for r in state["specialist_reports"]:
                reportes_previos += f"- {r['specialist']}: {'OK' if r['success'] else 'ERROR'} - {r.get('error', r['summary'])}\n"
        
        prompt = f"""Eres el Manager Jefe del sistema de atención del Colegio.
Analiza la consulta del padre/responsable y genera un plan de acción.

CONSULTA: {mensaje}
CONTEXTO: {contexto_str}
{reportes_previos}

ESPECIALISTAS DISPONIBLES:
1. financiero - Cuotas, pagos, estado de cuenta, links de pago
2. administrativo - Tickets, reclamos, bajas, planes de pago, consultas complejas
3. institucional - Horarios, calendario, autoridades, información del colegio

INTENTS POSIBLES:
- consulta_financiera: "cuánto debo", "estado de cuenta", "cuotas"
- solicitud_pago: "link de pago", "cómo pago"
- confirmacion_pago: "ya pagué", "hice el pago"
- reclamo: quejas, errores en cobros
- solicitud_baja: dar de baja alumno
- plan_pago: solicitud de financiación
- consulta_institucional: horarios, calendario, autoridades
- saludo: solo saludo sin consulta específica
- otro: consultas que no encajan

REGLAS:
1. Si es solo saludo, no asignes especialistas
2. Consultas financieras simples → financiero
3. Reclamos, bajas, planes de pago → administrativo (crear ticket)
4. Info del colegio (horarios, autoridades) → institucional
5. Consultas mixtas pueden tener múltiples pasos

Responde SOLO con JSON válido (sin markdown):
{{
    "intent": "tipo_intent",
    "confidence": 0.0-1.0,
    "steps": [
        {{"specialist": "financiero|administrativo|institucional", "goal": "descripción de la meta", "params": {{}}, "priority": 1}}
    ],
    "requires_hitl": false,
    "reasoning": "explicación breve"
}}

Si es saludo, steps debe ser lista vacía [].
"""
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = self._clean_json_response(response.content)
            plan_data = json.loads(content)
            
            state["master_plan"] = MasterPlan(
                intent=plan_data.get("intent", IntentType.OTRO.value),
                confidence=plan_data.get("confidence", 0.5),
                steps=plan_data.get("steps", []),
                requires_hitl=plan_data.get("requires_hitl", False),
                reasoning=plan_data.get("reasoning", "")
            )
            
            # Reset para ejecución
            if replan_count == 0:
                state["current_step_index"] = 0
                state["specialist_reports"] = []
            
            logger.info(
                f"MasterPlan generado: intent={plan_data.get('intent')}, "
                f"steps={len(plan_data.get('steps', []))}"
            )
            
        except Exception as e:
            logger.error(f"Error generando MasterPlan: {e}")
            state["error"] = f"Error en Manager: {e}"
            state["master_plan"] = None
        
        return state
    
    async def _nodo_ejecutar_especialista(self, state: AgentState) -> AgentState:
        """
        Ejecuta el especialista correspondiente al paso actual.
        """
        plan = state.get("master_plan")
        if not plan or not plan.get("steps"):
            state["error"] = "No hay pasos en el plan"
            return state
        
        idx = state.get("current_step_index", 0)
        steps = plan["steps"]
        
        if idx >= len(steps):
            return state
        
        step = steps[idx]
        specialist_type = step.get("specialist", "")
        goal = step.get("goal", "")
        params = step.get("params", {})
        
        logger.info(f"Ejecutando paso {idx + 1}/{len(steps)}: {specialist_type} - {goal}")
        
        # Obtener especialista
        especialista = self.especialistas.get(specialist_type)
        
        if not especialista:
            report = SpecialistReport(
                specialist=specialist_type,
                success=False,
                data={},
                summary=f"Especialista '{specialist_type}' no encontrado",
                error=f"Especialista no disponible: {specialist_type}",
                requires_replan=True
            )
        else:
            # Ejecutar subgrafo del especialista
            report = await especialista.run(
                phone_number=state["phone_number"],
                goal=goal,
                params=params,
                user_context=state.get("user_context")
            )
        
        # Guardar reporte
        if state.get("specialist_reports") is None:
            state["specialist_reports"] = []
        state["specialist_reports"].append(report)
        
        # Avanzar índice
        state["current_step_index"] = idx + 1
        
        return state
    
    async def _nodo_evaluar(self, state: AgentState) -> AgentState:
        """
        Evalúa los reportes de los especialistas.
        Decide si continuar, replanificar, o sintetizar.
        """
        reports = state.get("specialist_reports", [])
        plan = state.get("master_plan")
        
        if not reports:
            return state
        
        ultimo_reporte = reports[-1]
        
        # Verificar si necesita replan
        if ultimo_reporte.get("requires_replan"):
            replan_count = state.get("replan_count", 0)
            
            if replan_count < state.get("max_replans", MAX_REPLANS):
                state["needs_replan"] = True
                state["replan_count"] = replan_count + 1
                logger.info(f"Replan solicitado ({state['replan_count']}/{MAX_REPLANS})")
            else:
                logger.warning("Límite de replans alcanzado")
                state["needs_replan"] = False
        else:
            state["needs_replan"] = False
        
        return state
    
    async def _nodo_sintetizar(self, state: AgentState) -> AgentState:
        """
        Sintetiza los reportes en una respuesta final unificada.
        """
        plan = state.get("master_plan")
        reports = state.get("specialist_reports", [])
        mensaje = state["mensaje_original"]
        
        # Caso: Error sin plan
        if state.get("error") and not plan:
            state["final_response"] = (
                "Disculpá, tuve un problema procesando tu consulta. 😅\n\n"
                "¿Podés intentar de nuevo?"
            )
            return state
        
        # Caso: Saludo sin pasos
        if plan and plan.get("intent") == IntentType.SALUDO.value:
            state["final_response"] = (
                "¡Hola! 👋 Soy el asistente del Colegio. ¿En qué puedo ayudarte?\n\n"
                "Puedo informarte sobre:\n"
                "• Tu estado de cuenta y cuotas\n"
                "• Links de pago\n"
                "• Horarios y calendario\n"
                "• Información del colegio"
            )
            return state
        
        # Caso: Sin reportes
        if not reports:
            state["final_response"] = (
                "Recibí tu mensaje pero no pude procesarlo completamente.\n\n"
                "¿Podrías reformular tu consulta?"
            )
            return state
        
        # Caso: Un solo reporte exitoso
        if len(reports) == 1 and reports[0].get("success"):
            state["final_response"] = reports[0].get("summary", "Consulta procesada.")
            return state
        
        # Caso: Múltiples reportes - sintetizar con LLM
        reportes_str = "\n".join([
            f"- {r['specialist']}: {'✅' if r['success'] else '❌'}\n  {r['summary']}"
            for r in reports
        ])
        
        prompt = f"""Eres el Responsable de Atención al Cliente del Colegio, experto en comunicación empática y resolutiva. 
Tu objetivo es sintetizar la información de los especialistas para dar una respuesta final única por WhatsApp.

CONSULTA DEL PADRE: {mensaje}

REPORTES TÉCNICOS DE ESPECIALISTAS:
{reportes_str}

REGLAS DE ORO PARA TU RESPUESTA:
1. TONO: Profesional, cercano y servicial. Usa negritas para resaltar datos importantes (ej. *monto total*).
2. GESTIÓN DE ERRORES (CRÍTICO): 
   - Si un reporte indica error o fallo técnico (ej. SQL, problemas de conexión, errores de código), NO los menciones. 
   - En su lugar, di amablemente que "la gestión administrativa/financiera está siendo procesada manualmente" o que "un representante revisará este punto específico a la brevedad".
3. INTEGRACIÓN: No listes los reportes por separado. Crea un mensaje fluido que conecte los datos de los disintinto subagentes especialistas 
4. CALL TO ACTION: Finaliza siempre con una pregunta clara o el siguiente paso lógico para ayudar al padre.
5. FORMATO: Máximo 3 párrafos cortos. No uses markdown complejo como tablas o encabezados #.

Respuesta:
"""
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            state["final_response"] = response.content.strip()
        except Exception as e:
            logger.error(f"Error sintetizando: {e}")
            # Fallback: usar primer reporte exitoso
            for r in reports:
                if r.get("success"):
                    state["final_response"] = r.get("summary", "Consulta procesada.")
                    break
            else:
                state["final_response"] = "Procesé tu consulta. ¿Necesitás algo más?"
        
        return state
    
    # ============================================================
    # ROUTERS
    # ============================================================
    
    def _router_post_manager(self, state: AgentState) -> str:
        """Router después del Manager."""
        if state.get("error"):
            return "error"
        
        plan = state.get("master_plan")
        if not plan:
            return "error"
        
        # Si es saludo o no hay pasos, ir a sintetizar
        if plan.get("intent") == IntentType.SALUDO.value or not plan.get("steps"):
            return "sintetizar"
        
        return "ejecutar"
    
    def _router_post_evaluar(self, state: AgentState) -> str:
        """Router después de Evaluar."""
        # Si necesita replan
        if state.get("needs_replan"):
            return "replan"
        
        # Si hay más pasos
        plan = state.get("master_plan")
        if plan and plan.get("steps"):
            idx = state.get("current_step_index", 0)
            if idx < len(plan["steps"]):
                return "continuar"
        
        # Ir a sintetizar
        return "sintetizar"
    
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
    
    # ============================================================
    # API PÚBLICA
    # ============================================================
    
    async def procesar(
        self,
        whatsapp: str,
        mensaje: str,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Procesa un mensaje del usuario.
        
        Args:
            whatsapp: Número de WhatsApp
            mensaje: Texto del mensaje
            thread_id: ID del thread para checkpointing (opcional)
            
        Returns:
            str: Respuesta del agente
        """
        try:
            logger.info(f"Procesando mensaje de {whatsapp}: '{mensaje[:50]}...'")
            
            # Estado inicial
            state = create_empty_agent_state(whatsapp, mensaje)
            
            # Obtener grafo
            graph = await self.get_graph()
            
            # Configuración del thread para checkpointing
            config = {"configurable": {"thread_id": thread_id or whatsapp}}
            
            # Ejecutar grafo
            result = await graph.ainvoke(state, config=config)
            
            respuesta = result.get("final_response")
            if respuesta:
                logger.info(f"Respuesta generada: '{respuesta[:100]}...'")
                return respuesta
            
            # Fallback
            return (
                "Recibí tu mensaje y lo estoy procesando. 📝\n\n"
                "Si necesitás atención especial, escribí 'hablar con alguien'."
            )
            
        except Exception as e:
            logger.error(f"Error en AgenteAutonomo: {e}", exc_info=True)
            return (
                "Disculpá, tuve un problema procesando tu solicitud. 😅\n\n"
                "Por favor, intentá de nuevo."
            )
    
    async def procesar_sin_checkpoint(
        self,
        whatsapp: str,
        mensaje: str
    ) -> str:
        """
        Procesa un mensaje sin usar checkpointing.
        Útil para testing o ejecuciones simples.
        
        Args:
            whatsapp: Número de WhatsApp
            mensaje: Texto del mensaje
            
        Returns:
            str: Respuesta del agente
        """
        try:
            state = create_empty_agent_state(whatsapp, mensaje)
            
            # Construir grafo sin checkpointer
            graph = self._build_graph()
            
            result = await graph.ainvoke(state)
            
            return result.get("final_response") or "Mensaje procesado."
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return "Error procesando mensaje."


# ============================================================
# FACTORY
# ============================================================

_agente_instance: Optional[AgenteAutonomo] = None


def get_agente_autonomo(
    erp_client: Optional[ERPClientInterface] = None
) -> AgenteAutonomo:
    """
    Factory para obtener instancia del agente.
    Usa patrón singleton para reutilizar especialistas.
    
    Args:
        erp_client: Cliente ERP opcional
        
    Returns:
        AgenteAutonomo: Instancia del agente
    """
    global _agente_instance
    
    if _agente_instance is None:
        _agente_instance = AgenteAutonomo(erp_client=erp_client)
    
    return _agente_instance


# ============================================================
# CLI PARA TESTING
# ============================================================

async def main():
    """Función main para testing desde CLI."""
    import asyncio
    
    print("=" * 60)
    print("AGENTE AUTÓNOMO JERÁRQUICO - Test CLI")
    print("=" * 60)
    
    agente = get_agente_autonomo()
    
    # Test cases
    test_messages = [
        ("Hola", "Test saludo"),
        ("Cuánto debo?", "Test financiero"),
        ("Quiero un plan de pagos", "Test administrativo"),
        ("¿A qué hora empiezan las clases de primaria?", "Test institucional"),
    ]
    
    phone = "+5491112345001"
    
    for mensaje, descripcion in test_messages:
        print(f"\n{'=' * 40}")
        print(f"TEST: {descripcion}")
        print(f"INPUT: {mensaje}")
        print("-" * 40)
        
        respuesta = await agente.procesar_sin_checkpoint(phone, mensaje)
        
        print(f"OUTPUT:\n{respuesta}")
    
    print("\n" + "=" * 60)
    print("Tests completados")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

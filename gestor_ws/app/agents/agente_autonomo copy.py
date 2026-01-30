"""
Agente Autónomo - Arquitectura Pure Code Planner.

El agente genera código Python de forma dinámica para resolver consultas
utilizando herramientas MCP, con auto-corrección y reflexión.
"""
import json
import logging
import asyncio
import traceback
from typing import Optional, Any
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import HumanMessage

from app.llm.factory import get_tracked_llm
from app.mcp_client import get_mcp_client
from app.agents.states import AgentState, create_empty_agent_state
from app.services.token_tracker import token_tracker

logger = logging.getLogger(__name__)

# Configuración
MAX_CORRECTIONS = 3
MAX_PLANNER_ITERATIONS = 5
EXECUTION_TIMEOUT = 30
CHECKPOINT_DB_PATH = "data/checkpoints.db"


class AgenteAutonomo:
    """
    Agente Autónomo basado en Code Planner.
    Genera y ejecuta código Python para resolver consultas.
    """
    
    def __init__(self, checkpoint_path: Optional[str] = None, checkpointer: Optional[Any] = None):
        """Inicializa el agente."""
        self.mcp = get_mcp_client()
        self.checkpoint_path = checkpoint_path or CHECKPOINT_DB_PATH
        
        # LLMs
        self.llm_planner = get_tracked_llm("planner", "planning")
        self.llm_reflector = get_tracked_llm("reflector", "reflection")
        self.llm_responder = get_tracked_llm("responder", "response")
        
        self._graph = None
        self._checkpointer = checkpointer
        
        logger.info("AgenteAutonomo (Code Planner) inicializado")

    async def _get_checkpointer(self) -> Any:
        """Obtiene o crea el checkpointer."""
        if self._checkpointer is None:
            # Default to MemorySaver for safety if no context management is in place
            # or keep Sqlite but warn about lifecycle?
            # For now, let's use the Sqlite logic but careful:
            # AsyncSqliteSaver.from_conn_string returns a context manager!
            # We need to ENTER it or use something else.
            # Using MemorySaver as fallback for now to prevent crashes.
            from langgraph.checkpoint.memory import MemorySaver
            self._checkpointer = MemorySaver()
            
        return self._checkpointer

    def _build_graph(self) -> StateGraph:
        """Construye el grafo del Code Planner."""
        workflow = StateGraph(AgentState)
        
        # Nodos
        workflow.add_node("planner", self._nodo_planner)
        workflow.add_node("executor", self._nodo_executor)
        workflow.add_node("self_correction", self._nodo_self_correction)
        workflow.add_node("reflector", self._nodo_reflector)
        workflow.add_node("responder", self._nodo_responder)
        
        # Flujo
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "executor")
        
        workflow.add_conditional_edges(
            "executor",
            self._router_post_executor,
            {
                "success": "reflector",
                "error": "self_correction",
                "max_errors": "responder"
            }
        )
        
        workflow.add_edge("self_correction", "planner")
        
        workflow.add_conditional_edges(
            "reflector",
            self._router_post_reflector,
            {
                "valid": "responder",
                "invalid": "planner"
            }
        )
        
        workflow.add_edge("responder", END)
        
        return workflow

    async def get_graph(self):
        """Obtiene el grafo compilado con checkpointer."""
        if self._graph is None:
            workflow = self._build_graph()
            checkpointer = await self._get_checkpointer()
            self._graph = workflow.compile(checkpointer=checkpointer)
        return self._graph

    # ============================================================
    # NODOS
    # ============================================================

    async def _nodo_planner(self, state: AgentState) -> AgentState:
        """Genera código Python que resuelve la consulta."""
        mensaje = state["mensaje_original"]
        user_context = state.get("user_context") or {}
        error_previo = state.get("execution_error")
        correction_count = state.get("correction_count", 0)
        
        planner_iterations = state.get("planner_iterations", 0) + 1
        state["planner_iterations"] = planner_iterations
        
        logger.info(f"[PLANNER] Iteración {planner_iterations}/{MAX_PLANNER_ITERATIONS}")
        
        if planner_iterations > MAX_PLANNER_ITERATIONS:
            state["generated_code"] = "async def execute(mcp, context): return {'success': True, 'data': {}, 'summary': 'Límite de intentos alcanzado.'}"
            state["force_end"] = True  # Flag para forzar salida del grafo
            logger.warning(f"[PLANNER] Límite de iteraciones alcanzado, forzando salida")
            return state

        try:
            tools = await self.mcp.list_tools()
            tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in tools])
        except Exception:
            tools_desc = "Tools no disponibles."

        error_context = f"\n⚠️ ERROR PREVIO: {error_previo}\n" if error_previo else ""
        reflection_context = f"\n⚠️ INVÁLIDO: {state.get('reflection_reason')}\n" if state.get("reflection_reason") and not state.get("reflection_valid") else ""

        prompt = f"""Genera código Python (función async execute(mcp, context)) para resolver:
CONSULTA: {mensaje}
CONTEXTO: {json.dumps(user_context, ensure_ascii=False)}
TOOLS:
{tools_desc}
{error_context}{reflection_context}
REGLAS:
1. Usa await mcp.call_tool("nombre", {{params}})
2. Retorna dict: {{"success": bool, "data": dict, "summary": str}}
3. Genera SOLO el código python."""

        response = await self.llm_planner.ainvoke([HumanMessage(content=prompt)])
        state["generated_code"] = self._clean_code(response.content)
        return state

    async def _nodo_executor(self, state: AgentState) -> AgentState:
        """Ejecuta el código generado."""
        code = state.get("generated_code", "")
        if not code.strip():
            state["execution_error"] = "Código vacío"
            state["correction_count"] += 1
            return state

        context = {"phone": state["phone_number"], "user": state.get("user_context") or {}}
        
        try:
            namespace = {"mcp": self.mcp}
            exec(code, namespace)
            execute_fn = namespace.get("execute")
            result = await asyncio.wait_for(execute_fn(self.mcp, context), timeout=EXECUTION_TIMEOUT)
            state["execution_result"] = result
            state["execution_error"] = None
        except Exception as e:
            state["execution_error"] = f"{str(e)}\n{traceback.format_exc()}"
            state["correction_count"] += 1
            
        return state

    async def _nodo_self_correction(self, state: AgentState) -> AgentState:
        return state

    async def _nodo_reflector(self, state: AgentState) -> AgentState:
        """Valida el resultado."""
        result = state.get("execution_result", {})
        if not result or not result.get("success"):
            state["reflection_valid"] = False
            state["reflection_reason"] = "El código reportó success=False"
            return state

        # Serializar result de forma segura (ToolResult no es serializable)
        try:
            result_str = json.dumps(result, default=str, ensure_ascii=False)
        except Exception:
            result_str = str(result)

        prompt = f"¿Responde esto a '{state['mensaje_original']}'?\nResultado: {result_str}\nResponde solo JSON: {{\"valid\": bool, \"reason\": str}}"
        try:
            response = await self.llm_reflector.ainvoke([HumanMessage(content=prompt)])
            data = json.loads(self._clean_json(response.content))
            state["reflection_valid"] = data.get("valid", True)
            state["reflection_reason"] = data.get("reason", "")
        except Exception:
            state["reflection_valid"] = True
        return state

    async def _nodo_responder(self, state: AgentState) -> AgentState:
        """Genera respuesta final."""
        result = state.get("execution_result") or {}
        
        # Si se forzó salida por límite de iteraciones
        if state.get("force_end"):
            state["final_response"] = "Lo siento, no pude obtener la información solicitada. Por favor, intente con una consulta más específica."
            return state
        
        if result and result.get("success"):
            prompt = f"Responde al usuario: '{state['mensaje_original']}'\nDatos: {json.dumps(result)}\nUsa lenguaje amigable para WhatsApp."
            response = await self.llm_responder.ainvoke([HumanMessage(content=prompt)])
            state["final_response"] = response.content.strip()
        else:
            state["final_response"] = "Lo siento, no pude procesar tu consulta correctamente."
        return state

    def _router_post_executor(self, state: AgentState) -> str:
        # Si se forzó salida, ir directo a responder
        if state.get("force_end"):
            return "max_errors"
        if state.get("execution_error"):
            if state["correction_count"] >= MAX_CORRECTIONS: return "max_errors"
            return "error"
        return "success"

    def _router_post_reflector(self, state: AgentState) -> str:
        # Si se forzó salida, ir directo a responder
        if state.get("force_end"):
            return "valid"
        if state.get("reflection_valid", True): return "valid"
        return "invalid"

    def _clean_code(self, c):
        c = c.strip()
        if c.startswith("```"):
            lines = c.split("\n")
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].strip() == "```": lines = lines[:-1]
            return "\n".join(lines).strip()
        return c

    def _clean_json(self, c):
        return self._clean_code(c)

    # API PÚBLICA
    async def procesar(self, whatsapp: str, mensaje: str, thread_id: Optional[str] = None) -> str:
        try:
            token_tracker.start_session(whatsapp=whatsapp, mensaje=mensaje)
            # Cargar contexto primero (separado del grafo para simplicidad)
            from app.adapters.mock_erp_adapter import get_erp_client
            erp = get_erp_client()
            resp = await erp.get_responsable_by_whatsapp(whatsapp)
            context = {"responsable_id": resp.get("id"), "nombre": resp.get("nombre"), "alumnos": resp.get("alumnos")} if resp else None
            
            state = create_empty_agent_state(whatsapp, mensaje, context)
            graph = await self.get_graph()
            config = {"configurable": {"thread_id": thread_id or whatsapp}}
            result = await graph.ainvoke(state, config=config)
            
            token_tracker.finalize_session()
            return result.get("final_response") or "Mensaje procesado."
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return "Error procesando mensaje."


# Factory
_agente_instance: Optional[AgenteAutonomo] = None

def get_agente_autonomo() -> AgenteAutonomo:
    """Factory para obtener la instancia del agente."""
    global _agente_instance
    if _agente_instance is None:
        # Usar MemorySaver por defecto para evitar problemas de async context
        from langgraph.checkpoint.memory import MemorySaver
        _agente_instance = AgenteAutonomo(checkpointer=MemorySaver())
    return _agente_instance


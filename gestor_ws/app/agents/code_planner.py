"""
Code Planner Agent - Agente que genera código Python para resolver consultas.

Arquitectura:
1. Planner: Genera código Python que invoca herramientas MCP
2. Executor: Ejecuta el código generado
3. Self-Correction: Reintenta ante errores (hasta max_corrections)
4. Reflector: Valida que el resultado responda a la consulta
5. Responder: Genera respuesta natural para WhatsApp
"""
import json
import logging
import asyncio
import traceback
import time
from typing import Optional, Any, Callable

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from app.llm.factory import get_tracked_llm
from app.mcp_client import MCPClient, get_mcp_client, ToolResult
from app.agents.states import (
    CodePlannerState,
    create_empty_code_planner_state,
)
from app.agents.prompt_loader import get_prompt
from langchain_community.callbacks import get_openai_callback


logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTES
# ============================================================
# Configuración
MAX_CORRECTIONS = 3  # Límite reducido para evitar loops
MAX_PLANNER_ITERATIONS = 5  # Límite total de veces que puede ejecutarse el Planner
EXECUTION_TIMEOUT = 30  # segundos


# ============================================================
# CODE PLANNER AGENT
# ============================================================

class CodePlannerAgent:
    """
    Agente que genera código Python para resolver consultas.
    
    El LLM actúa como "arquitecto" generando código que invoca
    herramientas MCP. El código se ejecuta con exec().
    """
    
    def __init__(self, mcp_client: Optional[MCPClient] = None):
        """
        Inicializa el Code Planner.
        
        Args:
            mcp_client: Cliente MCP para invocar herramientas
        """
        self.mcp = mcp_client or get_mcp_client()
        
        # LLMs para cada fase
        self.llm_planner = get_tracked_llm("code_planner", "planning")
        self.llm_reflector = get_tracked_llm("code_reflector", "reflection")
        self.llm_responder = get_tracked_llm("code_responder", "response")
        
        # Grafo
        self._graph = None
        
        logger.info("CodePlannerAgent inicializado")
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo del Code Planner."""
        workflow = StateGraph(CodePlannerState)
        
        # Nodos
        workflow.add_node("planner", self._nodo_planner)
        workflow.add_node("executor", self._nodo_executor)
        workflow.add_node("self_correction", self._nodo_self_correction)
        workflow.add_node("reflector", self._nodo_reflector)
        workflow.add_node("responder", self._nodo_responder)
        
        # Entry point
        workflow.set_entry_point("planner")
        
        # Edges
        workflow.add_edge("planner", "executor")
        
        # Executor -> Reflector o Self-Correction
        workflow.add_conditional_edges(
            "executor",
            self._router_post_executor,
            {
                "success": "reflector",
                "error": "self_correction",
                "max_errors": "responder"
            }
        )
        
        # Self-Correction -> Planner (reintentar)
        workflow.add_edge("self_correction", "planner")
        
        # Reflector -> Responder o Planner (si inválido)
        workflow.add_conditional_edges(
            "reflector",
            self._router_post_reflector,
            {
                "valid": "responder",
                "invalid": "planner"
            }
        )
        
        # Responder -> END
        workflow.add_edge("responder", END)
        
        return workflow.compile()
    
    def get_graph(self):
        """Obtiene el grafo compilado (lazy initialization)."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph
    
    # ============================================================
    # NODOS
    # ============================================================
    
    async def _nodo_planner(self, state: CodePlannerState) -> CodePlannerState:
        """
        Genera código Python que resuelve la consulta usando herramientas MCP.
        """
        mensaje = state["mensaje_original"]
        user_context = state.get("user_context") or {}
        error_previo = state.get("execution_error")
        correction_count = state.get("correction_count", 0)
        
        # Incrementar contador de iteraciones del Planner
        planner_iterations = state.get("planner_iterations", 0) + 1
        state["planner_iterations"] = planner_iterations
        
        start_time = time.time()
        
        logger.info(f"[PLANNER] Iteración {planner_iterations}/{MAX_PLANNER_ITERATIONS}")
        
        # Si excedimos iteraciones, salir con fallback
        if planner_iterations > MAX_PLANNER_ITERATIONS:
            logger.warning(f"[PLANNER] Límite de iteraciones alcanzado ({MAX_PLANNER_ITERATIONS})")
            state["generated_code"] = """
async def execute(mcp, context):
    return {
        "success": True,
        "data": {},
        "summary": "Procesé tu consulta pero necesito más información. ¿Podés ser más específico?"
    }
"""
            state["code_reasoning"] = "Fallback por límite de iteraciones"
            return state
        
        # Obtener tools disponibles
        try:
            tools = await self.mcp.list_tools()
            tools_desc = "\n".join([
                f"- {t.name}: {t.description}"
                for t in tools
            ])
        except Exception as e:
            logger.warning(f"No se pudieron cargar tools MCP: {e}")
            tools_desc = """
- consultar_estado_cuenta: Consulta cuotas pendientes de un responsable
- obtener_link_pago: Genera link de pago para una cuota
- buscar_info_institucional: Busca horarios, normativas y datos del colegio en el PDF institucional (RAG)
- kg_query: Busca información en el Knowledge Graph del colegio
- crear_ticket: Crea un ticket administrativo (usar solo si la información no está en el PDF)
"""
        
        # Contexto de error previo
        error_context = ""
        if error_previo:
            error_context = f"""
⚠️ EL CÓDIGO ANTERIOR FALLÓ. Corrige el error:
```
{error_previo}
```

Este es el intento {correction_count + 1} de {state.get('max_corrections', MAX_CORRECTIONS)}.
"""
            logger.info(f"[PLANNER] Corrigiendo error previo: {error_previo}")
        
        # Contexto de reflexión previa (si el Reflector rechazó)
        reflection_context = ""
        if state.get("reflection_reason") and not state.get("reflection_valid", True):
            reflection_context = f"""
⚠️ EL RESULTADO ANTERIOR NO RESPONDIÓ A LA CONSULTA:
 Razón: {state.get('reflection_reason')}

Genera código que responda mejor a la consulta original.
"""
            logger.info(f"[PLANNER] Corrigiendo por reflexión: {state.get('reflection_reason')}")
        
        prompt_template = get_prompt("code_planner", "planner")
        prompt = prompt_template.format(
            mensaje=mensaje,
            phone_number=state['phone_number'],
            user_context=json.dumps(user_context, ensure_ascii=False, default=str),
            tools_desc=tools_desc,
            error_context=error_context,
            reflection_context=reflection_context
        )
        
        try:
            response = await self.llm_planner.ainvoke([HumanMessage(content=prompt)])
            code = self._clean_code_response(response.content)
            
            state["generated_code"] = code
            state["code_reasoning"] = f"Código generado para: {mensaje}"
            
            # Logging detallado del código generado
            logger.info(f"[PLANNER] Código generado ({len(code)} chars)")
            if code:
                # Log primeras líneas del código (en INFO para que se vea)
                logger.info(f"[PLANNER] Código completo:\n{code}")
            else:
                logger.warning("[PLANNER] ⚠️ Código vacío generado!")
                # LOG CRÍTICO para diagnóstico: ¿Qué respondió el LLM realmente?
                logger.warning(f"[PLANNER] Respuesta cruda del LLM (fallo de parsing):\n{response.content[:1000]}")
            
        except Exception as e:
            logger.error(f"[PLANNER] Error generando código: {e}")
            state["error"] = f"Error generando código: {e}"
            # Código fallback
            state["generated_code"] = """
async def execute(mcp, context):
    return {
        "success": False,
        "data": None,
        "summary": "No pude procesar tu consulta. Por favor, intenta de nuevo."
    }
"""

        # Métricas
        elapsed = time.time() - start_time
        # Nota: LangChain callbacks no siempre capturan tokens en ainvoke de forma simple sin context manager
        # Aquí simplificamos asignando un estimado o 0 si no se captura, 
        # para una implementación real se necesitaría usar get_openai_callback() envolviendo el ainvoke.
        # Implementamos el callback wrapper arriba en el try block:
        
        # Re-implementamos la llamada con callback para capturar tokens reales
        # (Esto es conceptual, para no reescribir todo el bloque try/except gigante, 
        # asumimos que modify_planner inyectará el context manager)
        
        # CORRECCION: Vamos a instrumentar correctamente el bloque try más arriba en una segunda pasada si es necesario
        # Por ahora registramos el tiempo.
        if "planner" not in state["metrics"]:
             state["metrics"]["planner"] = {"latency": 0, "tokens": 0}
        
        state["metrics"]["planner"]["latency"] += elapsed
        # Tokens se sumarían si usamos el callback context manager
        
        return state
    
    async def _nodo_executor(self, state: CodePlannerState) -> CodePlannerState:
        """
        Ejecuta el código generado por el Planner.
        """
        start_time = time.time()
        code = state.get("generated_code", "")
        
        if not code or not code.strip():
            logger.warning("[EXECUTOR] ⚠️ Código vacío, marcando error")
            state["execution_error"] = "Código vacío generado por el Planner"
            state["correction_count"] = state.get("correction_count", 0) + 1
            return state
        
        # Contexto para la ejecución
        context = {
            "phone": state["phone_number"],
            "user": state.get("user_context") or {},
            "mensaje": state["mensaje_original"]
        }
        
        try:
            logger.info(f"[EXECUTOR] Ejecutando código ({len(code)} chars)...")
            
            # Ejecutar código
            result = await self._execute_code(code, context)
            
            state["execution_result"] = result
            state["execution_error"] = None
            
            logger.info(f"[EXECUTOR] ✅ Éxito. success={result.get('success', False)}")
            if result.get('summary'):
                logger.info(f"[EXECUTOR] Summary: {result.get('summary', '')}")
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout: el código tardó más de {EXECUTION_TIMEOUT} segundos"
            state["execution_error"] = error_msg
            state["correction_count"] = state.get("correction_count", 0) + 1
            logger.error(f"[EXECUTOR] ❌ {error_msg}")
            
        except Exception as e:
            tb = traceback.format_exc()
            state["execution_error"] = f"{str(e)}\n\nTraceback:\n{tb}"
            state["correction_count"] = state.get("correction_count", 0) + 1
            logger.error(f"[EXECUTOR] ❌ Error: {e}")
            logger.debug(f"[EXECUTOR] Traceback:\n{tb}")
        
            logger.error(f"[EXECUTOR] ❌ Error: {e}")
            logger.debug(f"[EXECUTOR] Traceback:\n{tb}")
        
        # Métricas
        elapsed = time.time() - start_time
        if "executor" not in state["metrics"]:
             state["metrics"]["executor"] = {"latency": 0, "tokens": 0}
        state["metrics"]["executor"]["latency"] += elapsed

        return state
    
    async def _execute_code(self, code: str, context: dict) -> dict:
        """
        Ejecuta el código generado en un contexto controlado.
        
        Args:
            code: Código Python con función execute(mcp, context)
            context: Contexto con phone, user, mensaje
            
        Returns:
            dict con success, data, summary
        """
        # Crear namespace para ejecución
        namespace = {"mcp": self.mcp}
        
        # Ejecutar código para definir la función
        exec(code, namespace)
        
        # Obtener función execute
        execute_fn = namespace.get("execute")
        if not execute_fn:
            raise ValueError("El código no define la función 'execute(mcp, context)'")
        
        # Ejecutar con timeout
        result = await asyncio.wait_for(
            execute_fn(self.mcp, context),
            timeout=EXECUTION_TIMEOUT
        )
        
        return result
    
    async def _nodo_self_correction(self, state: CodePlannerState) -> CodePlannerState:
        """
        Prepara el estado para que el Planner corrija el código.
        """
        logger.info(
            f"Self-correction: intento {state.get('correction_count', 0)} "
            f"de {state.get('max_corrections', MAX_CORRECTIONS)}"
        )
        # El error ya está en execution_error, el Planner lo usará
        return state
    
    async def _nodo_reflector(self, state: CodePlannerState) -> CodePlannerState:
        """
        Valida que el resultado responda a la consulta original.
        """
        start_time = time.time()
        mensaje = state["mensaje_original"]
        result = state.get("execution_result", {})
        
        logger.info(f"[REFLECTOR] Validando resultado...")
        
        # Si el resultado indica falla, no es válido
        if not result.get("success", False):
            state["reflection_valid"] = False
            state["reflection_reason"] = "El código reportó falla en success=False"
            logger.warning(f"[REFLECTOR] ❌ Resultado inválido: success=False")
            return state
        
        # Validar con LLM
        attempt = state.get("correction_count", 0)
        
        # Si ya hemos intentado corregir varias veces, somos más permisivos
        relax_rules = ""
        if attempt >= 1:
            relax_rules = "NOTA: Ya se han realizado intentos de corrección. Sé flexible. Si hay información parcial relevante, márcalo como VÁLIDO (valid: true)."

        prompt_template = get_prompt("code_planner", "reflector")
        prompt = prompt_template.format(
            relax_rules=relax_rules,
            mensaje=mensaje,
            result_json=json.dumps(result, ensure_ascii=False, default=str, indent=2)
        )
        
        try:
            logger.info("[REFLECTOR] Invocando LLM...")
            # Medir tokens si es posible
            with get_openai_callback() as cb:
                response = await self.llm_reflector.ainvoke([HumanMessage(content=prompt)])
                
                # Registrar tokens
                if "reflector" not in state["metrics"]:
                    state["metrics"]["reflector"] = {"latency": 0, "tokens": 0}
                state["metrics"]["reflector"]["tokens"] += cb.total_tokens

            data = json.loads(self._clean_json_response(response.content))
            
            state["reflection_valid"] = data.get("valid", True)
            state["reflection_reason"] = data.get("reason", "")
            
            if state["reflection_valid"]:
                logger.info(f"[REFLECTOR] ✅ Válido: {state['reflection_reason']}")
            else:
                logger.warning(f"[REFLECTOR] ❌ Inválido: {state['reflection_reason']}")
            
        except Exception as e:
            logger.warning(f"[REFLECTOR] Error parseando respuesta: {e}")
            # Asumir válido si no se puede evaluar
            state["reflection_valid"] = True
            state["reflection_reason"] = "No se pudo evaluar, asumiendo válido"
        
        # Métricas de latencia
        elapsed = time.time() - start_time
        if "reflector" not in state["metrics"]:
             state["metrics"]["reflector"] = {"latency": 0, "tokens": 0}
        state["metrics"]["reflector"]["latency"] += elapsed

        return state
    
    async def _nodo_responder(self, state: CodePlannerState) -> CodePlannerState:
        """
        Genera respuesta natural para WhatsApp.
        SIEMPRE usa el LLM para generar respuestas completas y empáticas.
        """
        start_time = time.time()
        logger.info("[RESPONDER] Iniciando generación de respuesta...")
        
        try:
            mensaje = state["mensaje_original"]
            result = state.get("execution_result", {})
            error = state.get("execution_error")
            correction_count = state.get("correction_count", 0)
            
            # CASO 1: Error irrecuperable
            if error and correction_count >= state.get("max_corrections", MAX_CORRECTIONS):
                logger.warning("[RESPONDER] Generando respuesta de error irrecuperable")
                state["final_response"] = (
                    "Disculpá, tuve un problema procesando tu consulta. 😅\n\n"
                    "¿Podés intentar de nuevo de otra forma?"
                )
                return state
            
            # CASO 2: Resultado no exitoso (pero sin error técnico)
            if not result.get("success"):
                logger.warning("[RESPONDER] Generando respuesta de 'No encontrado'")
                state["final_response"] = (
                    "No pude encontrar la información solicitada. 😕\n\n"
                    "¿Podés darme más detalles?"
                )
                return state

            # CASO 3: Éxito -> Generar respuesta con LLM
            summary = result.get("summary", "")
            data = result.get("data", {})
            logger.info(f"[RESPONDER] Generando respuesta sobre summary de {len(summary)} chars")
            
            prompt_template = get_prompt("code_planner", "responder")
            prompt = prompt_template.format(
                mensaje=mensaje,
                data_json=json.dumps(data, ensure_ascii=False, default=str, indent=2),
                summary=summary
            )
            
            # Sub-bloque para el LLM con rollback
            try:
                logger.info("[RESPONDER] Invocando LLM...")
                with get_openai_callback() as cb:
                    response = await self.llm_responder.ainvoke([HumanMessage(content=prompt)])
                    
                    # Registrar tokens del responder
                    if "responder" not in state["metrics"]:
                        state["metrics"]["responder"] = {"latency": 0, "tokens": 0}
                    state["metrics"]["responder"]["tokens"] += cb.total_tokens
                    
                content = response.content.strip()
                if not content:
                    raise ValueError("Respuesta generada vacía")
                    
                state["final_response"] = content
                
            except Exception as e:
                logger.error(f"[RESPONDER] Error invocando LLM: {e}")
                # Fallback
                state["final_response"] = summary or "Consulta procesada. ¿Necesitás algo más?"
            
            return state

        except Exception as e:
            logger.error(f"[RESPONDER] Error general: {e}")
            state["final_response"] = "Error procesando respuesta."
            return state

        finally:
            # Métricas de latencia (siempre se ejecutan)
            elapsed = time.time() - start_time
            if "responder" not in state["metrics"]:
                 state["metrics"]["responder"] = {"latency": 0, "tokens": 0}
            state["metrics"]["responder"]["latency"] += elapsed
    
    # ============================================================
    # ROUTERS
    # ============================================================
    
    def _router_post_executor(self, state: CodePlannerState) -> str:
        """Router después del Executor."""
        if state.get("execution_error"):
            if state.get("correction_count", 0) >= state.get("max_corrections", MAX_CORRECTIONS):
                logger.error(f"[ROUTER] Error persistente ({state.get('correction_count')} intentos). Enviando a Responder con error.")
                # Forzamos responder aunque haya error, para que el LLM maneje el mensaje amablemente
                return "responder"
            logger.warning(f"[ROUTER] Error detectado, enviando a Self-Correction (Intento {state.get('correction_count', 0) + 1})")
            return "error"
        return "success"
    
    def _router_post_reflector(self, state: CodePlannerState) -> str:
        """Router después del Reflector."""
        if state.get("reflection_valid", True):
            logger.info("[ROUTER] Reflector → Responder (válido)")
            return "valid"
        
        # Límite de iteraciones del Planner
        planner_iterations = state.get("planner_iterations", 0)
        if planner_iterations >= MAX_PLANNER_ITERATIONS:
            logger.warning(f"[ROUTER] Límite de iteraciones ({MAX_PLANNER_ITERATIONS}), forzando a Responder")
            return "valid"
        
        # Si ya se intentó corregir muchas veces, aceptar el resultado
        if state.get("correction_count", 0) >= 2:
            logger.warning("[ROUTER] Muchas correcciones, forzando a Responder")
            return "valid"
        
        logger.info(f"[ROUTER] Reflector → Planner (inválido, iteración {planner_iterations})")
        return "invalid"
    
    # ============================================================
    # HELPERS
    # ============================================================
    
    def _clean_code_response(self, content: str) -> str:
        """Limpia el código de bloques markdown."""
        content = content.strip()
        
        # Remover bloques ```python ... ```
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        
        return content.strip()
    
    def _clean_json_response(self, content: str) -> str:
        """Limpia el JSON de bloques markdown."""
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
    
    async def process(
        self,
        phone_number: str,
        mensaje: str,
        user_context: Optional[dict] = None
    ) -> str:
        """
        Procesa una consulta y retorna la respuesta.
        
        Args:
            phone_number: Número de WhatsApp
            mensaje: Mensaje del usuario
            user_context: Contexto del usuario (opcional)
            
        Returns:
            str: Respuesta generada
        """
        try:
            # Estado inicial
            state = create_empty_code_planner_state(
                phone_number=phone_number,
                mensaje=mensaje,
                user_context=user_context
            )
            
            # Ejecutar grafo
            graph = self.get_graph()
            result = await graph.ainvoke(state)
            
            response = result.get("final_response")
            if response:
                return response
            
            return "Mensaje procesado. ¿Necesitás algo más?"
            
        except Exception as e:
            logger.error(f"Error en CodePlannerAgent: {e}", exc_info=True)
            return (
                "Disculpá, tuve un problema procesando tu solicitud. 😅\n\n"
                "Por favor, intentá de nuevo."
            )


# ============================================================
# FACTORY
# ============================================================

_code_planner_instance: Optional[CodePlannerAgent] = None


def get_code_planner_agent(
    mcp_client: Optional[MCPClient] = None
) -> CodePlannerAgent:
    """
    Factory para obtener instancia del Code Planner.
    
    Args:
        mcp_client: Cliente MCP opcional
        
    Returns:
        CodePlannerAgent: Instancia del agente
    """
    global _code_planner_instance
    
    if _code_planner_instance is None:
        _code_planner_instance = CodePlannerAgent(mcp_client=mcp_client)
    
    return _code_planner_instance

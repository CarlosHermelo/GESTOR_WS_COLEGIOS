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
from typing import Optional, Any, Callable

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from app.llm.factory import get_tracked_llm
from app.mcp_client import MCPClient, get_mcp_client, ToolResult
from app.agents.states import (
    CodePlannerState,
    create_empty_code_planner_state,
)


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
- kg_query: Busca información en el Knowledge Graph del colegio
- crear_ticket: Crea un ticket administrativo
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
            logger.info(f"[PLANNER] Corrigiendo error previo: {error_previo[:200]}...")
        
        # Contexto de reflexión previa (si el Reflector rechazó)
        reflection_context = ""
        if state.get("reflection_reason") and not state.get("reflection_valid", True):
            reflection_context = f"""
⚠️ EL RESULTADO ANTERIOR NO RESPONDIÓ A LA CONSULTA:
 Razón: {state.get('reflection_reason')}

Genera código que responda mejor a la consulta original.
"""
            logger.info(f"[PLANNER] Corrigiendo por reflexión: {state.get('reflection_reason')}")
        
        prompt = f"""Eres un Code Planner experto. Genera código Python para resolver la consulta del usuario.

CONSULTA: {mensaje}

CONTEXTO DEL USUARIO:
- Teléfono: {state['phone_number']}
- Datos: {json.dumps(user_context, ensure_ascii=False, default=str)}

HERRAMIENTAS MCP DISPONIBLES:
{tools_desc}

{error_context}
{reflection_context}

REGLAS:
1. Genera SOLO una función async llamada `execute(mcp, context)` que retorne un dict
2. Usa `await mcp.call_tool("nombre_tool", {{"param": "valor"}})` para invocar tools
3. El resultado de call_tool tiene: .success (bool), .data (dict/Any), .error (str/None)
4. La función debe retornar un dict con:
   - "success": bool
   - "data": datos obtenidos
   - "summary": resumen breve del resultado
5. Maneja errores con try/except
6. NO uses imports externos, todo está disponible en el contexto

EJEMPLO:
```python
async def execute(mcp, context):
    # Consultar estado de cuenta
    result = await mcp.call_tool("consultar_estado_cuenta", {{"whatsapp": context["phone"]}})
    
    if not result.success:
        return {{"success": False, "data": None, "summary": f"Error: {{result.error}}"}}
    
    return {{
        "success": True,
        "data": result.data,
        "summary": f"Deuda total: ${{result.data.get('deuda_total', 0):,.0f}}"
    }}
```

IMPORTANTE: Genera SOLO el código Python, sin explicaciones adicionales.
"""
        
        try:
            response = await self.llm_planner.ainvoke([HumanMessage(content=prompt)])
            code = self._clean_code_response(response.content)
            
            state["generated_code"] = code
            state["code_reasoning"] = f"Código generado para: {mensaje[:50]}..."
            
            # Logging detallado del código generado
            logger.info(f"[PLANNER] Código generado ({len(code)} chars)")
            if code:
                # Log primeras líneas del código (en INFO para que se vea)
                code_preview = code[:200] + "..." if len(code) > 200 else code
                logger.info(f"[PLANNER] Preview del código:\n{code_preview}")
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
        
        return state
    
    async def _nodo_executor(self, state: CodePlannerState) -> CodePlannerState:
        """
        Ejecuta el código generado por el Planner.
        """
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
                logger.info(f"[EXECUTOR] Summary: {result.get('summary', '')[:200]}")
            
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

        prompt = f"""Eres el asistente del Colegio. Evalúa si el resultado responde a la consulta del usuario.
{relax_rules}

CONSULTA ORIGINAL: {mensaje}

RESULTADO OBTENIDO:
{json.dumps(result, ensure_ascii=False, default=str, indent=2)}

Responde SOLO con JSON:
{{"valid": true/false, "reason": "explicación breve"}}
"""
        
        try:
            response = await self.llm_reflector.ainvoke([HumanMessage(content=prompt)])
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
        
        return state
    
    async def _nodo_responder(self, state: CodePlannerState) -> CodePlannerState:
        """
        Genera respuesta natural para WhatsApp.
        SIEMPRE usa el LLM para generar respuestas completas y empáticas.
        """
        mensaje = state["mensaje_original"]
        result = state.get("execution_result", {})
        error = state.get("execution_error")
        
        # Si hubo error irrecuperable
        if error and state.get("correction_count", 0) >= state.get("max_corrections", MAX_CORRECTIONS):
            state["final_response"] = (
                "Disculpá, tuve un problema procesando tu consulta. 😅\n\n"
                "¿Podés intentar de nuevo de otra forma?"
            )
            return state
        
        # Si hay resultado exitoso, SIEMPRE usar LLM para respuesta completa
        if result.get("success"):
            summary = result.get("summary", "")
            data = result.get("data", {})
            
            # SIEMPRE generar respuesta con LLM para que responda a TODAS las partes de la consulta
            prompt = f"""Eres el asistente del Colegio. Genera una respuesta natural y COMPLETA para WhatsApp.

CONSULTA ORIGINAL DEL USUARIO: {mensaje}

DATOS OBTENIDOS DEL SISTEMA:
{json.dumps(data, ensure_ascii=False, default=str, indent=2)}

RESUMEN DE LA OPERACIÓN: {summary}

REGLAS IMPORTANTES:
1. **Responde a TODAS las partes de la consulta del usuario**, no solo a los datos obtenidos
2. Si el usuario preguntó algo que NO está en los datos (ej: ubicación, horarios, lugar de atención):
   - Indica amablemente que consultarás con el área correspondiente
   - O sugiere que contacte al colegio directamente para esa información específica
3. Tono amigable, profesional y empático
4. Usa emojis apropiados pero con moderación (máximo 3-4)
5. Máximo 4 párrafos cortos y claros
6. Resalta datos importantes con *negritas*
7. Si hay inconsistencias en los datos (ej: deuda total pero 0 cuotas), acláralas o indica que lo verificarás
8. Termina ofreciendo ayuda adicional o indicando próximos pasos
"""
            
            try:
                response = await self.llm_responder.ainvoke([HumanMessage(content=prompt)])
                state["final_response"] = response.content.strip()
            except Exception as e:
                logger.error(f"Error en Responder: {e}")
                # Fallback al summary si falla el LLM
                state["final_response"] = summary or "Consulta procesada. ¿Necesitás algo más?"
        else:
            state["final_response"] = (
                "No pude encontrar la información solicitada. 😕\n\n"
                "¿Podés darme más detalles?"
            )
        
        return state
    
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

"""
Especialista Financiero - Subgrafo para consultas de pagos y cuotas.
Maneja: estado de cuenta, links de pago, confirmaciones.
"""
import json
import logging
from typing import Optional

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from app.llm.factory import get_llm, get_tracked_llm
from app.adapters.erp_interface import ERPClientInterface
from app.adapters.mock_erp_adapter import get_erp_client
from app.agents.states import (
    SpecialistState,
    SpecialistReport,
    SubPlan,
    ActionPlan,
    SpecialistType,
    create_specialist_report,
)


logger = logging.getLogger(__name__)


class FinancieroSubgraph:
    """
    Subgrafo del Especialista Financiero.
    
    Responsabilidades:
    - Consultar estado de cuenta
    - Obtener links de pago
    - Registrar confirmaciones de pago
    - Informar vencimientos y montos
    """
    
    def __init__(self, erp_client: Optional[ERPClientInterface] = None):
        """
        Inicializa el especialista financiero.
        
        Args:
            erp_client: Cliente ERP. Si no se proporciona, usa el singleton.
        """
        self.erp = erp_client or get_erp_client()
        # Usar TrackedLLM para tracking de tokens
        self.llm = get_tracked_llm("financiero_planificar", "specialist")
        self.graph = self._build_graph()
        
        logger.info("FinancieroSubgraph inicializado")
    
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
        
        prompt = f"""Eres el Especialista Financiero de un colegio. 
Tu tarea es planificar cómo resolver esta meta:

META: {goal}
PARÁMETROS: {json.dumps(params, ensure_ascii=False)}

Herramientas disponibles:
1. consultar_estado_cuenta - Obtiene cuotas pendientes del responsable
2. obtener_link_pago - Genera link de pago para una cuota específica
3. registrar_confirmacion_pago - Registra que el padre confirmó un pago

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
                specialist=SpecialistType.FINANCIERO.value,
                goal_received=goal,
                actions=plan_data.get("actions", []),
                reasoning=plan_data.get("reasoning", "")
            )
            state["current_action_index"] = 0
            
            logger.info(f"SubPlan financiero: {len(plan_data.get('actions', []))} acciones")
            
        except Exception as e:
            logger.error(f"Error planificando: {e}")
            # Plan por defecto: consultar estado de cuenta
            state["sub_plan"] = SubPlan(
                specialist=SpecialistType.FINANCIERO.value,
                goal_received=goal,
                actions=[
                    ActionPlan(
                        tool="consultar_estado_cuenta",
                        params={"whatsapp": state["phone_number"]},
                        description="Consultar estado de cuenta del responsable"
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
        
        # Inyectar phone_number si no está
        if "whatsapp" not in params and tool_name in ["consultar_estado_cuenta"]:
            params["whatsapp"] = state["phone_number"]
        
        logger.info(f"Ejecutando acción {idx + 1}/{len(actions)}: {tool_name}")
        
        result = {"tool": tool_name, "success": False, "data": None, "error": None}
        
        try:
            if tool_name == "consultar_estado_cuenta":
                result["data"] = await self._tool_consultar_estado_cuenta(
                    params.get("whatsapp", state["phone_number"])
                )
                result["success"] = True
                
            elif tool_name == "obtener_link_pago":
                result["data"] = await self._tool_obtener_link_pago(
                    params.get("cuota_id", "")
                )
                result["success"] = True
                
            elif tool_name == "registrar_confirmacion_pago":
                result["data"] = await self._tool_registrar_confirmacion(
                    params.get("cuota_id", ""),
                    state["phone_number"]
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
            summary = self._format_financial_summary(combined_data)
            error = None
        else:
            summary = "No se pudo completar la consulta financiera."
            errors = [r.get("error") for r in action_results if r.get("error")]
            error = "; ".join(errors) if errors else "Error desconocido"
        
        state["report"] = create_specialist_report(
            specialist=SpecialistType.FINANCIERO.value,
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
    
    async def _tool_consultar_estado_cuenta(self, whatsapp: str) -> dict:
        """Consulta estado de cuenta del responsable."""
        from app.config import settings
        
        # MODO MOCK: Retornar datos simulados
        if settings.MOCK_MODE:
            return self._get_mock_estado_cuenta(whatsapp)
        
        # MODO REAL: Consultar ERP
        try:
            responsable = await self.erp.get_responsable_by_whatsapp(whatsapp)
        except Exception as e:
            logger.warning(f"ERP no disponible, usando mock: {e}")
            return self._get_mock_estado_cuenta(whatsapp)
        
        if not responsable:
            return {
                "found": False,
                "message": "No encontré tu número registrado en el sistema."
            }
        
        alumnos = responsable.get("alumnos", [])
        resultado = {
            "found": True,
            "responsable": responsable.get("nombre", ""),
            "alumnos": [],
            "deuda_total": 0
        }
        
        for alumno in alumnos:
            cuotas = await self.erp.get_alumno_cuotas(
                alumno["id"],
                estado="pendiente"
            )
            
            alumno_data = {
                "id": alumno["id"],
                "nombre": f"{alumno.get('nombre', '')} {alumno.get('apellido', '')}".strip(),
                "grado": alumno.get("grado", ""),
                "cuotas_pendientes": []
            }
            
            for cuota in cuotas:
                monto = cuota.get("monto", 0)
                resultado["deuda_total"] += monto
                alumno_data["cuotas_pendientes"].append({
                    "id": cuota.get("id", ""),
                    "numero": cuota.get("numero_cuota", "?"),
                    "monto": monto,
                    "vencimiento": cuota.get("fecha_vencimiento", ""),
                    "link_pago": cuota.get("link_pago", "")
                })
            
            resultado["alumnos"].append(alumno_data)
        
        return resultado
    
    async def _tool_obtener_link_pago(self, cuota_id: str) -> dict:
        """Obtiene link de pago para una cuota."""
        from app.config import settings
        
        # MODO MOCK
        if settings.MOCK_MODE:
            logger.info(f"[MOCK] Retornando link de pago para cuota {cuota_id}")
            return {
                "found": True,
                "cuota_id": cuota_id,
                "monto": 45000,
                "vencimiento": "15/03/2026",
                "link_pago": f"https://pago.mock/{cuota_id}"
            }
        
        # MODO REAL
        try:
            cuota = await self.erp.get_cuota(cuota_id)
        except Exception as e:
            logger.warning(f"ERP no disponible: {e}")
            return {"found": False, "message": "ERP no disponible"}
        
        if not cuota:
            return {"found": False, "message": "Cuota no encontrada"}
        
        return {
            "found": True,
            "cuota_id": cuota_id,
            "monto": cuota.get("monto", 0),
            "vencimiento": cuota.get("fecha_vencimiento", ""),
            "link_pago": cuota.get("link_pago", "")
        }
    
    async def _tool_registrar_confirmacion(
        self, 
        cuota_id: str, 
        whatsapp: str
    ) -> dict:
        """Registra confirmación de pago."""
        from app.config import settings
        
        # MODO MOCK
        if settings.MOCK_MODE:
            logger.info(f"[MOCK] Registrando confirmación de pago para cuota {cuota_id}")
            return {
                "registered": True,
                "cuota_id": cuota_id,
                "message": "Pago registrado (MOCK), pendiente de validación"
            }
        
        # MODO REAL
        from app.models.interacciones import Interaccion
        from app.database import async_session_maker
        
        try:
            async with async_session_maker() as session:
                interaccion = Interaccion(
                    whatsapp_from=whatsapp,
                    erp_cuota_id=cuota_id,
                    tipo="confirmacion_pago",
                    contenido="Padre confirmó haber realizado el pago",
                    agente="especialista_financiero",
                    extra_data={"cuota_id": cuota_id, "estado": "pendiente_validacion"}
                )
                session.add(interaccion)
                await session.commit()
            
            return {
                "registered": True,
                "cuota_id": cuota_id,
                "message": "Pago registrado, pendiente de validación"
            }
        except Exception as e:
            return {
                "registered": False,
                "error": str(e)
            }
    
    # ============================================================
    # HELPERS
    # ============================================================
    
    def _clean_json_response(self, content: str) -> str:
        """Limpia marcadores de código de la respuesta."""
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            # Remover primera y última línea si son ```
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        return content.strip()
    
    def _get_mock_estado_cuenta(self, whatsapp: str) -> dict:
        """Retorna datos mock de estado de cuenta para testing."""
        logger.info(f"[MOCK] Retornando estado de cuenta simulado para {whatsapp}")
        
        return {
            "found": True,
            "responsable": "María García",
            "alumnos": [
                {
                    "id": "mock-alumno-001",
                    "nombre": "Juan Pérez García",
                    "grado": "3ro A",
                    "cuotas_pendientes": [
                        {
                            "id": "mock-cuota-003",
                            "numero": 3,
                            "monto": 45000,
                            "vencimiento": "15/03/2026",
                            "link_pago": "https://pago.mock/cuota-003"
                        },
                        {
                            "id": "mock-cuota-004",
                            "numero": 4,
                            "monto": 45000,
                            "vencimiento": "15/04/2026",
                            "link_pago": "https://pago.mock/cuota-004"
                        }
                    ]
                },
                {
                    "id": "mock-alumno-002",
                    "nombre": "Ana Pérez García",
                    "grado": "1ro B",
                    "cuotas_pendientes": [
                        {
                            "id": "mock-cuota-103",
                            "numero": 3,
                            "monto": 42000,
                            "vencimiento": "15/03/2026",
                            "link_pago": "https://pago.mock/cuota-103"
                        }
                    ]
                }
            ],
            "deuda_total": 132000
        }
    
    def _format_financial_summary(self, data: dict) -> str:
        """Formatea los datos financieros en resumen legible."""
        estado = data.get("consultar_estado_cuenta", {})
        
        if not estado.get("found"):
            return estado.get("message", "No se encontró información.")
        
        lines = ["📋 Estado de cuenta:\n"]
        
        for alumno in estado.get("alumnos", []):
            nombre = alumno.get("nombre", "Alumno")
            grado = alumno.get("grado", "")
            lines.append(f"👤 {nombre} ({grado}):")
            
            for cuota in alumno.get("cuotas_pendientes", []):
                monto = cuota.get("monto", 0)
                venc = cuota.get("vencimiento", "")
                num = cuota.get("numero", "?")
                lines.append(f"  • Cuota {num}: ${monto:,.0f} (vence {venc})")
            
            lines.append("")
        
        deuda = estado.get("deuda_total", 0)
        if deuda > 0:
            lines.append(f"💰 Total adeudado: ${deuda:,.0f}")
            lines.append("\n¿Necesitás los links de pago?")
        else:
            lines = ["✅ ¡Estás al día! No hay cuotas pendientes. 🎉"]
        
        return "\n".join(lines)
    
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
                specialist=SpecialistType.FINANCIERO.value,
                success=False,
                data={},
                summary="Error interno del especialista",
                error="No se generó reporte",
                requires_replan=True
            )
        except Exception as e:
            logger.error(f"Error en FinancieroSubgraph: {e}", exc_info=True)
            return create_specialist_report(
                specialist=SpecialistType.FINANCIERO.value,
                success=False,
                data={},
                summary="Error ejecutando especialista financiero",
                error=str(e),
                requires_replan=True
            )

"""
Especialista Institucional - Subgrafo para información del colegio.
Maneja: horarios, calendario, autoridades, información general.

NOTA: Este especialista usa un placeholder para la BD vectorial.
La implementación completa se hará cuando la BD vectorial esté lista.
"""
import json
import logging
from typing import Optional

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from app.llm.factory import get_llm, get_tracked_llm
from app.agents.states import (
    SpecialistState,
    SpecialistReport,
    SubPlan,
    ActionPlan,
    SpecialistType,
    create_specialist_report,
)


logger = logging.getLogger(__name__)


# ============================================================
# DATOS MOCK - Reemplazar con BD Vectorial
# ============================================================

MOCK_INFO_INSTITUCIONAL = {
    "horarios": {
        "primaria": {
            "turno_mañana": "7:30 - 12:30",
            "turno_tarde": "13:00 - 18:00"
        },
        "secundaria": {
            "turno_mañana": "7:15 - 13:15",
            "turno_tarde": "13:30 - 19:30"
        },
        "administracion": "8:00 - 17:00 (Lunes a Viernes)"
    },
    "calendario": {
        "inicio_clases": "4 de marzo de 2026",
        "fin_clases": "11 de diciembre de 2026",
        "receso_invierno": "14 al 25 de julio de 2026",
        "feriados_importantes": [
            "1 de mayo - Día del Trabajador",
            "25 de mayo - Revolución de Mayo",
            "9 de julio - Día de la Independencia"
        ]
    },
    "autoridades": {
        "director_general": "Dr. Roberto Martínez",
        "directora_primaria": "Lic. María García",
        "director_secundaria": "Prof. Juan López",
        "coordinadora_administrativa": "Sra. Ana Fernández"
    },
    "contacto": {
        "telefono": "(011) 4555-1234",
        "email": "info@colegio.edu.ar",
        "direccion": "Av. Siempreviva 742, CABA"
    }
}


class InstitucionalSubgraph:
    """
    Subgrafo del Especialista Institucional.
    
    Responsabilidades:
    - Informar horarios de clases
    - Consultar calendario escolar
    - Proporcionar información de autoridades
    - Responder consultas institucionales generales
    
    NOTA: Actualmente usa datos mock. Se integrará con BD vectorial.
    """
    
    def __init__(self):
        """Inicializa el especialista institucional."""
        # Usar TrackedLLM para tracking de tokens
        self.llm = get_tracked_llm("institucional_planificar", "specialist")
        self.graph = self._build_graph()
        self.info_db = MOCK_INFO_INSTITUCIONAL  # Placeholder para BD vectorial
        
        logger.info("InstitucionalSubgraph inicializado (modo mock)")
    
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
        
        prompt = f"""Eres el Especialista Institucional de un colegio.
Tu tarea es planificar cómo resolver esta meta:

META: {goal}
PARÁMETROS: {json.dumps(params, ensure_ascii=False)}

Herramientas disponibles:
1. buscar_horarios - Busca horarios de clases (primaria/secundaria/administración)
2. buscar_calendario - Busca fechas del calendario escolar
3. buscar_autoridades - Busca información de autoridades del colegio
4. buscar_contacto - Busca datos de contacto del colegio
5. buscar_info_general - Búsqueda semántica de información general (placeholder)

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
                specialist=SpecialistType.INSTITUCIONAL.value,
                goal_received=goal,
                actions=plan_data.get("actions", []),
                reasoning=plan_data.get("reasoning", "")
            )
            state["current_action_index"] = 0
            
            logger.info(f"SubPlan institucional: {len(plan_data.get('actions', []))} acciones")
            
        except Exception as e:
            logger.error(f"Error planificando: {e}")
            # Plan por defecto: búsqueda general
            state["sub_plan"] = SubPlan(
                specialist=SpecialistType.INSTITUCIONAL.value,
                goal_received=goal,
                actions=[
                    ActionPlan(
                        tool="buscar_info_general",
                        params={"query": goal},
                        description="Búsqueda general de información"
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
            if tool_name == "buscar_horarios":
                result["data"] = await self._tool_buscar_horarios(
                    params.get("nivel", None)
                )
                result["success"] = True
                
            elif tool_name == "buscar_calendario":
                result["data"] = await self._tool_buscar_calendario(
                    params.get("tipo", None)
                )
                result["success"] = True
                
            elif tool_name == "buscar_autoridades":
                result["data"] = await self._tool_buscar_autoridades(
                    params.get("cargo", None)
                )
                result["success"] = True
                
            elif tool_name == "buscar_contacto":
                result["data"] = await self._tool_buscar_contacto()
                result["success"] = True
                
            elif tool_name == "buscar_info_general":
                result["data"] = await self._tool_buscar_info_general(
                    params.get("query", state["goal"])
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
            summary = self._format_institucional_summary(combined_data, state["goal"])
            error = None
        else:
            summary = "No se pudo encontrar la información solicitada."
            errors = [r.get("error") for r in action_results if r.get("error")]
            error = "; ".join(errors) if errors else "Error desconocido"
        
        state["report"] = create_specialist_report(
            specialist=SpecialistType.INSTITUCIONAL.value,
            success=all_success,
            data=combined_data,
            summary=summary,
            error=error,
            requires_replan=not all_success
        )
        
        return state
    
    # ============================================================
    # HERRAMIENTAS (Tools) - MOCK
    # ============================================================
    
    async def _tool_buscar_horarios(self, nivel: Optional[str] = None) -> dict:
        """Busca horarios de clases."""
        horarios = self.info_db["horarios"]
        
        if nivel and nivel.lower() in horarios:
            return {
                "found": True,
                "nivel": nivel,
                "horarios": horarios[nivel.lower()]
            }
        
        return {
            "found": True,
            "horarios": horarios
        }
    
    async def _tool_buscar_calendario(self, tipo: Optional[str] = None) -> dict:
        """Busca información del calendario escolar."""
        calendario = self.info_db["calendario"]
        
        if tipo:
            tipo_lower = tipo.lower()
            for key, value in calendario.items():
                if tipo_lower in key.lower():
                    return {
                        "found": True,
                        "tipo": key,
                        "fecha": value
                    }
        
        return {
            "found": True,
            "calendario": calendario
        }
    
    async def _tool_buscar_autoridades(self, cargo: Optional[str] = None) -> dict:
        """Busca información de autoridades."""
        autoridades = self.info_db["autoridades"]
        
        if cargo:
            cargo_lower = cargo.lower()
            for key, value in autoridades.items():
                if cargo_lower in key.lower():
                    return {
                        "found": True,
                        "cargo": key.replace("_", " ").title(),
                        "nombre": value
                    }
        
        return {
            "found": True,
            "autoridades": {
                k.replace("_", " ").title(): v 
                for k, v in autoridades.items()
            }
        }
    
    async def _tool_buscar_contacto(self) -> dict:
        """Busca datos de contacto del colegio."""
        return {
            "found": True,
            "contacto": self.info_db["contacto"]
        }
    
    async def _tool_buscar_info_general(self, query: str) -> dict:
        """
        Búsqueda semántica de información general.
        
        PLACEHOLDER: En el futuro, esto consultará la BD vectorial.
        Por ahora, hace matching simple con keywords.
        """
        query_lower = query.lower()
        resultados = {}
        
        # Matching simple por keywords
        if any(kw in query_lower for kw in ["horario", "hora", "clase", "turno"]):
            resultados["horarios"] = self.info_db["horarios"]
            
        if any(kw in query_lower for kw in ["inicio", "fin", "vacacion", "feriado", "calendario"]):
            resultados["calendario"] = self.info_db["calendario"]
            
        if any(kw in query_lower for kw in ["director", "autoridad", "cargo"]):
            resultados["autoridades"] = self.info_db["autoridades"]
            
        if any(kw in query_lower for kw in ["contacto", "telefono", "email", "direccion"]):
            resultados["contacto"] = self.info_db["contacto"]
        
        if resultados:
            return {
                "found": True,
                "query": query,
                "resultados": resultados
            }
        
        # Si no hay match, devolver todo (el LLM seleccionará)
        return {
            "found": True,
            "query": query,
            "resultados": self.info_db,
            "nota": "Búsqueda general - BD vectorial no implementada"
        }
    
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
    
    def _format_institucional_summary(self, data: dict, goal: str) -> str:
        """Formatea el resumen de información institucional."""
        lines = []
        
        # Horarios
        if "buscar_horarios" in data:
            horarios_data = data["buscar_horarios"]
            if horarios_data.get("found"):
                lines.append("📅 **Horarios:**\n")
                horarios = horarios_data.get("horarios", {})
                
                if isinstance(horarios, dict):
                    if "primaria" in horarios:
                        lines.append("**Primaria:**")
                        for turno, hora in horarios["primaria"].items():
                            lines.append(f"  • {turno.replace('_', ' ').title()}: {hora}")
                    if "secundaria" in horarios:
                        lines.append("**Secundaria:**")
                        for turno, hora in horarios["secundaria"].items():
                            lines.append(f"  • {turno.replace('_', ' ').title()}: {hora}")
                    if "administracion" in horarios:
                        lines.append(f"**Administración:** {horarios['administracion']}")
                lines.append("")
        
        # Calendario
        if "buscar_calendario" in data:
            cal_data = data["buscar_calendario"]
            if cal_data.get("found"):
                lines.append("📆 **Calendario escolar:**\n")
                calendario = cal_data.get("calendario", {})
                
                if "inicio_clases" in calendario:
                    lines.append(f"• Inicio de clases: {calendario['inicio_clases']}")
                if "fin_clases" in calendario:
                    lines.append(f"• Fin de clases: {calendario['fin_clases']}")
                if "receso_invierno" in calendario:
                    lines.append(f"• Receso de invierno: {calendario['receso_invierno']}")
                lines.append("")
        
        # Autoridades
        if "buscar_autoridades" in data:
            auth_data = data["buscar_autoridades"]
            if auth_data.get("found"):
                if auth_data.get("cargo"):
                    lines.append(f"👤 **{auth_data['cargo']}:** {auth_data['nombre']}")
                else:
                    lines.append("👥 **Autoridades:**\n")
                    for cargo, nombre in auth_data.get("autoridades", {}).items():
                        lines.append(f"• {cargo}: {nombre}")
                lines.append("")
        
        # Contacto
        if "buscar_contacto" in data:
            cont_data = data["buscar_contacto"]
            if cont_data.get("found"):
                contacto = cont_data.get("contacto", {})
                lines.append("📞 **Contacto:**\n")
                if contacto.get("telefono"):
                    lines.append(f"• Tel: {contacto['telefono']}")
                if contacto.get("email"):
                    lines.append(f"• Email: {contacto['email']}")
                if contacto.get("direccion"):
                    lines.append(f"• Dirección: {contacto['direccion']}")
                lines.append("")
        
        # Búsqueda general
        if "buscar_info_general" in data and not lines:
            info_data = data["buscar_info_general"]
            if info_data.get("found"):
                lines.append("ℹ️ Información encontrada. ¿Necesitás algo específico?")
        
        if lines:
            return "\n".join(lines).strip()
        
        return "No encontré información específica sobre tu consulta. ¿Podrías reformularla?"
    
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
            user_context: Contexto del usuario
            
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
                specialist=SpecialistType.INSTITUCIONAL.value,
                success=False,
                data={},
                summary="Error interno del especialista",
                error="No se generó reporte",
                requires_replan=True
            )
        except Exception as e:
            logger.error(f"Error en InstitucionalSubgraph: {e}", exc_info=True)
            return create_specialist_report(
                specialist=SpecialistType.INSTITUCIONAL.value,
                success=False,
                data={},
                summary="Error ejecutando especialista institucional",
                error=str(e),
                requires_replan=True
            )

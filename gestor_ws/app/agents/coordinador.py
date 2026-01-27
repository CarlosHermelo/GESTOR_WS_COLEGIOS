"""
Agente Coordinador Autónomo - Capa 3 (LangGraph).
Maneja casos complejos que requieren múltiples pasos y escalamiento.
"""
import json
import logging
from typing import TypedDict, Optional, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from app.llm.factory import get_llm
from app.adapters.erp_interface import ERPClientInterface
from app.adapters.mock_erp_adapter import get_erp_client


logger = logging.getLogger(__name__)


class ConversationState(TypedDict):
    """Estado de la conversación para el grafo."""
    phone_number: str
    messages: list[str]
    categoria: Optional[str]
    prioridad: Optional[str]
    ticket_id: Optional[str]
    respuesta_admin: Optional[str]
    intentos_resolucion: int
    respuesta_final: Optional[str]
    erp_alumno_id: Optional[str]
    erp_responsable_id: Optional[str]
    error: Optional[str]


class AgenteAutonomo:
    """
    Agente autónomo que maneja casos complejos usando LangGraph.
    
    Flujo:
    1. Clasificar consulta → Determina categoría y prioridad
    2. Intentar resolver → Intenta resolución automática
    3. Crear ticket → Si no se puede resolver automáticamente
    4. Esperar admin → Espera respuesta del administrador
    5. Reformular → Reformula respuesta técnica a lenguaje amigable
    6. Enviar a padre → Envía respuesta final
    """
    
    def __init__(
        self,
        erp_client: Optional[ERPClientInterface] = None
    ):
        """
        Inicializa el agente autónomo.
        
        Args:
            erp_client: Cliente ERP opcional
        """
        self.erp = erp_client or get_erp_client()
        self.llm = get_llm()
        self.graph = self._build_graph()
        
        logger.info("AgenteAutonomo inicializado")
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo de estados con LangGraph."""
        workflow = StateGraph(ConversationState)
        
        # Agregar nodos
        workflow.add_node("clasificar", self.clasificar_consulta)
        workflow.add_node("intentar_resolver", self.intentar_resolucion)
        workflow.add_node("crear_ticket", self.crear_ticket)
        workflow.add_node("generar_respuesta_espera", self.generar_respuesta_espera)
        
        # Punto de entrada
        workflow.set_entry_point("clasificar")
        
        # Edges condicionales desde clasificar
        workflow.add_conditional_edges(
            "clasificar",
            self.decidir_ruta,
            {
                "resolver": "intentar_resolver",
                "escalar": "crear_ticket",
                "error": END
            }
        )
        
        # Edges condicionales desde intentar_resolver
        workflow.add_conditional_edges(
            "intentar_resolver",
            self.validar_resolucion,
            {
                "exito": END,
                "fallo": "crear_ticket"
            }
        )
        
        # Después de crear ticket, generar respuesta de espera
        workflow.add_edge("crear_ticket", "generar_respuesta_espera")
        workflow.add_edge("generar_respuesta_espera", END)
        
        return workflow.compile()
    
    async def clasificar_consulta(self, state: ConversationState) -> ConversationState:
        """
        Clasifica la consulta del usuario usando LLM.
        Determina categoría y prioridad.
        """
        try:
            ultimo_mensaje = state["messages"][-1] if state["messages"] else ""
            
            prompt = f"""
Clasifica esta consulta de un padre/responsable de alumnos:

Mensaje: {ultimo_mensaje}

Categorías posibles:
- plan_pago: Solicita plan de pagos, financiación
- reclamo: Queja sobre cobros, errores, mal servicio
- baja: Solicita dar de baja al alumno
- consulta_admin: Otra consulta que requiere administración

Prioridades:
- baja: Consultas generales
- media: Solicitudes normales
- alta: Urgencias, reclamos graves

Responde SOLO con JSON válido (sin markdown):
{{"categoria": "plan_pago|reclamo|baja|consulta_admin", "prioridad": "baja|media|alta", "requiere_humano": true|false, "razon": "breve explicación"}}
"""
            
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            
            # Parsear respuesta
            try:
                # Limpiar posibles marcadores de código
                content = response.content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()
                
                clasificacion = json.loads(content)
                
                state["categoria"] = clasificacion.get("categoria", "consulta_admin")
                state["prioridad"] = clasificacion.get("prioridad", "media")
                
                logger.info(
                    f"Consulta clasificada: {state['categoria']} "
                    f"(prioridad: {state['prioridad']})"
                )
                
            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando clasificación: {e}")
                state["categoria"] = "consulta_admin"
                state["prioridad"] = "media"
            
            return state
            
        except Exception as e:
            logger.error(f"Error clasificando consulta: {e}")
            state["error"] = str(e)
            state["categoria"] = "consulta_admin"
            state["prioridad"] = "media"
            return state
    
    def decidir_ruta(self, state: ConversationState) -> str:
        """Decide la ruta basada en la clasificación."""
        if state.get("error"):
            return "error"
        
        # Categorías que siempre escalan
        categorias_escalar = ["baja", "reclamo"]
        
        if state.get("categoria") in categorias_escalar:
            return "escalar"
        
        # Plan de pago intentamos resolver primero
        if state.get("categoria") == "plan_pago":
            return "resolver"
        
        # Por defecto, intentar resolver
        return "resolver"
    
    async def intentar_resolucion(self, state: ConversationState) -> ConversationState:
        """
        Intenta resolver la consulta automáticamente.
        Para ciertas categorías, podemos dar información útil.
        """
        state["intentos_resolucion"] = state.get("intentos_resolucion", 0) + 1
        
        categoria = state.get("categoria", "")
        
        try:
            if categoria == "plan_pago":
                # Informar sobre el proceso de plan de pagos
                state["respuesta_final"] = (
                    "Entiendo que necesitás un plan de pagos. 📝\n\n"
                    "Para solicitar un plan de pagos, necesito derivar tu "
                    "consulta al área administrativa.\n\n"
                    "Ellos evaluarán tu situación y te contactarán con "
                    "las opciones disponibles.\n\n"
                    "¿Querés que proceda con la solicitud?"
                )
                # Aunque damos respuesta, igual escalamos
                return state
            
            elif categoria == "consulta_admin":
                # Consultas administrativas generales
                state["respuesta_final"] = (
                    "Tu consulta requiere atención del área administrativa. 📋\n\n"
                    "Voy a crear un ticket para que te respondan a la brevedad.\n\n"
                    "Normalmente responden en menos de 24 horas hábiles."
                )
                return state
            
            # Si llegamos aquí, no pudimos resolver
            state["respuesta_final"] = None
            return state
            
        except Exception as e:
            logger.error(f"Error intentando resolución: {e}")
            state["respuesta_final"] = None
            return state
    
    def validar_resolucion(self, state: ConversationState) -> str:
        """Valida si la resolución fue exitosa."""
        # Para plan_pago y consulta_admin, siempre escalamos
        # aunque hayamos dado una respuesta inicial
        if state.get("categoria") in ["plan_pago", "consulta_admin"]:
            return "fallo"
        
        if state.get("respuesta_final"):
            return "exito"
        
        return "fallo"
    
    async def crear_ticket(self, state: ConversationState) -> ConversationState:
        """Crea un ticket de escalamiento."""
        try:
            from app.models.tickets import Ticket
            from app.database import async_session_maker
            
            async with async_session_maker() as session:
                ticket = Ticket.crear(
                    erp_alumno_id=state.get("erp_alumno_id", "desconocido"),
                    erp_responsable_id=state.get("erp_responsable_id"),
                    categoria=state.get("categoria", "consulta_admin"),
                    motivo=state["messages"][-1] if state["messages"] else "",
                    contexto={
                        "phone_number": state["phone_number"],
                        "mensajes": state["messages"],
                        "timestamp": datetime.now().isoformat()
                    },
                    prioridad=state.get("prioridad", "media")
                )
                
                session.add(ticket)
                await session.commit()
                await session.refresh(ticket)
                
                state["ticket_id"] = str(ticket.id)
                
                logger.info(f"Ticket creado: {ticket.id}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error creando ticket: {e}")
            state["error"] = f"Error creando ticket: {e}"
            return state
    
    async def generar_respuesta_espera(self, state: ConversationState) -> ConversationState:
        """Genera respuesta indicando que el ticket fue creado."""
        categoria = state.get("categoria", "")
        ticket_id = state.get("ticket_id", "")
        
        # Respuestas según categoría
        respuestas = {
            "plan_pago": (
                "✅ Registré tu solicitud de plan de pagos.\n\n"
                f"📝 Ticket: #{ticket_id[:8] if ticket_id else 'pendiente'}\n\n"
                "El área administrativa va a evaluar tu situación y te "
                "contactará por este medio con las opciones disponibles.\n\n"
                "⏰ Tiempo estimado de respuesta: 24-48 horas hábiles."
            ),
            "reclamo": (
                "📋 Tu reclamo fue registrado correctamente.\n\n"
                f"📝 Ticket: #{ticket_id[:8] if ticket_id else 'pendiente'}\n\n"
                "Un representante del colegio va a revisar tu caso y "
                "te contactará para darle solución.\n\n"
                "⏰ Tiempo estimado de respuesta: 24 horas hábiles."
            ),
            "baja": (
                "📝 Tu solicitud de baja fue registrada.\n\n"
                f"Ticket: #{ticket_id[:8] if ticket_id else 'pendiente'}\n\n"
                "El área administrativa se comunicará contigo para "
                "continuar con el proceso.\n\n"
                "⚠️ Recordá que pueden aplicarse políticas de baja anticipada."
            ),
            "consulta_admin": (
                "✅ Tu consulta fue derivada al área administrativa.\n\n"
                f"📝 Ticket: #{ticket_id[:8] if ticket_id else 'pendiente'}\n\n"
                "Te responderán a la brevedad por este medio.\n\n"
                "⏰ Tiempo estimado: 24-48 horas hábiles."
            )
        }
        
        state["respuesta_final"] = respuestas.get(
            categoria,
            respuestas["consulta_admin"]
        )
        
        return state
    
    async def procesar(
        self,
        whatsapp: str,
        mensaje: str,
        erp_alumno_id: Optional[str] = None,
        erp_responsable_id: Optional[str] = None
    ) -> str:
        """
        Procesa un mensaje complejo.
        
        Args:
            whatsapp: Número de WhatsApp
            mensaje: Texto del mensaje
            erp_alumno_id: ID del alumno (opcional)
            erp_responsable_id: ID del responsable (opcional)
            
        Returns:
            str: Respuesta del agente
        """
        try:
            state: ConversationState = {
                "phone_number": whatsapp,
                "messages": [mensaje],
                "categoria": None,
                "prioridad": None,
                "ticket_id": None,
                "respuesta_admin": None,
                "intentos_resolucion": 0,
                "respuesta_final": None,
                "erp_alumno_id": erp_alumno_id,
                "erp_responsable_id": erp_responsable_id,
                "error": None
            }
            
            result = await self.graph.ainvoke(state)
            
            respuesta = result.get("respuesta_final")
            if respuesta:
                return respuesta
            
            # Respuesta de fallback
            return (
                "Recibí tu mensaje y lo estoy procesando. 📝\n\n"
                "Si tu consulta requiere atención especial, "
                "un representante te contactará pronto."
            )
            
        except Exception as e:
            logger.error(f"Error en AgenteAutonomo: {e}", exc_info=True)
            return (
                "Disculpá, tuve un problema procesando tu solicitud. 😅\n\n"
                "Por favor, intentá de nuevo o escribí 'hablar con alguien' "
                "para que te atienda una persona."
            )
    
    async def procesar_respuesta_admin(
        self,
        ticket_id: str,
        respuesta_admin: str,
        phone_number: str
    ) -> str:
        """
        Reformula la respuesta del admin y la envía al padre.
        
        Args:
            ticket_id: ID del ticket
            respuesta_admin: Respuesta técnica del admin
            phone_number: Número de WhatsApp del padre
            
        Returns:
            str: Respuesta reformulada para WhatsApp
        """
        try:
            prompt = f"""
Eres asistente del colegio. Reformula esta respuesta técnica del administrador
en lenguaje amigable para WhatsApp (máximo 3 párrafos cortos).

Respuesta del administrador:
{respuesta_admin}

Reglas:
- Usa lenguaje simple y cercano
- Incluye emojis relevantes
- Sé conciso (es para WhatsApp)
- Termina con una nota positiva o próximo paso claro

Respuesta reformulada:
"""
            
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error reformulando respuesta: {e}")
            return respuesta_admin  # Retorna original si falla




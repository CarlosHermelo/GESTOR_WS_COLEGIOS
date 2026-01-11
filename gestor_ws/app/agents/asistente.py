"""
Asistente Virtual - Capa 2 (LLM + Herramientas).
Maneja consultas simples usando LLM con tool calling.
"""
import logging
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import create_tool_calling_agent, AgentExecutor

from app.llm.factory import get_llm
from app.adapters.erp_interface import ERPClientInterface
from app.adapters.mock_erp_adapter import get_erp_client


logger = logging.getLogger(__name__)


# System prompt para el asistente
SYSTEM_PROMPT = """Eres el asistente de cobranza del Colegio. Tu rol es ayudar a los padres con consultas sobre pagos y cuotas.

PUEDES:
- Informar cuotas pendientes y pagadas
- Enviar links de pago
- Registrar confirmaciones de pago
- Responder sobre vencimientos y montos
- Dar información del estado de cuenta

NO PUEDES:
- Modificar montos de cuotas
- Ofrecer planes de pago (debes escalar)
- Dar de baja alumnos
- Resolver reclamos complejos
- Aprobar descuentos o becas

REGLAS:
1. Sé conciso y amigable. Las respuestas deben ser cortas para WhatsApp.
2. Usa emojis con moderación (📋, 💰, ✅, 📅)
3. Si no puedes resolver algo, usa la herramienta escalar_a_agente
4. Siempre verifica el contexto del usuario antes de dar información
5. Formatea montos con separador de miles (ej: $45,000)

CONTEXTO DEL USUARIO:
- WhatsApp: {whatsapp}
"""


class AsistenteVirtual:
    """
    Asistente Virtual que usa LLM para responder consultas.
    Utiliza herramientas para consultar ERP y realizar acciones.
    """
    
    def __init__(
        self,
        erp_client: Optional[ERPClientInterface] = None
    ):
        """
        Inicializa el asistente.
        
        Args:
            erp_client: Cliente ERP opcional. Si no se proporciona,
                       usa el singleton global.
        """
        self.erp = erp_client or get_erp_client()
        self.llm = get_llm()
        self.tools = self._get_tools()
        self.agent_executor = self._create_agent()
        
        logger.info("AsistenteVirtual inicializado")
    
    def _get_tools(self) -> list:
        """Obtiene las herramientas disponibles para el agente."""
        # Importar aquí para evitar imports circulares
        from app.tools.consultar_erp import get_erp_tools
        return get_erp_tools(self.erp)
    
    def _create_agent(self) -> AgentExecutor:
        """Crea el agente con herramientas."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
    
    async def responder(
        self,
        whatsapp: str,
        mensaje: str,
        historial: Optional[list[dict]] = None
    ) -> str:
        """
        Procesa un mensaje y retorna la respuesta.
        
        Args:
            whatsapp: Número de WhatsApp del usuario
            mensaje: Texto del mensaje entrante
            historial: Historial de conversación (opcional)
            
        Returns:
            str: Respuesta generada por el asistente
        """
        try:
            logger.info(f"Procesando mensaje de {whatsapp}: '{mensaje[:50]}...'")
            
            # Construir historial de chat si existe
            chat_history = []
            if historial:
                for msg in historial[-5:]:  # Últimos 5 mensajes
                    if msg.get("from") == "usuario":
                        chat_history.append(HumanMessage(content=msg["text"]))
                    else:
                        chat_history.append(AIMessage(content=msg["text"]))
            
            # Invocar el agente
            result = await self.agent_executor.ainvoke({
                "input": mensaje,
                "whatsapp": whatsapp,
                "chat_history": chat_history
            })
            
            response = result.get("output", "")
            logger.info(f"Respuesta generada para {whatsapp}: '{response[:100]}...'")
            
            return response
            
        except Exception as e:
            logger.error(f"Error en asistente para {whatsapp}: {e}", exc_info=True)
            return self._get_error_response()
    
    def _get_error_response(self) -> str:
        """Respuesta genérica de error."""
        return (
            "Disculpá, tuve un problema procesando tu consulta. 😅\n\n"
            "¿Podés intentar de nuevo? Si el problema persiste, "
            "escribí 'hablar con alguien' para que te atienda un humano."
        )
    
    async def get_estado_cuenta_rapido(self, whatsapp: str) -> str:
        """
        Obtiene estado de cuenta de forma directa (sin LLM).
        Útil para consultas simples que no requieren razonamiento.
        
        Args:
            whatsapp: Número de WhatsApp
            
        Returns:
            str: Estado de cuenta formateado
        """
        try:
            # Buscar responsable
            responsable = await self.erp.get_responsable_by_whatsapp(whatsapp)
            
            if not responsable:
                return (
                    "No encontré tu número registrado en el sistema. 🤔\n\n"
                    "Por favor, contactá a administración para verificar "
                    "tus datos."
                )
            
            alumnos = responsable.get("alumnos", [])
            if not alumnos:
                return "No encontré alumnos asociados a tu cuenta."
            
            # Construir respuesta
            mensaje = "📋 **Estado de cuenta:**\n\n"
            deuda_total = 0
            
            for alumno in alumnos:
                cuotas = await self.erp.get_alumno_cuotas(
                    alumno["id"],
                    estado="pendiente"
                )
                
                if cuotas:
                    nombre = f"{alumno.get('nombre', '')} {alumno.get('apellido', '')}".strip()
                    grado = alumno.get("grado", "")
                    mensaje += f"👤 **{nombre}** ({grado}):\n"
                    
                    for cuota in cuotas:
                        monto = cuota.get("monto", 0)
                        deuda_total += monto
                        venc = cuota.get("fecha_vencimiento", "")
                        mensaje += f"  • Cuota {cuota.get('numero_cuota', '?')}: "
                        mensaje += f"${monto:,.0f} (vence {venc})\n"
                    
                    mensaje += "\n"
            
            if deuda_total > 0:
                mensaje += f"💰 **Total adeudado:** ${deuda_total:,.0f}\n\n"
                mensaje += "¿Necesitás los links de pago?"
            else:
                mensaje = "✅ ¡Estás al día! No hay cuotas pendientes. 🎉"
            
            return mensaje
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de cuenta: {e}")
            return "Hubo un error consultando tu estado de cuenta. Intentá de nuevo."


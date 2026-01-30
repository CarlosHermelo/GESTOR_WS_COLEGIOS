"""
Herramientas para envío de notificaciones.
"""
import logging

from langchain_core.tools import tool

from app.database import async_session_maker
from app.models.tickets import NotificacionEnviada


logger = logging.getLogger(__name__)


def get_notification_tools() -> list:
    """
    Factory que crea herramientas de notificaciones.
    
    Returns:
        list: Lista de herramientas
    """
    
@tool
    async def enviar_notificacion_whatsapp(
        whatsapp: str,
        mensaje: str,
        tipo: str = "general"
    ) -> str:
        """
        Envía una notificación por WhatsApp.
        
        Args:
            whatsapp: Número de WhatsApp destino
            mensaje: Mensaje a enviar
            tipo: Tipo de notificación (general, recordatorio, confirmacion)
        """
        try:
            from app.services.skill_manager import get_skill_manager
            from app.config import settings
            
            skill_name = settings.COMMUNICATION_SKILL
            logger.info(f"Delegando envío a skill {skill_name}: {whatsapp}")
            
            skill_manager = get_skill_manager()
            result = await skill_manager.execute_skill(
                skill_name=skill_name,
                script_name="send_message.py",
                args={
                    "to": whatsapp,
                    "message": mensaje
                }
            )
            
            if result.get("success"):
                source = result.get("source", "skill")
                return f"✅ Notificación enviada a {whatsapp} ({source})"
            else:
                error = result.get("error", "Error desconocido")
                return f"Error enviando notificación: {error}"
            
        except Exception as e:
            logger.error(f"Error enviando notificación: {e}")
            return f"Error enviando notificación: {e}"
    
    @tool
    async def registrar_notificacion_enviada(
        erp_cuota_id: str,
        whatsapp: str,
        tipo: str
    ) -> str:
        """
        Registra una notificación enviada en la base de datos.
        
        Args:
            erp_cuota_id: ID de la cuota relacionada
            whatsapp: Número de WhatsApp destino
            tipo: Tipo de notificación (recordatorio_d7, recordatorio_d3, confirmacion_pago)
        """
        try:
            async with async_session_maker() as session:
                notificacion = NotificacionEnviada(
                    erp_cuota_id=erp_cuota_id,
                    whatsapp_to=whatsapp,
                    tipo=tipo
                )
                session.add(notificacion)
                await session.commit()
                await session.refresh(notificacion)
                
                return f"Notificación registrada: {notificacion.id}"
                
        except Exception as e:
            logger.error(f"Error registrando notificación: {e}")
            return f"Error: {e}"
    
    return [enviar_notificacion_whatsapp, registrar_notificacion_enviada]

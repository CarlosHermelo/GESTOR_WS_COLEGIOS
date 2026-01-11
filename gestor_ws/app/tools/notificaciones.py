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
        Por ahora es simulado (no conecta con API real).
        
        Args:
            whatsapp: Número de WhatsApp destino
            mensaje: Mensaje a enviar
            tipo: Tipo de notificación (general, recordatorio, confirmacion)
        """
        try:
            # Simulación de envío
            logger.info(f"[SIMULADO] Enviando a {whatsapp}: {mensaje[:50]}...")
            
            return f"✅ Notificación enviada a {whatsapp}"
            
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

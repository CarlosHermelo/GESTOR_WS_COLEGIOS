"""
Servicio de notificaciones automáticas.
Gestiona recordatorios de pago y confirmaciones.
"""
import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, and_

from app.database import async_session_maker
from app.models.cache import CacheCuota, CacheAlumno, CacheResponsable
from app.models.tickets import NotificacionEnviada
from app.services.whatsapp_service import get_whatsapp_service
from app.adapters.mock_erp_adapter import get_erp_client


logger = logging.getLogger(__name__)


class NotificationService:
    """
    Servicio para envío de notificaciones automáticas.
    """
    
    def __init__(self):
        """Inicializa el servicio."""
        self.whatsapp = get_whatsapp_service()
        self.erp = get_erp_client()
    
    async def enviar_recordatorio_vencimiento(
        self,
        cuota_id: str,
        dias_antes: int
    ) -> bool:
        """
        Envía recordatorio de vencimiento de cuota.
        
        Args:
            cuota_id: ID de la cuota
            dias_antes: Días antes del vencimiento (7, 3, 1)
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Obtener datos de la cuota
            cuota_data = await self.erp.get_cuota(cuota_id)
            if not cuota_data:
                logger.warning(f"Cuota {cuota_id} no encontrada")
                return False
            
            # Obtener alumno y responsable
            alumno_id = cuota_data.get("alumno_id")
            alumno_data = await self.erp.get_alumno(alumno_id)
            if not alumno_data:
                return False
            
            # Buscar responsable con WhatsApp
            responsables = alumno_data.get("responsables", [])
            whatsapp = None
            for resp in responsables:
                if resp.get("whatsapp"):
                    whatsapp = resp["whatsapp"]
                    break
            
            if not whatsapp:
                logger.warning(f"No hay WhatsApp para alumno {alumno_id}")
                return False
            
            # Verificar si ya enviamos esta notificación
            if await self._ya_enviada(cuota_id, f"recordatorio_d{dias_antes}"):
                logger.info(f"Recordatorio d{dias_antes} ya enviado para {cuota_id}")
                return False
            
            # Construir mensaje
            alumno_nombre = f"{alumno_data.get('nombre', '')} {alumno_data.get('apellido', '')}".strip()
            monto = cuota_data.get("monto", 0)
            vencimiento = cuota_data.get("fecha_vencimiento", "")
            link = cuota_data.get("link_pago", "")
            
            mensaje = self._construir_mensaje_recordatorio(
                alumno_nombre, monto, vencimiento, dias_antes, link
            )
            
            # Enviar
            result = await self.whatsapp.send_message(whatsapp, mensaje)
            
            if result.get("success"):
                # Registrar envío
                await self._registrar_envio(cuota_id, whatsapp, f"recordatorio_d{dias_antes}")
                logger.info(f"Recordatorio d{dias_antes} enviado para {cuota_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error enviando recordatorio: {e}")
            return False
    
    async def enviar_confirmacion_pago(
        self,
        cuota_id: str,
        alumno_id: str
    ) -> bool:
        """
        Envía confirmación de pago al responsable.
        
        Args:
            cuota_id: ID de la cuota pagada
            alumno_id: ID del alumno
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Obtener datos
            alumno_data = await self.erp.get_alumno(alumno_id)
            if not alumno_data:
                return False
            
            cuota_data = await self.erp.get_cuota(cuota_id)
            
            # Buscar WhatsApp
            responsables = alumno_data.get("responsables", [])
            whatsapp = None
            for resp in responsables:
                if resp.get("whatsapp"):
                    whatsapp = resp["whatsapp"]
                    break
            
            if not whatsapp:
                return False
            
            # Construir mensaje
            alumno_nombre = f"{alumno_data.get('nombre', '')} {alumno_data.get('apellido', '')}".strip()
            monto = cuota_data.get("monto", 0) if cuota_data else 0
            
            mensaje = (
                f"✅ *Pago confirmado*\n\n"
                f"Recibimos el pago de la cuota de {alumno_nombre}.\n\n"
                f"💰 Monto: ${monto:,.0f}\n\n"
                f"¡Gracias por tu pago! 🙌"
            )
            
            # Enviar
            result = await self.whatsapp.send_message(whatsapp, mensaje)
            
            if result.get("success"):
                await self._registrar_envio(cuota_id, whatsapp, "confirmacion_pago")
                logger.info(f"Confirmación de pago enviada para {cuota_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error enviando confirmación: {e}")
            return False
    
    async def procesar_recordatorios_pendientes(self) -> dict:
        """
        Procesa todos los recordatorios pendientes.
        Debe ejecutarse como tarea programada (cron).
        
        Returns:
            dict: Estadísticas del procesamiento
        """
        stats = {"d7": 0, "d3": 0, "d1": 0, "errors": 0}
        
        try:
            # Obtener cuotas por vencer
            cuotas_d7 = await self.erp.get_cuotas_por_vencer(dias=7)
            cuotas_d3 = await self.erp.get_cuotas_por_vencer(dias=3)
            cuotas_d1 = await self.erp.get_cuotas_por_vencer(dias=1)
            
            # Procesar recordatorios de 7 días
            for cuota in cuotas_d7:
                if await self.enviar_recordatorio_vencimiento(cuota["id"], 7):
                    stats["d7"] += 1
            
            # Procesar recordatorios de 3 días
            for cuota in cuotas_d3:
                if await self.enviar_recordatorio_vencimiento(cuota["id"], 3):
                    stats["d3"] += 1
            
            # Procesar recordatorios de 1 día
            for cuota in cuotas_d1:
                if await self.enviar_recordatorio_vencimiento(cuota["id"], 1):
                    stats["d1"] += 1
            
            logger.info(f"Recordatorios procesados: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error procesando recordatorios: {e}")
            stats["errors"] += 1
            return stats
    
    def _construir_mensaje_recordatorio(
        self,
        alumno: str,
        monto: float,
        vencimiento: str,
        dias: int,
        link: str
    ) -> str:
        """Construye el mensaje de recordatorio."""
        if dias == 7:
            emoji = "📅"
            urgencia = "Recordatorio de pago"
        elif dias == 3:
            emoji = "⚠️"
            urgencia = "Cuota próxima a vencer"
        else:
            emoji = "🔔"
            urgencia = "¡Vence mañana!"
        
        mensaje = (
            f"{emoji} *{urgencia}*\n\n"
            f"La cuota de {alumno} vence el {vencimiento}.\n\n"
            f"💰 Monto: ${monto:,.0f}\n"
        )
        
        if link:
            mensaje += f"\n🔗 Link de pago:\n{link}\n"
        
        mensaje += "\n¿Ya pagaste? Avisame así lo registro ✅"
        
        return mensaje
    
    async def _ya_enviada(self, cuota_id: str, tipo: str) -> bool:
        """Verifica si ya se envió una notificación."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(NotificacionEnviada).where(
                    and_(
                        NotificacionEnviada.erp_cuota_id == cuota_id,
                        NotificacionEnviada.tipo == tipo
                    )
                )
            )
            return result.scalar_one_or_none() is not None
    
    async def _registrar_envio(
        self,
        cuota_id: str,
        whatsapp: str,
        tipo: str
    ) -> None:
        """Registra una notificación enviada."""
        async with async_session_maker() as session:
            notificacion = NotificacionEnviada(
                erp_cuota_id=cuota_id,
                whatsapp_to=whatsapp,
                tipo=tipo
            )
            session.add(notificacion)
            await session.commit()




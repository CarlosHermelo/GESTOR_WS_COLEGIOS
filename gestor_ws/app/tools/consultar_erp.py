"""
Herramientas para consultar el ERP.
Usadas por los agentes LLM para obtener información.
"""
import logging
from typing import Optional

from langchain_core.tools import tool

from app.adapters.erp_interface import ERPClientInterface


logger = logging.getLogger(__name__)


def get_erp_tools(erp_client: ERPClientInterface) -> list:
    """
    Factory que crea herramientas ERP con el cliente inyectado.
    
    Args:
        erp_client: Cliente ERP a usar
        
    Returns:
        list: Lista de herramientas configuradas
    """
    
    @tool
    async def consultar_estado_cuenta(whatsapp: str) -> str:
        """
        Consulta las cuotas pendientes de un responsable por su WhatsApp.
        Retorna el estado de cuenta con montos y fechas de vencimiento.
        Usa esta herramienta cuando el padre pregunte cuánto debe o su estado de cuenta.
        
        Args:
            whatsapp: Número de WhatsApp del responsable con código de país (ej: +5491112345001)
        """
        try:
            # Buscar responsable
            responsable = await erp_client.get_responsable_by_whatsapp(whatsapp)
            
            if not responsable:
                return (
                    "No encontré tu número registrado en el sistema. "
                    "Por favor, contactá a administración para verificar tus datos."
                )
            
            alumnos = responsable.get("alumnos", [])
            if not alumnos:
                return "No encontré alumnos asociados a tu cuenta."
            
            # Construir respuesta
            mensaje = "📋 Estado de cuenta:\n\n"
            deuda_total = 0
            cuotas_encontradas = []
            
            for alumno in alumnos:
                cuotas = await erp_client.get_alumno_cuotas(
                    alumno["id"],
                    estado="pendiente"
                )
                
                if cuotas:
                    nombre = f"{alumno.get('nombre', '')} {alumno.get('apellido', '')}".strip()
                    grado = alumno.get("grado", "")
                    mensaje += f"👤 {nombre} ({grado}):\n"
                    
                    for cuota in cuotas:
                        monto = cuota.get("monto", 0)
                        deuda_total += monto
                        venc = cuota.get("fecha_vencimiento", "")
                        num = cuota.get("numero_cuota", "?")
                        cuota_id = cuota.get("id", "")
                        
                        mensaje += f"  • Cuota {num}: ${monto:,.0f} (vence {venc})\n"
                        cuotas_encontradas.append(cuota_id)
                    
                    mensaje += "\n"
            
            if deuda_total > 0:
                mensaje += f"💰 Total adeudado: ${deuda_total:,.0f}\n\n"
                mensaje += "¿Necesitás los links de pago?"
            else:
                mensaje = "✅ ¡Estás al día! No hay cuotas pendientes."
            
            return mensaje
            
        except Exception as e:
            logger.error(f"Error consultando estado de cuenta: {e}")
            return "Hubo un error consultando el estado de cuenta. Intentá de nuevo."
    
    @tool
    async def obtener_link_pago(cuota_id: str) -> str:
        """
        Obtiene el link de pago de una cuota específica.
        Usa esta herramienta cuando el padre pida el link para pagar.
        
        Args:
            cuota_id: ID de la cuota para la cual obtener el link de pago
        """
        try:
            cuota = await erp_client.get_cuota(cuota_id)
            
            if not cuota:
                return "No encontré esa cuota. ¿Podés verificar el número?"
            
            link = cuota.get("link_pago")
            monto = cuota.get("monto", 0)
            venc = cuota.get("fecha_vencimiento", "")
            
            if link:
                return (
                    f"💳 Link de pago:\n\n"
                    f"Monto: ${monto:,.0f}\n"
                    f"Vencimiento: {venc}\n\n"
                    f"🔗 {link}\n\n"
                    f"Una vez que pagues, avisame así lo registro."
                )
            else:
                return (
                    "El link de pago aún no está disponible para esta cuota. "
                    "Te lo enviamos apenas esté listo."
                )
                
        except Exception as e:
            logger.error(f"Error obteniendo link de pago: {e}")
            return "Hubo un error obteniendo el link. Intentá de nuevo."
    
    @tool
    async def registrar_confirmacion_pago(cuota_id: str, whatsapp: str) -> str:
        """
        Registra que el padre confirmó haber realizado un pago.
        Usa esta herramienta cuando el padre diga que ya pagó.
        El pago queda pendiente de validación por administración.
        
        Args:
            cuota_id: ID de la cuota que el padre dice haber pagado
            whatsapp: Número de WhatsApp del responsable
        """
        try:
            from app.models.interacciones import Interaccion
            from app.database import async_session_maker
            
            async with async_session_maker() as session:
                interaccion = Interaccion(
                    whatsapp_from=whatsapp,
                    erp_cuota_id=cuota_id,
                    tipo="confirmacion_pago",
                    contenido="Padre confirmó haber realizado el pago",
                    agente="asistente",
                    extra_data={"cuota_id": cuota_id, "estado": "pendiente_validacion"}
                )
                session.add(interaccion)
                await session.commit()
            
            return (
                "✅ ¡Perfecto! Registré tu pago.\n\n"
                "Lo vamos a validar y te confirmo en las próximas horas. "
                "Si tenés el comprobante, podés enviarlo por acá."
            )
            
        except Exception as e:
            logger.error(f"Error registrando confirmación: {e}")
            return "Hubo un error registrando el pago. Intentá de nuevo."
    
    @tool
    async def escalar_a_agente(motivo: str, categoria: str = "consulta_admin") -> str:
        """
        Escala la consulta al agente coordinador para casos complejos.
        Usa esta herramienta cuando:
        - El padre pide plan de pagos
        - Hay un reclamo o queja
        - Solicita dar de baja
        - La consulta excede tus capacidades
        
        Args:
            motivo: Motivo por el cual se escala la consulta
            categoria: Categoría del escalamiento (plan_pago, reclamo, baja, consulta_admin)
        """
        return f"__ESCALAR__|{categoria}|{motivo}"
    
    return [
        consultar_estado_cuenta,
        obtener_link_pago,
        registrar_confirmacion_pago,
        escalar_a_agente
    ]

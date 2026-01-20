"""
Tools para notificaciones (WhatsApp, email).
Categoría: notif
"""
import logging
from datetime import datetime
from typing import Optional
import httpx

from app.mcp.registry import tool
from app.config import settings
from app.tools.base import gestor_client

logger = logging.getLogger(__name__)

# Registro de notificaciones enviadas (mock)
_mock_notificaciones: list[dict] = []


@tool(
    category="notif",
    mock_response={
        "sent": True,
        "whatsapp": "+5491112345001",
        "message_id": "mock-msg-001"
    }
)
async def enviar_whatsapp(whatsapp: str, mensaje: str, tipo: str = "general") -> dict:
    """
    Envía un mensaje por WhatsApp.
    
    Args:
        whatsapp: Número de WhatsApp destino
        mensaje: Mensaje a enviar
        tipo: Tipo de notificación (general, recordatorio, confirmacion)
    
    Returns:
        dict con sent y message_id
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] enviar_whatsapp({whatsapp}, tipo={tipo})")
        logger.info(f"[MOCK] Mensaje: {mensaje[:100]}...")
        
        notif = {
            "id": f"mock-msg-{len(_mock_notificaciones) + 1:03d}",
            "whatsapp": whatsapp,
            "mensaje": mensaje,
            "tipo": tipo,
            "timestamp": datetime.now().isoformat()
        }
        _mock_notificaciones.append(notif)
        
        return {
            "sent": True,
            "whatsapp": whatsapp,
            "message_id": notif["id"]
        }
    
    try:
        # Nota: El gestor_ws no tiene endpoint REST para enviar WhatsApp directamente
        # Se usa el servicio interno. Por ahora, intentamos el endpoint si existe
        # o retornamos error indicando que se debe usar el servicio interno
        response = await gestor_client.post("/api/whatsapp/send", {
            "to": whatsapp,
            "message": mensaje,
            "type": tipo
        })
        return {
            "sent": True,
            "whatsapp": whatsapp,
            "message_id": response.get("message_id", "")
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning("Endpoint /api/whatsapp/send no existe. Usar servicio interno de WhatsApp.")
            return {
                "sent": False,
                "whatsapp": whatsapp,
                "error": "Endpoint no disponible. Usar servicio interno de WhatsApp."
            }
        raise
    except Exception as e:
        logger.error(f"Error enviando WhatsApp: {e}")
        return {"sent": False, "whatsapp": whatsapp, "error": str(e)}


@tool(
    category="notif",
    mock_response={
        "registered": True,
        "cuota_id": "mock-cuota-003",
        "tipo": "recordatorio_d7"
    }
)
async def registrar_notificacion(
    cuota_id: str,
    whatsapp: str,
    tipo: str
) -> dict:
    """
    Registra que se envió una notificación para una cuota.
    
    Args:
        cuota_id: ID de la cuota
        whatsapp: WhatsApp destino
        tipo: Tipo de notificación (recordatorio_d7, recordatorio_d3, recordatorio_d1, confirmacion_pago)
    
    Returns:
        dict con registered y detalles
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] registrar_notificacion({cuota_id}, {tipo})")
        return {
            "registered": True,
            "cuota_id": cuota_id,
            "whatsapp": whatsapp,
            "tipo": tipo
        }
    
    try:
        response = await gestor_client.post("/api/notificaciones", {
            "cuota_id": cuota_id,
            "whatsapp": whatsapp,
            "tipo": tipo
        })
        return {"registered": True, **response}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning("Endpoint /api/notificaciones no existe. Registrar en BD directamente.")
            # En modo real, deberías registrar en la BD directamente
            return {"registered": False, "error": "Endpoint no disponible"}
        raise
    except Exception as e:
        logger.error(f"Error registrando notificación: {e}")
        return {"registered": False, "error": str(e)}


@tool(
    category="notif",
    mock_response={
        "cuotas": [
            {"id": "c001", "alumno": "Juan Pérez", "monto": 45000, "vencimiento": "2026-03-15"},
            {"id": "c002", "alumno": "Ana López", "monto": 42000, "vencimiento": "2026-03-18"}
        ],
        "count": 2
    }
)
async def obtener_cuotas_por_vencer(dias: int = 7) -> dict:
    """
    Obtiene las cuotas que vencen en los próximos N días.
    
    Args:
        dias: Cantidad de días a futuro (default: 7)
    
    Returns:
        dict con lista de cuotas y count
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] obtener_cuotas_por_vencer({dias})")
        return {
            "cuotas": [
                {"id": "c001", "alumno": "Juan Pérez García", "monto": 45000, "vencimiento": "2026-03-15", "whatsapp": "+5491112345001"},
                {"id": "c002", "alumno": "Ana Pérez García", "monto": 42000, "vencimiento": "2026-03-15", "whatsapp": "+5491112345001"}
            ],
            "count": 2,
            "dias": dias
        }
    
    try:
        response = await gestor_client.get(f"/api/cuotas/por-vencer?dias={dias}")
        return response
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning("Endpoint /api/cuotas/por-vencer no existe.")
            return {"cuotas": [], "count": 0, "error": "Endpoint no disponible"}
        raise
    except Exception as e:
        logger.error(f"Error obteniendo cuotas: {e}")
        return {"cuotas": [], "count": 0, "error": str(e)}


@tool(
    category="notif",
    mock_response={
        "enviados": 5,
        "errores": 0,
        "tipo": "recordatorio_d7"
    }
)
async def enviar_recordatorios_masivos(tipo: str, dias: int = 7) -> dict:
    """
    Envía recordatorios masivos para cuotas próximas a vencer.
    
    Args:
        tipo: Tipo de recordatorio (recordatorio_d7, recordatorio_d3, recordatorio_d1)
        dias: Días antes del vencimiento
    
    Returns:
        dict con cantidad de enviados y errores
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] enviar_recordatorios_masivos({tipo}, {dias})")
        return {
            "enviados": 5,
            "errores": 0,
            "tipo": tipo,
            "dias": dias
        }
    
    try:
        # Obtener cuotas
        cuotas_result = await obtener_cuotas_por_vencer(dias)
        cuotas = cuotas_result.get("cuotas", [])
        
        enviados = 0
        errores = 0
        
        for cuota in cuotas:
            whatsapp = cuota.get("whatsapp")
            if not whatsapp:
                continue
            
            mensaje = (
                f"📅 Recordatorio de pago\n\n"
                f"Alumno: {cuota.get('alumno', '')}\n"
                f"Monto: ${cuota.get('monto', 0):,.0f}\n"
                f"Vencimiento: {cuota.get('vencimiento', '')}\n\n"
                f"¿Necesitás el link de pago?"
            )
            
            result = await enviar_whatsapp(whatsapp, mensaje, tipo)
            
            if result.get("sent"):
                enviados += 1
                await registrar_notificacion(cuota["id"], whatsapp, tipo)
            else:
                errores += 1
        
        return {
            "enviados": enviados,
            "errores": errores,
            "tipo": tipo,
            "total_cuotas": len(cuotas)
        }
    except Exception as e:
        logger.error(f"Error en envío masivo: {e}")
        return {"enviados": 0, "errores": 1, "error": str(e)}

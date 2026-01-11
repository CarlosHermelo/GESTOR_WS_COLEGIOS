"""
Webhooks para recibir eventos del ERP.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas.erp import PagoConfirmadoEvent, CuotaGeneradaEvent
from app.services.sync_service import SyncService
from app.services.notification_service import NotificationService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/erp", tags=["Webhooks ERP"])

# Servicios
sync_service = SyncService()
notification_service = NotificationService()


@router.post("/pago-confirmado")
async def webhook_pago_confirmado(
    event: PagoConfirmadoEvent,
    background_tasks: BackgroundTasks
):
    """
    Webhook que recibe notificación de pago confirmado del ERP.
    
    Acciones:
    1. Actualiza el estado de la cuota en cache
    2. Envía confirmación al padre (background)
    """
    try:
        logger.info(f"Webhook pago confirmado recibido: {event.datos}")
        
        cuota_id = event.datos.get("cuota_id")
        alumno_id = event.datos.get("alumno_id")
        
        if not cuota_id:
            raise HTTPException(status_code=400, detail="cuota_id es requerido")
        
        # 1. Actualizar cache
        await sync_service.actualizar_estado_cuota(cuota_id, "pagada")
        
        # 2. Enviar confirmación en background
        if alumno_id:
            background_tasks.add_task(
                notification_service.enviar_confirmacion_pago,
                cuota_id,
                alumno_id
            )
        
        logger.info(f"Pago confirmado procesado: cuota={cuota_id}")
        
        return {
            "status": "ok",
            "message": "Pago confirmado procesado",
            "cuota_id": cuota_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando pago confirmado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cuota-generada")
async def webhook_cuota_generada(
    event: CuotaGeneradaEvent,
    background_tasks: BackgroundTasks
):
    """
    Webhook que recibe notificación de nueva cuota generada del ERP.
    
    Acciones:
    1. Sincroniza la cuota al cache
    2. Evalúa si debe enviar notificación (background)
    """
    try:
        logger.info(f"Webhook cuota generada recibido: {event.datos}")
        
        datos = event.datos
        cuota_id = datos.get("cuota_id")
        
        if not cuota_id:
            raise HTTPException(status_code=400, detail="cuota_id es requerido")
        
        # 1. Sincronizar cuota al cache
        await sync_service.sync_cuota(cuota_id, datos)
        
        # 2. Evaluar notificación en background
        # Por ahora no enviamos notificación automática de nueva cuota
        # pero dejamos el hook listo
        
        logger.info(f"Cuota generada procesada: {cuota_id}")
        
        return {
            "status": "ok",
            "message": "Cuota generada procesada",
            "cuota_id": cuota_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando cuota generada: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alumno-actualizado")
async def webhook_alumno_actualizado(
    event: dict,
    background_tasks: BackgroundTasks
):
    """
    Webhook que recibe actualización de datos de alumno.
    """
    try:
        logger.info(f"Webhook alumno actualizado: {event}")
        
        datos = event.get("datos", {})
        alumno_id = datos.get("alumno_id")
        
        if not alumno_id:
            raise HTTPException(status_code=400, detail="alumno_id es requerido")
        
        await sync_service.sync_alumno(alumno_id, datos)
        
        return {
            "status": "ok",
            "message": "Alumno actualizado",
            "alumno_id": alumno_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando alumno actualizado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/responsable-actualizado")
async def webhook_responsable_actualizado(
    event: dict,
    background_tasks: BackgroundTasks
):
    """
    Webhook que recibe actualización de datos de responsable.
    """
    try:
        logger.info(f"Webhook responsable actualizado: {event}")
        
        datos = event.get("datos", {})
        responsable_id = datos.get("responsable_id")
        
        if not responsable_id:
            raise HTTPException(status_code=400, detail="responsable_id es requerido")
        
        await sync_service.sync_responsable(responsable_id, datos)
        
        return {
            "status": "ok",
            "message": "Responsable actualizado",
            "responsable_id": responsable_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando responsable actualizado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


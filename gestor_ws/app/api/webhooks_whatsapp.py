"""
Webhooks para recibir mensajes de WhatsApp.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks

from app.schemas.whatsapp import WhatsAppMessage, WebhookVerification
from app.agents.router import MessageRouter, RouteType, get_saludo_response
from app.agents.asistente import AsistenteVirtual
from app.agents.coordinador import AgenteAutonomo
from app.services.whatsapp_service import get_whatsapp_service
from app.models.interacciones import Interaccion
from app.database import async_session_maker
from app.config import settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhooks WhatsApp"])

# Instancias de agentes (lazy loading)
_router_service: Optional[MessageRouter] = None
_asistente: Optional[AsistenteVirtual] = None
_agente: Optional[AgenteAutonomo] = None


def get_router_service() -> MessageRouter:
    """Obtiene instancia del router."""
    global _router_service
    if _router_service is None:
        _router_service = MessageRouter()
    return _router_service


def get_asistente() -> AsistenteVirtual:
    """Obtiene instancia del asistente."""
    global _asistente
    if _asistente is None:
        _asistente = AsistenteVirtual()
    return _asistente


def get_agente() -> AgenteAutonomo:
    """Obtiene instancia del agente coordinador."""
    global _agente
    if _agente is None:
        _agente = AgenteAutonomo()
    return _agente


@router.get("/whatsapp")
async def webhook_verification(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge")
):
    """
    Endpoint de verificación para Meta/WhatsApp.
    Meta envía un GET para verificar el webhook.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verificado correctamente")
        return int(hub_challenge)
    
    logger.warning(f"Verificación fallida: token={hub_verify_token}")
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@router.post("/whatsapp")
async def webhook_whatsapp(
    message: WhatsAppMessage,
    background_tasks: BackgroundTasks
):
    """
    Recibe mensajes de WhatsApp (formato simplificado para pruebas).
    
    Flujo:
    1. Router clasifica el mensaje
    2. Asistente o Agente procesa según clasificación
    3. Se envía respuesta
    4. Se registra la interacción
    """
    try:
        whatsapp_from = message.from_number
        texto = message.text
        
        logger.info(f"Mensaje recibido de {whatsapp_from}: '{texto[:50]}...'")
        
        # 1. Router decide la ruta
        router_service = get_router_service()
        ruta = router_service.route(texto)
        
        logger.info(f"Mensaje ruteado a: {ruta.value}")
        
        # 2. Procesar según ruta
        if ruta == RouteType.SALUDO:
            respuesta = get_saludo_response()
            agente = "router"
        
        elif ruta == RouteType.ASISTENTE:
            asistente = get_asistente()
            respuesta = await asistente.responder(whatsapp_from, texto)
            agente = "asistente"
            
            # Verificar si el asistente quiere escalar
            if respuesta.startswith("__ESCALAR__"):
                parts = respuesta.split("|")
                categoria = parts[1] if len(parts) > 1 else "consulta_admin"
                motivo = parts[2] if len(parts) > 2 else texto
                
                agente_coord = get_agente()
                respuesta = await agente_coord.procesar(whatsapp_from, texto)
                agente = "coordinador"
        
        else:  # RouteType.AGENTE
            agente_coord = get_agente()
            respuesta = await agente_coord.procesar(whatsapp_from, texto)
            agente = "coordinador"
        
        # 3. Enviar respuesta
        whatsapp_service = get_whatsapp_service()
        await whatsapp_service.send_message(whatsapp_from, respuesta)
        
        # 4. Registrar interacción (background)
        background_tasks.add_task(
            registrar_interaccion,
            whatsapp_from,
            texto,
            respuesta,
            agente
        )
        
        return {
            "status": "ok",
            "ruta": ruta.value,
            "agente": agente,
            "respuesta_preview": respuesta[:100] + "..." if len(respuesta) > 100 else respuesta
        }
        
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}", exc_info=True)
        
        # Enviar respuesta de error
        try:
            whatsapp_service = get_whatsapp_service()
            await whatsapp_service.send_message(
                message.from_number,
                "Disculpá, tuve un problema. ¿Podés intentar de nuevo?"
            )
        except Exception:
            pass
        
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whatsapp/test")
async def test_message(
    message: WhatsAppMessage
):
    """
    Endpoint de prueba para simular mensajes de WhatsApp.
    No envía respuesta real, solo procesa y retorna el resultado.
    """
    try:
        whatsapp_from = message.from_number
        texto = message.text
        
        # Router
        router_service = get_router_service()
        route_info = router_service.get_route_info(texto)
        ruta = RouteType(route_info["route"])
        
        # Procesar
        if ruta == RouteType.SALUDO:
            respuesta = get_saludo_response()
            agente = "router"
        elif ruta == RouteType.ASISTENTE:
            asistente = get_asistente()
            respuesta = await asistente.responder(whatsapp_from, texto)
            agente = "asistente"
        else:
            agente_coord = get_agente()
            respuesta = await agente_coord.procesar(whatsapp_from, texto)
            agente = "coordinador"
        
        return {
            "status": "ok",
            "from": whatsapp_from,
            "message": texto,
            "route_info": route_info,
            "agente": agente,
            "respuesta": respuesta
        }
        
    except Exception as e:
        logger.error(f"Error en test: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


async def registrar_interaccion(
    whatsapp: str,
    mensaje_entrada: str,
    respuesta: str,
    agente: str
) -> None:
    """Registra la interacción en la base de datos."""
    try:
        async with async_session_maker() as session:
            # Registrar mensaje entrante
            interaccion_entrada = Interaccion.crear_mensaje_entrante(
                whatsapp=whatsapp,
                contenido=mensaje_entrada
            )
            session.add(interaccion_entrada)
            
            # Registrar respuesta
            interaccion_respuesta = Interaccion.crear_respuesta_bot(
                whatsapp=whatsapp,
                contenido=respuesta,
                agente=agente
            )
            session.add(interaccion_respuesta)
            
            await session.commit()
            
            logger.debug(f"Interacción registrada para {whatsapp}")
            
    except Exception as e:
        logger.error(f"Error registrando interacción: {e}")


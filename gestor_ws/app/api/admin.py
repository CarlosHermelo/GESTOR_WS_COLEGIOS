"""
API de administración para gestión de tickets.
"""
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func

from app.database import async_session_maker
from app.models.tickets import Ticket
from app.schemas.tickets import (
    TicketResponse,
    TicketResolve,
    TicketListResponse
)
from app.agents.coordinador import AgenteAutonomo
from app.services.whatsapp_service import get_whatsapp_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/tickets", response_model=TicketListResponse)
async def list_tickets(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    prioridad: Optional[str] = Query(None, description="Filtrar por prioridad"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Lista tickets con filtros opcionales.
    """
    try:
        async with async_session_maker() as session:
            # Query base
            query = select(Ticket)
            count_query = select(func.count(Ticket.id))
            
            # Aplicar filtros
            if estado:
                query = query.where(Ticket.estado == estado)
                count_query = count_query.where(Ticket.estado == estado)
            
            if categoria:
                query = query.where(Ticket.categoria == categoria)
                count_query = count_query.where(Ticket.categoria == categoria)
            
            if prioridad:
                query = query.where(Ticket.prioridad == prioridad)
                count_query = count_query.where(Ticket.prioridad == prioridad)
            
            # Ordenar por fecha (más recientes primero)
            query = query.order_by(Ticket.created_at.desc())
            
            # Paginación
            query = query.offset(offset).limit(limit)
            
            # Ejecutar
            result = await session.execute(query)
            tickets = result.scalars().all()
            
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # Contar por estado
            pendientes = await session.execute(
                select(func.count(Ticket.id)).where(Ticket.estado == "pendiente")
            )
            en_proceso = await session.execute(
                select(func.count(Ticket.id)).where(Ticket.estado == "en_proceso")
            )
            resueltos = await session.execute(
                select(func.count(Ticket.id)).where(Ticket.estado == "resuelto")
            )
            
            return TicketListResponse(
                tickets=[TicketResponse.model_validate(t) for t in tickets],
                total=total,
                pendientes=pendientes.scalar() or 0,
                en_proceso=en_proceso.scalar() or 0,
                resueltos=resueltos.scalar() or 0
            )
            
    except Exception as e:
        logger.error(f"Error listando tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: UUID):
    """
    Obtiene detalle de un ticket.
    """
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Ticket).where(Ticket.id == ticket_id)
            )
            ticket = result.scalar_one_or_none()
            
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket no encontrado")
            
            return TicketResponse.model_validate(ticket)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tickets/{ticket_id}/resolver")
async def resolver_ticket(
    ticket_id: UUID,
    data: TicketResolve,
    background_tasks: BackgroundTasks
):
    """
    Resuelve un ticket y envía la respuesta al padre.
    
    La respuesta del admin se reformula usando LLM antes de enviarse.
    """
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Ticket).where(Ticket.id == ticket_id)
            )
            ticket = result.scalar_one_or_none()
            
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket no encontrado")
            
            if ticket.estado == "resuelto":
                raise HTTPException(status_code=400, detail="Ticket ya está resuelto")
            
            # Resolver ticket
            ticket.resolver(data.respuesta)
            await session.commit()
            await session.refresh(ticket)
            
            # Enviar respuesta al padre (background)
            phone_number = ticket.contexto.get("phone_number") if ticket.contexto else None
            
            if phone_number:
                background_tasks.add_task(
                    enviar_respuesta_ticket,
                    str(ticket_id),
                    data.respuesta,
                    phone_number
                )
            
            logger.info(f"Ticket {ticket_id} resuelto")
            
            return {
                "status": "ok",
                "message": "Ticket resuelto",
                "ticket_id": str(ticket_id),
                "notificacion_enviada": phone_number is not None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolviendo ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tickets/{ticket_id}/estado")
async def cambiar_estado_ticket(
    ticket_id: UUID,
    estado: str = Query(..., description="Nuevo estado: pendiente, en_proceso, resuelto")
):
    """
    Cambia el estado de un ticket.
    """
    estados_validos = ["pendiente", "en_proceso", "resuelto"]
    if estado not in estados_validos:
        raise HTTPException(
            status_code=400, 
            detail=f"Estado inválido. Opciones: {estados_validos}"
        )
    
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Ticket).where(Ticket.id == ticket_id)
            )
            ticket = result.scalar_one_or_none()
            
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket no encontrado")
            
            ticket.estado = estado
            if estado == "resuelto":
                ticket.resolved_at = datetime.now()
            
            await session.commit()
            
            return {
                "status": "ok",
                "ticket_id": str(ticket_id),
                "nuevo_estado": estado
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando estado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Obtiene estadísticas generales del sistema.
    """
    try:
        async with async_session_maker() as session:
            # Tickets por estado
            tickets_stats = {}
            for estado in ["pendiente", "en_proceso", "resuelto"]:
                result = await session.execute(
                    select(func.count(Ticket.id)).where(Ticket.estado == estado)
                )
                tickets_stats[estado] = result.scalar() or 0
            
            # Tickets por categoría
            categorias = ["plan_pago", "reclamo", "baja", "consulta_admin"]
            categorias_stats = {}
            for cat in categorias:
                result = await session.execute(
                    select(func.count(Ticket.id)).where(Ticket.categoria == cat)
                )
                categorias_stats[cat] = result.scalar() or 0
            
            # Tickets por prioridad (solo pendientes)
            prioridades_stats = {}
            for pri in ["baja", "media", "alta"]:
                result = await session.execute(
                    select(func.count(Ticket.id)).where(
                        Ticket.prioridad == pri,
                        Ticket.estado == "pendiente"
                    )
                )
                prioridades_stats[pri] = result.scalar() or 0
            
            return {
                "tickets": {
                    "por_estado": tickets_stats,
                    "por_categoria": categorias_stats,
                    "pendientes_por_prioridad": prioridades_stats,
                    "total": sum(tickets_stats.values())
                }
            }
            
    except Exception as e:
        logger.error(f"Error obteniendo stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def enviar_respuesta_ticket(
    ticket_id: str,
    respuesta_admin: str,
    phone_number: str
) -> None:
    """
    Reformula y envía la respuesta del ticket al padre.
    """
    try:
        # Reformular usando LLM
        agente = AgenteAutonomo()
        respuesta_reformulada = await agente.procesar_respuesta_admin(
            ticket_id,
            respuesta_admin,
            phone_number
        )
        
        # Enviar por WhatsApp
        whatsapp_service = get_whatsapp_service()
        await whatsapp_service.send_message(phone_number, respuesta_reformulada)
        
        logger.info(f"Respuesta de ticket {ticket_id} enviada a {phone_number}")
        
    except Exception as e:
        logger.error(f"Error enviando respuesta de ticket: {e}")


# ============== CONFIGURACION LLM ==============

from app.config import settings
from pydantic import BaseModel
from typing import Literal


class ConfigResponse(BaseModel):
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    openai_api_key_configured: bool
    google_api_key_configured: bool
    whatsapp_configured: bool


class ConfigUpdate(BaseModel):
    llm_provider: Optional[Literal["openai", "google"]] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_max_tokens: Optional[int] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None


class TestLLMRequest(BaseModel):
    provider: Literal["openai", "google"]


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """
    Retorna la configuración actual del sistema.
    """
    return ConfigResponse(
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_MODEL,
        llm_temperature=settings.LLM_TEMPERATURE,
        llm_max_tokens=settings.LLM_MAX_TOKENS,
        openai_api_key_configured=bool(settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 10),
        google_api_key_configured=bool(settings.GOOGLE_API_KEY and len(settings.GOOGLE_API_KEY) > 10),
        whatsapp_configured=bool(settings.WHATSAPP_TOKEN and not settings.WHATSAPP_TOKEN.startswith("dummy")),
    )


@router.put("/config")
async def update_config(config: ConfigUpdate):
    """
    Actualiza la configuración del sistema.
    
    NOTA: Los cambios se aplican en memoria. Para persistir,
    se deben guardar en .env o BD.
    """
    import os
    
    try:
        if config.llm_provider:
            os.environ['LLM_PROVIDER'] = config.llm_provider
            settings.LLM_PROVIDER = config.llm_provider
            
        if config.llm_model:
            os.environ['LLM_MODEL'] = config.llm_model
            settings.LLM_MODEL = config.llm_model
            
        if config.llm_temperature is not None:
            os.environ['LLM_TEMPERATURE'] = str(config.llm_temperature)
            settings.LLM_TEMPERATURE = config.llm_temperature
            
        if config.llm_max_tokens is not None:
            os.environ['LLM_MAX_TOKENS'] = str(config.llm_max_tokens)
            settings.LLM_MAX_TOKENS = config.llm_max_tokens
            
        if config.openai_api_key:
            os.environ['OPENAI_API_KEY'] = config.openai_api_key
            settings.OPENAI_API_KEY = config.openai_api_key
            
        if config.google_api_key:
            os.environ['GOOGLE_API_KEY'] = config.google_api_key
            settings.GOOGLE_API_KEY = config.google_api_key
        
        # Recargar LLM con nueva configuración
        from app.llm.factory import get_llm, validate_llm_config
        validate_llm_config()
        
        logger.info(f"Configuración actualizada: provider={settings.LLM_PROVIDER}, model={settings.LLM_MODEL}")
        
        return {
            "status": "ok",
            "message": "Configuración actualizada correctamente",
            "config": {
                "llm_provider": settings.LLM_PROVIDER,
                "llm_model": settings.LLM_MODEL,
                "llm_temperature": settings.LLM_TEMPERATURE,
                "llm_max_tokens": settings.LLM_MAX_TOKENS
            }
        }
        
    except Exception as e:
        logger.error(f"Error actualizando configuración: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/llm-models")
async def get_llm_models():
    """
    Retorna la lista de modelos disponibles por proveedor.
    """
    return {
        "openai": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo"
        ],
        "google": [
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-pro"
        ]
    }


@router.post("/config/test-llm")
async def test_llm(data: TestLLMRequest):
    """
    Prueba la conexión con el LLM del proveedor especificado.
    """
    try:
        from app.llm.factory import get_llm
        from langchain_core.messages import HumanMessage
        
        # Temporalmente cambiar provider para el test
        original_provider = settings.LLM_PROVIDER
        settings.LLM_PROVIDER = data.provider
        
        try:
            llm = get_llm()
            response = await llm.ainvoke([HumanMessage(content="Di 'Hola' en una palabra")])
            
            return {
                "success": True,
                "provider": data.provider,
                "model": settings.LLM_MODEL,
                "response": response.content[:100] if response.content else "OK"
            }
            
        finally:
            # Restaurar provider original
            settings.LLM_PROVIDER = original_provider
            
    except Exception as e:
        logger.error(f"Error probando LLM: {e}")
        return {
            "success": False,
            "error": str(e),
            "provider": data.provider
        }


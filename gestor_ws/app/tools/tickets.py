"""
Herramientas para gestión de tickets.
"""
import logging
from uuid import UUID

from langchain_core.tools import tool

from app.database import async_session_maker
from app.models.tickets import Ticket


logger = logging.getLogger(__name__)


def get_ticket_tools() -> list:
    """
    Factory que crea herramientas de tickets.
    
    Returns:
        list: Lista de herramientas
    """
    
    @tool
    async def crear_ticket(
        erp_alumno_id: str,
        categoria: str,
        motivo: str,
        prioridad: str = "media"
    ) -> str:
        """
        Crea un ticket de escalamiento para atención humana.
        
        Args:
            erp_alumno_id: ID del alumno en el ERP
            categoria: Categoría del ticket (plan_pago, reclamo, baja, consulta_admin)
            motivo: Motivo o descripción del ticket
            prioridad: Prioridad del ticket (baja, media, alta)
        """
        try:
            async with async_session_maker() as session:
                ticket = Ticket.crear(
                    erp_alumno_id=erp_alumno_id,
                    categoria=categoria,
                    motivo=motivo,
                    contexto={"origen": "herramienta_llm"},
                    prioridad=prioridad
                )
                session.add(ticket)
                await session.commit()
                await session.refresh(ticket)
                
                return f"Ticket creado: {ticket.id}"
                
        except Exception as e:
            logger.error(f"Error creando ticket: {e}")
            return f"Error creando ticket: {e}"
    
    @tool
    async def buscar_ticket(ticket_id: str) -> str:
        """
        Busca información de un ticket existente.
        
        Args:
            ticket_id: ID del ticket a buscar
        """
        try:
            from sqlalchemy import select
            
            async with async_session_maker() as session:
                result = await session.execute(
                    select(Ticket).where(Ticket.id == UUID(ticket_id))
                )
                ticket = result.scalar_one_or_none()
                
                if not ticket:
                    return f"Ticket {ticket_id} no encontrado"
                
                return (
                    f"Ticket: {ticket.id}\n"
                    f"Categoría: {ticket.categoria}\n"
                    f"Estado: {ticket.estado}\n"
                    f"Prioridad: {ticket.prioridad}\n"
                    f"Motivo: {ticket.motivo}\n"
                    f"Creado: {ticket.created_at}"
                )
                
        except Exception as e:
            logger.error(f"Error buscando ticket: {e}")
            return f"Error buscando ticket: {e}"
    
    return [crear_ticket, buscar_ticket]

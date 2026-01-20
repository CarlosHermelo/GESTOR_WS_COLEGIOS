"""
Tools para gestión administrativa (tickets, escalamientos).
Categoría: admin
"""
import logging
import uuid
from datetime import datetime
from typing import Optional

from app.mcp.registry import tool
from app.config import settings
from app.tools.base import gestor_client

logger = logging.getLogger(__name__)

# Almacén en memoria para tickets mock
_mock_tickets: dict[str, dict] = {}


def _get_mensaje_ticket(categoria: str, ticket_short_id: str) -> str:
    """Genera mensaje según categoría del ticket."""
    mensajes = {
        "plan_pago": (
            f"✅ Registré tu solicitud de plan de pagos.\n\n"
            f"📝 Ticket: #{ticket_short_id}\n\n"
            "El área administrativa va a evaluar tu situación y te "
            "contactará por este medio con las opciones disponibles.\n\n"
            "⏰ Tiempo estimado: 24-48 horas hábiles."
        ),
        "reclamo": (
            f"📋 Tu reclamo fue registrado correctamente.\n\n"
            f"📝 Ticket: #{ticket_short_id}\n\n"
            "Un representante del colegio va a revisar tu caso y "
            "te contactará para darle solución.\n\n"
            "⏰ Tiempo estimado: 24 horas hábiles."
        ),
        "baja": (
            f"📝 Tu solicitud de baja fue registrada.\n\n"
            f"Ticket: #{ticket_short_id}\n\n"
            "El área administrativa se comunicará contigo para "
            "continuar con el proceso.\n\n"
            "⚠️ Recordá que pueden aplicarse políticas de baja anticipada."
        ),
        "info_autoridades": (
            f"📋 Tu solicitud de información fue registrada.\n\n"
            f"📝 Ticket: #{ticket_short_id}\n\n"
            "Te contactaremos con la información solicitada.\n\n"
            "⏰ Tiempo estimado: 24-48 horas hábiles."
        ),
        "consulta_admin": (
            f"✅ Tu consulta fue derivada al área administrativa.\n\n"
            f"📝 Ticket: #{ticket_short_id}\n\n"
            "Te responderán a la brevedad por este medio.\n\n"
            "⏰ Tiempo estimado: 24-48 horas hábiles."
        )
    }
    return mensajes.get(categoria, mensajes["consulta_admin"])


@tool(
    category="admin",
    mock_response={
        "created": True,
        "ticket_id": "mock-ticket-001",
        "categoria": "consulta_admin",
        "prioridad": "media",
        "mensaje": "✅ Tu consulta fue derivada al área administrativa."
    }
)
async def crear_ticket(
    categoria: str,
    motivo: str,
    phone_number: str,
    prioridad: str = "media",
    alumno_id: str = None
) -> dict:
    """
    Crea un ticket de escalamiento para atención humana.
    
    Args:
        categoria: Categoría del ticket (plan_pago, reclamo, baja, consulta_admin, info_autoridades)
        motivo: Motivo o descripción del ticket
        phone_number: WhatsApp del solicitante
        prioridad: Prioridad (baja, media, alta)
        alumno_id: ID del alumno relacionado (opcional)
    
    Returns:
        dict con created, ticket_id, categoria, prioridad y mensaje
    """
    if settings.MOCK_MODE:
        ticket_id = str(uuid.uuid4())
        logger.info(f"[MOCK] crear_ticket: {ticket_id} - {categoria}")
        
        # Guardar en memoria
        _mock_tickets[ticket_id] = {
            "id": ticket_id,
            "categoria": categoria,
            "motivo": motivo,
            "phone_number": phone_number,
            "prioridad": prioridad,
            "alumno_id": alumno_id,
            "estado": "pendiente",
            "created_at": datetime.now().isoformat()
        }
        
        return {
            "created": True,
            "ticket_id": ticket_id,
            "categoria": categoria,
            "prioridad": prioridad,
            "mensaje": _get_mensaje_ticket(categoria, ticket_id[:8])
        }
    
    try:
        response = await gestor_client.post("/api/admin/tickets", {
            "categoria": categoria,
            "motivo": motivo,
            "phone_number": phone_number,
            "prioridad": prioridad,
            "alumno_id": alumno_id
        })
        
        ticket_id = response.get("id", "")
        return {
            "created": True,
            "ticket_id": str(ticket_id),  # Convertir UUID a string
            "categoria": categoria,
            "prioridad": prioridad,
            "mensaje": _get_mensaje_ticket(categoria, str(ticket_id)[:8] if ticket_id else "000")
        }
    except Exception as e:
        logger.error(f"Error creando ticket: {e}")
        return {"created": False, "error": str(e)}


@tool(
    category="admin",
    mock_response={
        "found": True,
        "ticket": {
            "id": "mock-ticket-001",
            "categoria": "consulta_admin",
            "estado": "pendiente",
            "prioridad": "media",
            "motivo": "Consulta sobre pagos"
        }
    }
)
async def buscar_ticket(ticket_id: str) -> dict:
    """
    Busca información de un ticket existente.
    
    Args:
        ticket_id: ID del ticket a buscar
    
    Returns:
        dict con found y datos del ticket
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] buscar_ticket({ticket_id})")
        
        if ticket_id in _mock_tickets:
            return {"found": True, "ticket": _mock_tickets[ticket_id]}
        
        return {
            "found": True,
            "ticket": {
                "id": ticket_id,
                "categoria": "consulta_admin",
                "estado": "pendiente",
                "prioridad": "media",
                "motivo": "Ticket de prueba"
            }
        }
    
    try:
        response = await gestor_client.get(f"/api/admin/tickets/{ticket_id}")
        return {"found": True, "ticket": response}
    except Exception as e:
        logger.error(f"Error buscando ticket: {e}")
        return {"found": False, "error": str(e)}


@tool(
    category="admin",
    mock_response={
        "prioridad": "media",
        "razon": "Consulta general sin urgencia"
    }
)
async def clasificar_prioridad(motivo: str) -> dict:
    """
    Clasifica la prioridad de un caso basándose en el motivo.
    Esta función siempre usa lógica local (no requiere API).
    
    Args:
        motivo: Descripción del caso a clasificar
    
    Returns:
        dict con prioridad (baja, media, alta) y razon
    """
    logger.info(f"Clasificando prioridad para: {motivo[:50]}...")
    
    motivo_lower = motivo.lower()
    
    # Reglas de clasificación (siempre local, no requiere API)
    if any(kw in motivo_lower for kw in ["urgente", "legal", "grave", "demanda", "judicial"]):
        return {"prioridad": "alta", "razon": "Caso urgente o con implicaciones legales"}
    elif any(kw in motivo_lower for kw in ["reclamo", "error", "queja", "problema", "mal"]):
        return {"prioridad": "media", "razon": "Reclamo o problema que requiere atención"}
    else:
        return {"prioridad": "baja", "razon": "Consulta general"}


@tool(
    category="admin",
    mock_response={
        "tickets": [
            {"id": "t001", "categoria": "plan_pago", "estado": "pendiente"},
            {"id": "t002", "categoria": "reclamo", "estado": "en_proceso"}
        ],
        "count": 2
    }
)
async def listar_tickets_pendientes(phone_number: str = None) -> dict:
    """
    Lista los tickets pendientes, opcionalmente filtrados por número de teléfono.
    
    Args:
        phone_number: WhatsApp para filtrar (opcional)
    
    Returns:
        dict con lista de tickets y count
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] listar_tickets_pendientes({phone_number})")
        
        tickets = list(_mock_tickets.values())
        if phone_number:
            tickets = [t for t in tickets if t.get("phone_number") == phone_number]
        
        return {
            "tickets": tickets,
            "count": len(tickets)
        }
    
    try:
        params = {}
        if phone_number:
            params["phone_number"] = phone_number
        
        response = await gestor_client.get("/api/admin/tickets", params=params)
        
        # Transformar respuesta si es necesario
        tickets = response.get("tickets", [])
        return {
            "tickets": tickets,
            "count": len(tickets)
        }
    except Exception as e:
        logger.error(f"Error listando tickets: {e}")
        return {"tickets": [], "count": 0, "error": str(e)}

"""
Schemas Pydantic para validación de datos.
"""
from app.schemas.erp import (
    AlumnoSchema,
    ResponsableSchema,
    CuotaSchema,
    PagoConfirmadoEvent,
    CuotaGeneradaEvent
)
from app.schemas.whatsapp import (
    WhatsAppMessage,
    WhatsAppResponse,
    WebhookPayload
)
from app.schemas.tickets import (
    TicketCreate,
    TicketResponse,
    TicketResolve,
    TicketListResponse
)

__all__ = [
    # ERP
    "AlumnoSchema",
    "ResponsableSchema",
    "CuotaSchema",
    "PagoConfirmadoEvent",
    "CuotaGeneradaEvent",
    # WhatsApp
    "WhatsAppMessage",
    "WhatsAppResponse",
    "WebhookPayload",
    # Tickets
    "TicketCreate",
    "TicketResponse",
    "TicketResolve",
    "TicketListResponse"
]




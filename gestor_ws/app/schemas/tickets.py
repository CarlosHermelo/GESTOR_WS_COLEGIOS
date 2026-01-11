"""
Schemas para gestión de tickets.
"""
from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    """Schema para crear un nuevo ticket."""
    
    erp_alumno_id: str = Field(
        ...,
        description="ID del alumno en el ERP"
    )
    erp_responsable_id: Optional[str] = Field(
        None,
        description="ID del responsable en el ERP"
    )
    categoria: str = Field(
        ...,
        description="Categoría del ticket: plan_pago, reclamo, baja, consulta_admin"
    )
    motivo: str = Field(
        ...,
        description="Descripción del motivo del ticket"
    )
    contexto: dict[str, Any] = Field(
        default_factory=dict,
        description="Contexto de la conversación"
    )
    prioridad: str = Field(
        default="media",
        description="Prioridad: baja, media, alta"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "erp_alumno_id": "ALU-001",
                "erp_responsable_id": "RES-001",
                "categoria": "plan_pago",
                "motivo": "El padre solicita un plan de pagos en 3 cuotas",
                "contexto": {
                    "mensajes": [
                        {"from": "usuario", "text": "Necesito un plan de pago"},
                        {"from": "bot", "text": "Entiendo, voy a derivar tu consulta"}
                    ]
                },
                "prioridad": "media"
            }
        }


class TicketResponse(BaseModel):
    """Schema para respuesta de ticket."""
    
    id: UUID
    erp_alumno_id: str
    erp_responsable_id: Optional[str] = None
    categoria: Optional[str] = None
    motivo: Optional[str] = None
    contexto: Optional[dict[str, Any]] = None
    estado: str
    prioridad: str
    respuesta_admin: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TicketResolve(BaseModel):
    """Schema para resolver un ticket."""
    
    respuesta: str = Field(
        ...,
        description="Respuesta del administrador para el padre",
        min_length=10
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "respuesta": "Se aprobó el plan de pagos en 3 cuotas sin interés. Las nuevas fechas de vencimiento son: 15/02, 15/03 y 15/04."
            }
        }


class TicketListResponse(BaseModel):
    """Schema para listado de tickets."""
    
    tickets: list[TicketResponse]
    total: int
    pendientes: int
    en_proceso: int
    resueltos: int


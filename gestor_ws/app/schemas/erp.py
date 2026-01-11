"""
Schemas para datos del ERP.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, Field


class AlumnoSchema(BaseModel):
    """Schema para datos de alumno."""
    
    id: str
    nombre: str
    apellido: str
    grado: Optional[str] = None
    
    class Config:
        from_attributes = True


class ResponsableSchema(BaseModel):
    """Schema para datos de responsable con sus alumnos."""
    
    id: str
    nombre: str
    apellido: str
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    alumnos: list[AlumnoSchema] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class CuotaSchema(BaseModel):
    """Schema para datos de cuota."""
    
    id: str
    alumno_id: str
    numero_cuota: int
    monto: Decimal
    fecha_vencimiento: date
    estado: str  # pendiente, pagada, vencida
    link_pago: Optional[str] = None
    fecha_pago: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============== EVENTOS WEBHOOK ==============

class PagoConfirmadoEvent(BaseModel):
    """Evento de webhook cuando se confirma un pago."""
    
    tipo: str = "pago_confirmado"
    timestamp: datetime = Field(default_factory=datetime.now)
    datos: dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "tipo": "pago_confirmado",
                "timestamp": "2024-01-15T10:30:00",
                "datos": {
                    "cuota_id": "CUO-001",
                    "alumno_id": "ALU-001",
                    "monto": 45000.00,
                    "metodo_pago": "transferencia",
                    "fecha_pago": "2024-01-15T10:30:00"
                }
            }
        }


class CuotaGeneradaEvent(BaseModel):
    """Evento de webhook cuando se genera una nueva cuota."""
    
    tipo: str = "cuota_generada"
    timestamp: datetime = Field(default_factory=datetime.now)
    datos: dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "tipo": "cuota_generada",
                "timestamp": "2024-01-01T00:00:00",
                "datos": {
                    "cuota_id": "CUO-001",
                    "alumno_id": "ALU-001",
                    "monto": 45000.00,
                    "fecha_vencimiento": "2024-01-15",
                    "link_pago": "https://pago.colegio.com/CUO-001"
                }
            }
        }


"""
Schemas Pydantic para validación de request/response.
Usa Pydantic v2 con model_config.
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum


# ============== ENUMS ==============

class EstadoCuota(str, Enum):
    """Estados posibles de una cuota."""
    PENDIENTE = "pendiente"
    PAGADA = "pagada"
    VENCIDA = "vencida"


class TipoResponsable(str, Enum):
    """Tipos de responsable."""
    PADRE = "padre"
    MADRE = "madre"
    TUTOR = "tutor"


# ============== BASE SCHEMAS ==============

class ResponsableBase(BaseModel):
    """Schema base para responsable."""
    nombre: str = Field(..., max_length=100)
    apellido: str = Field(..., max_length=100)
    whatsapp: str = Field(..., max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    tipo: Optional[TipoResponsable] = None


class AlumnoBase(BaseModel):
    """Schema base para alumno."""
    nombre: str = Field(..., max_length=100)
    apellido: str = Field(..., max_length=100)
    fecha_nacimiento: Optional[date] = None
    grado: Optional[str] = Field(None, max_length=50)
    activo: bool = True


class PlanPagoBase(BaseModel):
    """Schema base para plan de pago."""
    nombre: Optional[str] = Field(None, max_length=100)
    cantidad_cuotas: Optional[int] = None
    monto_cuota: Optional[Decimal] = None
    anio: Optional[int] = None


class CuotaBase(BaseModel):
    """Schema base para cuota."""
    alumno_id: str = Field(..., max_length=50)
    plan_pago_id: Optional[str] = Field(None, max_length=50)
    numero_cuota: Optional[int] = None
    monto: Decimal
    fecha_vencimiento: date
    estado: Optional[EstadoCuota] = EstadoCuota.PENDIENTE
    link_pago: Optional[str] = None


class PagoBase(BaseModel):
    """Schema base para pago."""
    cuota_id: str = Field(..., max_length=50)
    monto: Decimal
    metodo_pago: Optional[str] = Field(None, max_length=50)
    referencia: Optional[str] = Field(None, max_length=100)


# ============== RESPONSE SCHEMAS ==============

class AlumnoResponse(AlumnoBase):
    """Schema de respuesta para alumno."""
    id: str
    
    model_config = ConfigDict(from_attributes=True)


class AlumnoDetalleResponse(AlumnoResponse):
    """Schema de respuesta con detalle de alumno (incluye responsables)."""
    responsables: List["ResponsableSimpleResponse"] = []


class ResponsableSimpleResponse(BaseModel):
    """Schema simplificado de responsable (sin alumnos)."""
    id: str
    nombre: str
    apellido: str
    whatsapp: str
    email: Optional[str] = None
    tipo: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ResponsableResponse(ResponsableBase):
    """Schema de respuesta para responsable."""
    id: str
    
    model_config = ConfigDict(from_attributes=True)


class ResponsableConAlumnosResponse(ResponsableResponse):
    """Schema de respuesta con responsable y sus alumnos a cargo."""
    alumnos: List[AlumnoResponse] = []


class PlanPagoResponse(PlanPagoBase):
    """Schema de respuesta para plan de pago."""
    id: str
    
    model_config = ConfigDict(from_attributes=True)


class CuotaResponse(BaseModel):
    """Schema de respuesta para cuota."""
    id: str
    alumno_id: str
    plan_pago_id: Optional[str] = None
    numero_cuota: Optional[int] = None
    monto: Decimal
    fecha_vencimiento: date
    estado: Optional[str] = None
    link_pago: Optional[str] = None
    fecha_pago: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class CuotaDetalleResponse(CuotaResponse):
    """Schema de respuesta con detalle de cuota (incluye alumno)."""
    alumno: Optional[AlumnoResponse] = None
    plan_pago: Optional[PlanPagoResponse] = None


class PagoResponse(BaseModel):
    """Schema de respuesta para pago."""
    id: str
    cuota_id: str
    monto: Decimal
    fecha_pago: datetime
    metodo_pago: Optional[str] = None
    referencia: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============== REQUEST SCHEMAS ==============

class ConfirmarPagoRequest(BaseModel):
    """Schema para confirmar un pago."""
    cuota_id: str = Field(..., description="ID de la cuota a pagar")
    monto: Decimal = Field(..., gt=0, description="Monto del pago")
    metodo_pago: Optional[str] = Field(None, description="Método de pago utilizado")
    referencia: Optional[str] = Field(None, description="Referencia del pago")


class ConfirmarPagoResponse(BaseModel):
    """Schema de respuesta al confirmar pago."""
    success: bool
    message: str
    pago: Optional[PagoResponse] = None
    cuota: Optional[CuotaResponse] = None


# ============== WEBHOOK SCHEMAS ==============

class WebhookPagoConfirmadoDatos(BaseModel):
    """Datos del webhook de pago confirmado."""
    cuota_id: str
    alumno_id: str
    monto: Decimal
    fecha_pago: datetime


class WebhookPagoConfirmado(BaseModel):
    """Schema del webhook enviado cuando se confirma un pago."""
    tipo: str = "pago_confirmado"
    timestamp: datetime
    datos: WebhookPagoConfirmadoDatos


# ============== UTILITY SCHEMAS ==============

class HealthResponse(BaseModel):
    """Schema de respuesta para health check."""
    status: str
    service: str = "erp_mock"
    timestamp: datetime
    database: str = "connected"


class ErrorResponse(BaseModel):
    """Schema de respuesta para errores."""
    detail: str
    error_code: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Schema base para respuestas paginadas."""
    total: int
    page: int = 1
    page_size: int = 20
    items: List = []


# Actualizar referencias forward
AlumnoDetalleResponse.model_rebuild()


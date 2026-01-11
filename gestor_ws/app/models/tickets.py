"""
Modelos para gestión de tickets y notificaciones.
"""
import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import String, DateTime, Text, Boolean, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Ticket(Base):
    """
    Tickets de escalamiento para casos complejos.
    Creados cuando el bot no puede resolver una consulta.
    """
    
    __tablename__ = "tickets"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    erp_alumno_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    erp_responsable_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True
    )
    categoria: Mapped[Optional[str]] = mapped_column(
        String(50),
        index=True
    )  # plan_pago, reclamo, baja, consulta_admin
    motivo: Mapped[Optional[str]] = mapped_column(Text)
    contexto: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB
    )  # Conversación completa
    estado: Mapped[str] = mapped_column(
        String(20),
        default="pendiente",
        index=True
    )  # pendiente, en_proceso, resuelto
    prioridad: Mapped[str] = mapped_column(
        String(20),
        default="media",
        index=True
    )  # baja, media, alta
    respuesta_admin: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    def __repr__(self) -> str:
        return f"<Ticket {self.id} - {self.categoria} ({self.estado})>"
    
    @property
    def esta_pendiente(self) -> bool:
        """Verifica si el ticket está pendiente."""
        return self.estado == "pendiente"
    
    @property
    def esta_resuelto(self) -> bool:
        """Verifica si el ticket está resuelto."""
        return self.estado == "resuelto"
    
    def resolver(self, respuesta: str) -> None:
        """Marca el ticket como resuelto."""
        self.estado = "resuelto"
        self.respuesta_admin = respuesta
        self.resolved_at = datetime.now()
    
    @classmethod
    def crear(
        cls,
        erp_alumno_id: str,
        categoria: str,
        motivo: str,
        contexto: dict,
        prioridad: str = "media",
        erp_responsable_id: Optional[str] = None
    ) -> "Ticket":
        """Factory para crear un nuevo ticket."""
        return cls(
            erp_alumno_id=erp_alumno_id,
            erp_responsable_id=erp_responsable_id,
            categoria=categoria,
            motivo=motivo,
            contexto=contexto,
            prioridad=prioridad
        )


class NotificacionEnviada(Base):
    """
    Registro de notificaciones enviadas por WhatsApp.
    Para tracking de recordatorios y confirmaciones.
    """
    
    __tablename__ = "notificaciones_enviadas"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    erp_cuota_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    whatsapp_to: Mapped[Optional[str]] = mapped_column(
        String(20),
        index=True
    )
    tipo: Mapped[Optional[str]] = mapped_column(
        String(50),
        index=True
    )  # recordatorio_d7, recordatorio_d3, recordatorio_d1, confirmacion_pago
    fecha_envio: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now()
    )
    leido: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self) -> str:
        return f"<NotificacionEnviada {self.tipo} a {self.whatsapp_to}>"
    
    @classmethod
    def crear_recordatorio(
        cls,
        erp_cuota_id: str,
        whatsapp: str,
        dias_antes: int
    ) -> "NotificacionEnviada":
        """Factory para crear notificación de recordatorio."""
        return cls(
            erp_cuota_id=erp_cuota_id,
            whatsapp_to=whatsapp,
            tipo=f"recordatorio_d{dias_antes}"
        )
    
    @classmethod
    def crear_confirmacion(
        cls,
        erp_cuota_id: str,
        whatsapp: str
    ) -> "NotificacionEnviada":
        """Factory para crear notificación de confirmación de pago."""
        return cls(
            erp_cuota_id=erp_cuota_id,
            whatsapp_to=whatsapp,
            tipo="confirmacion_pago"
        )


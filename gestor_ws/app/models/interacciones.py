"""
Modelos para registro de interacciones y sincronizaciones.
"""
import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Interaccion(Base):
    """
    Registro de todas las interacciones con usuarios.
    Incluye mensajes entrantes, respuestas del bot, etc.
    """
    
    __tablename__ = "interacciones"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    whatsapp_from: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    erp_alumno_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True
    )
    erp_cuota_id: Mapped[Optional[str]] = mapped_column(String(100))
    tipo: Mapped[Optional[str]] = mapped_column(
        String(50),
        index=True
    )  # consulta, notificacion, respuesta, confirmacion_pago, etc.
    contenido: Mapped[Optional[str]] = mapped_column(Text)
    agente: Mapped[Optional[str]] = mapped_column(
        String(20)
    )  # bot, asistente, coordinador, humano
    extra_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        index=True
    )
    
    def __repr__(self) -> str:
        return f"<Interaccion {self.id} - {self.tipo} de {self.whatsapp_from}>"
    
    @classmethod
    def crear_mensaje_entrante(
        cls,
        whatsapp: str,
        contenido: str,
        erp_alumno_id: Optional[str] = None
    ) -> "Interaccion":
        """Factory para crear interacción de mensaje entrante."""
        return cls(
            whatsapp_from=whatsapp,
            erp_alumno_id=erp_alumno_id,
            tipo="mensaje_entrante",
            contenido=contenido,
            agente="usuario"
        )
    
    @classmethod
    def crear_respuesta_bot(
        cls,
        whatsapp: str,
        contenido: str,
        agente: str = "asistente",
        extra_data: Optional[dict] = None
    ) -> "Interaccion":
        """Factory para crear interacción de respuesta del bot."""
        return cls(
            whatsapp_from=whatsapp,
            tipo="respuesta",
            contenido=contenido,
            agente=agente,
            extra_data=extra_data
        )


class SincronizacionLog(Base):
    """
    Log de sincronizaciones con el ERP.
    Registra todas las operaciones de sincronización.
    """
    
    __tablename__ = "sincronizaciones_log"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tipo: Mapped[Optional[str]] = mapped_column(
        String(50),
        index=True
    )  # alumno, cuota, responsable, pago
    erp_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True
    )
    accion: Mapped[Optional[str]] = mapped_column(
        String(20)
    )  # create, update, delete
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        index=True
    )
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    
    def __repr__(self) -> str:
        return f"<SincronizacionLog {self.tipo}/{self.accion} - {self.erp_id}>"


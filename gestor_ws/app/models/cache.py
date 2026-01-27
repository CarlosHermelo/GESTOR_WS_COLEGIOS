"""
Modelos de cache para réplica parcial del ERP.
Almacena datos sincronizados del ERP para consulta rápida.
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, DateTime, Date, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CacheResponsable(Base):
    """Cache de responsables (padres/tutores) del ERP."""
    
    __tablename__ = "cache_responsables"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    erp_responsable_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    nombre: Mapped[Optional[str]] = mapped_column(String(200))
    apellido: Mapped[Optional[str]] = mapped_column(String(200))
    whatsapp: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique=True,
        index=True
    )
    email: Mapped[Optional[str]] = mapped_column(String(200))
    ultima_sync: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<CacheResponsable {self.nombre} {self.apellido} ({self.whatsapp})>"
    
    @property
    def nombre_completo(self) -> str:
        """Retorna nombre completo del responsable."""
        return f"{self.nombre or ''} {self.apellido or ''}".strip()


class CacheAlumno(Base):
    """Cache de alumnos del ERP."""
    
    __tablename__ = "cache_alumnos"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    erp_alumno_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    nombre: Mapped[Optional[str]] = mapped_column(String(200))
    apellido: Mapped[Optional[str]] = mapped_column(String(200))
    grado: Mapped[Optional[str]] = mapped_column(String(100))
    erp_responsable_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True
    )
    ultima_sync: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<CacheAlumno {self.nombre} {self.apellido} ({self.grado})>"
    
    @property
    def nombre_completo(self) -> str:
        """Retorna nombre completo del alumno."""
        return f"{self.nombre or ''} {self.apellido or ''}".strip()


class CacheCuota(Base):
    """Cache de cuotas del ERP."""
    
    __tablename__ = "cache_cuotas"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    erp_cuota_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    erp_alumno_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True
    )
    monto: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date, index=True)
    estado: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    link_pago: Mapped[Optional[str]] = mapped_column(Text)
    fecha_pago: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ultima_sync: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<CacheCuota {self.erp_cuota_id} - ${self.monto} ({self.estado})>"
    
    @property
    def esta_vencida(self) -> bool:
        """Verifica si la cuota está vencida."""
        if not self.fecha_vencimiento:
            return False
        return self.fecha_vencimiento < date.today() and self.estado != "pagada"




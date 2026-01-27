"""
Modelo de datos para tracking de tokens.
Preparado para persistencia futura en base de datos.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, Index
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class TokenUsage(Base):
    """
    Modelo para persistir el consumo de tokens por consulta.
    
    Este modelo está preparado para futura migración a BD.
    Por ahora solo se define el schema, no se crea la tabla aún.
    """
    __tablename__ = "token_usage"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # Identificación de la consulta
    query_id = Column(
        String(100),
        nullable=False,
        index=True,
        comment="ID único de la consulta (generado por TokenTracker)"
    )
    
    whatsapp = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Número de WhatsApp del usuario"
    )
    
    mensaje = Column(
        Text,
        nullable=False,
        comment="Mensaje original del usuario"
    )
    
    # Timestamps
    start_time = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Inicio de la sesión de tracking"
    )
    
    end_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fin de la sesión de tracking"
    )
    
    # Tokens totales
    total_prompt_tokens = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total de tokens de entrada (prompt)"
    )
    
    total_completion_tokens = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total de tokens de salida (completion)"
    )
    
    total_tokens = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total de tokens (prompt + completion)"
    )
    
    # Metadata del LLM
    provider = Column(
        String(50),
        nullable=True,
        comment="Provider LLM (openai, google)"
    )
    
    model = Column(
        String(100),
        nullable=True,
        comment="Modelo LLM usado (gpt-4o, gemini-2.0-flash-exp, etc.)"
    )
    
    # Inferencias detalladas (JSON)
    inferences_json = Column(
        JSON,
        nullable=True,
        comment="Array de InferenceRecord serializado en JSON"
    )
    
    # Metadata adicional
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Fecha de creación del registro"
    )
    
    # Índices compuestos para consultas comunes
    __table_args__ = (
        Index('idx_token_usage_whatsapp_created', 'whatsapp', 'created_at'),
        Index('idx_token_usage_query_id', 'query_id'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<TokenUsage(id={self.id}, query_id={self.query_id}, "
            f"whatsapp={self.whatsapp}, total_tokens={self.total_tokens})>"
        )
    
    def to_dict(self) -> dict:
        """Convierte el modelo a dict para serialización."""
        return {
            "id": str(self.id),
            "query_id": self.query_id,
            "whatsapp": self.whatsapp,
            "mensaje": self.mensaje,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "provider": self.provider,
            "model": self.model,
            "inferences_json": self.inferences_json,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

"""
Token Tracker Service - Tracking de consumo de tokens por consulta.
Captura tokens de cada inferencia LLM y genera resumen por sesión.
"""
import json
import logging
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable para tracking thread-safe
_current_session: ContextVar[Optional["TokenSession"]] = ContextVar("_current_session", default=None)


@dataclass
class InferenceRecord:
    """Registro de una inferencia LLM individual."""
    node_name: str           # "manager", "financiero_planificar", "sintetizador"
    inference_type: str      # "planning", "synthesis", "specialist"
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: datetime
    metadata: Dict[str, Any]  # Modelo, provider, etc.
    
    def to_dict(self) -> dict:
        """Convierte a dict para serialización."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class TokenSession:
    """Sesión de tracking de tokens para una consulta completa."""
    query_id: str
    whatsapp: str
    mensaje: str
    start_time: datetime
    inferences: list[InferenceRecord]
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    provider: Optional[str] = None
    model: Optional[str] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convierte a dict para serialización."""
        return {
            "query_id": self.query_id,
            "whatsapp": self.whatsapp,
            "mensaje": self.mensaje,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "inferences": [inf.to_dict() for inf in self.inferences],
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "provider": self.provider,
            "model": self.model,
            "inference_count": len(self.inferences)
        }


class TokenTracker:
    """
    Singleton para tracking de tokens por consulta.
    Thread-safe usando context variables.
    """
    
    _instance: Optional["TokenTracker"] = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._enabled = True
        return cls._instance
    
    def start_session(
        self,
        query_id: Optional[str] = None,
        whatsapp: str = "",
        mensaje: str = ""
    ) -> str:
        """
        Inicia una nueva sesión de tracking.
        
        Args:
            query_id: ID único de la consulta (se genera si no se proporciona)
            whatsapp: Número de WhatsApp del usuario
            mensaje: Mensaje original del usuario
        
        Returns:
            str: query_id de la sesión iniciada
        """
        if not self._enabled:
            return query_id or str(uuid.uuid4())
        
        query_id = query_id or str(uuid.uuid4())
        
        session = TokenSession(
            query_id=query_id,
            whatsapp=whatsapp,
            mensaje=mensaje,
            start_time=datetime.now(),
            inferences=[],
            total_prompt_tokens=0,
            total_completion_tokens=0,
            total_tokens=0
        )
        
        _current_session.set(session)
        
        logger.info(
            f"[TOKEN_TRACKER] Sesión iniciada: query_id={query_id}, "
            f"whatsapp={whatsapp}, mensaje='{mensaje[:50]}...'"
        )
        
        return query_id
    
    def record_inference(
        self,
        node_name: str,
        inference_type: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registra una inferencia LLM.
        
        Args:
            node_name: Nombre del nodo (ej: "manager", "financiero_planificar")
            inference_type: Tipo de inferencia (ej: "planning", "synthesis")
            prompt_tokens: Tokens de entrada
            completion_tokens: Tokens de salida
            total_tokens: Total de tokens
            metadata: Metadata adicional (provider, model, etc.)
        """
        if not self._enabled:
            return
        
        session = _current_session.get()
        if not session:
            logger.warning(
                f"[TOKEN_TRACKER] Intento de registrar inferencia sin sesión activa: {node_name}"
            )
            return
        
        # Extraer provider y model de metadata si está disponible
        if metadata:
            if not session.provider and "provider" in metadata:
                session.provider = metadata["provider"]
            if not session.model and "model" in metadata:
                session.model = metadata["model"]
        
        # Crear registro
        inference = InferenceRecord(
            node_name=node_name,
            inference_type=inference_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # Acumular
        session.inferences.append(inference)
        session.total_prompt_tokens += prompt_tokens
        session.total_completion_tokens += completion_tokens
        session.total_tokens += total_tokens
        
        logger.debug(
            f"[TOKEN_TRACKER] Inferencia registrada: {node_name} "
            f"({inference_type}) - {total_tokens} tokens "
            f"(prompt: {prompt_tokens}, completion: {completion_tokens})"
        )
    
    def finalize_session(self) -> Optional[TokenSession]:
        """
        Finaliza la sesión actual y genera resumen.
        
        Returns:
            TokenSession: Sesión finalizada con resumen, o None si no hay sesión activa
        """
        if not self._enabled:
            return None
        
        session = _current_session.get()
        if not session:
            logger.warning("[TOKEN_TRACKER] Intento de finalizar sesión sin sesión activa")
            return None
        
        session.end_time = datetime.now()
        
        # Log estructurado
        self._log_session_summary(session)
        
        # Limpiar sesión
        _current_session.set(None)
        
        return session
    
    def get_session_summary(self) -> Optional[Dict[str, Any]]:
        """
        Retorna resumen de la sesión actual sin finalizarla.
        
        Returns:
            dict: Resumen de la sesión o None si no hay sesión activa
        """
        session = _current_session.get()
        if not session:
            return None
        
        return {
            "query_id": session.query_id,
            "whatsapp": session.whatsapp,
            "mensaje": session.mensaje,
            "start_time": session.start_time.isoformat(),
            "inference_count": len(session.inferences),
            "total_prompt_tokens": session.total_prompt_tokens,
            "total_completion_tokens": session.total_completion_tokens,
            "total_tokens": session.total_tokens,
            "provider": session.provider,
            "model": session.model,
            "inferences": [
                {
                    "node_name": inf.node_name,
                    "inference_type": inf.inference_type,
                    "tokens": inf.total_tokens,
                    "prompt_tokens": inf.prompt_tokens,
                    "completion_tokens": inf.completion_tokens
                }
                for inf in session.inferences
            ]
        }
    
    def _log_session_summary(self, session: TokenSession) -> None:
        """
        Genera log estructurado con resumen de la sesión.
        
        Args:
            session: Sesión finalizada
        """
        # Preparar datos para log JSON
        log_data = {
            "event": "token_usage_summary",
            "query_id": session.query_id,
            "whatsapp": session.whatsapp,
            "mensaje": session.mensaje[:200],  # Limitar longitud
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "duration_seconds": (
                (session.end_time - session.start_time).total_seconds()
                if session.end_time else None
            ),
            "provider": session.provider,
            "model": session.model,
            "inference_count": len(session.inferences),
            "inferences": [
                {
                    "node_name": inf.node_name,
                    "inference_type": inf.inference_type,
                    "prompt_tokens": inf.prompt_tokens,
                    "completion_tokens": inf.completion_tokens,
                    "total_tokens": inf.total_tokens,
                    "timestamp": inf.timestamp.isoformat()
                }
                for inf in session.inferences
            ],
            "totals": {
                "prompt_tokens": session.total_prompt_tokens,
                "completion_tokens": session.total_completion_tokens,
                "total_tokens": session.total_tokens
            }
        }
        
        # Log estructurado (JSON)
        logger.info(
            f"[TOKEN_USAGE] {json.dumps(log_data, ensure_ascii=False)}"
        )
        
        # Log legible para humanos
        logger.info(
            f"\n{'='*60}\n"
            f"TOKEN USAGE SUMMARY - Query ID: {session.query_id}\n"
            f"{'='*60}\n"
            f"WhatsApp: {session.whatsapp}\n"
            f"Mensaje: {session.mensaje[:100]}...\n"
            f"Provider: {session.provider or 'N/A'}\n"
            f"Model: {session.model or 'N/A'}\n"
            f"Inferencias: {len(session.inferences)}\n"
            f"\nDetalle por inferencia:\n"
            + "\n".join([
                f"  [{i+1}] {inf.node_name} ({inf.inference_type}): "
                f"{inf.total_tokens} tokens "
                f"(prompt: {inf.prompt_tokens}, completion: {inf.completion_tokens})"
                for i, inf in enumerate(session.inferences)
            ])
            + f"\n\nTOTALES:\n"
            f"  Prompt tokens: {session.total_prompt_tokens:,}\n"
            f"  Completion tokens: {session.total_completion_tokens:,}\n"
            f"  Total tokens: {session.total_tokens:,}\n"
            f"{'='*60}\n"
        )
    
    def enable(self):
        """Activa el tracking."""
        self._enabled = True
        logger.info("[TOKEN_TRACKER] Tracking activado")
    
    def disable(self):
        """Desactiva el tracking."""
        self._enabled = False
        logger.info("[TOKEN_TRACKER] Tracking desactivado")
    
    def is_enabled(self) -> bool:
        """Retorna si el tracking está activo."""
        return self._enabled


# Singleton global
token_tracker = TokenTracker()

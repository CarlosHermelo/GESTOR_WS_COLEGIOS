"""
Modelos SQLAlchemy para Gestor WS.
"""
from app.models.cache import CacheResponsable, CacheAlumno, CacheCuota
from app.models.interacciones import Interaccion, SincronizacionLog
from app.models.tickets import Ticket, NotificacionEnviada

__all__ = [
    "CacheResponsable",
    "CacheAlumno", 
    "CacheCuota",
    "Interaccion",
    "SincronizacionLog",
    "Ticket",
    "NotificacionEnviada"
]


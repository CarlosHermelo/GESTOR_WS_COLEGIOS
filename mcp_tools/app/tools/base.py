"""
Base classes y utilidades para tools.
"""
import httpx
import logging
from typing import Optional, Any
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)


class HTTPClient:
    """Cliente HTTP reutilizable para conectar a servicios."""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client
    
    async def get(self, path: str, params: dict = None) -> dict:
        """GET request."""
        client = await self._get_client()
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()
    
    async def post(self, path: str, data: dict = None) -> dict:
        """POST request."""
        client = await self._get_client()
        response = await client.post(path, json=data)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Cierra el cliente."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Clientes singleton para cada servicio
erp_client = HTTPClient(settings.ERP_URL)
kg_client = HTTPClient(settings.KNOWLEDGE_GRAPH_URL)
gestor_client = HTTPClient(settings.GESTOR_WS_URL)


# ============================================================
# DATOS MOCK
# ============================================================

MOCK_RESPONSABLE = {
    "id": "mock-resp-001",
    "nombre": "María García",
    "whatsapp": "+5491112345001",
    "email": "maria.garcia@email.com",
    "alumnos": [
        {
            "id": "mock-alumno-001",
            "nombre": "Juan",
            "apellido": "Pérez García",
            "grado": "3ro A"
        },
        {
            "id": "mock-alumno-002",
            "nombre": "Ana",
            "apellido": "Pérez García",
            "grado": "1ro B"
        }
    ]
}

MOCK_CUOTAS = [
    {
        "id": "mock-cuota-003",
        "numero_cuota": 3,
        "monto": 45000,
        "fecha_vencimiento": "15/03/2026",
        "estado": "pendiente",
        "link_pago": "https://pago.mock/cuota-003"
    },
    {
        "id": "mock-cuota-004",
        "numero_cuota": 4,
        "monto": 45000,
        "fecha_vencimiento": "15/04/2026",
        "estado": "pendiente",
        "link_pago": "https://pago.mock/cuota-004"
    }
]

MOCK_INFO_INSTITUCIONAL = {
    "horarios": {
        "primaria": {
            "turno_mañana": "7:30 - 12:30",
            "turno_tarde": "13:00 - 18:00"
        },
        "secundaria": {
            "turno_mañana": "7:15 - 13:15",
            "turno_tarde": "13:30 - 19:30"
        },
        "administracion": "8:00 - 17:00 (Lunes a Viernes)"
    },
    "calendario": {
        "inicio_clases": "4 de marzo de 2026",
        "fin_clases": "11 de diciembre de 2026",
        "receso_invierno": "14 al 25 de julio de 2026"
    },
    "autoridades": {
        "director_general": "Dr. Roberto Martínez",
        "directora_primaria": "Lic. María García",
        "director_secundaria": "Prof. Juan López",
        "coordinadora_administrativa": "Sra. Ana Fernández"
    },
    "contacto": {
        "telefono": "(011) 4555-1234",
        "email": "info@colegio.edu.ar",
        "direccion": "Av. Siempreviva 742, CABA"
    }
}

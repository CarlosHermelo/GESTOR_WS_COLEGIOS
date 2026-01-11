"""
Adaptador para el ERP Mock (Fase 1).
Implementa ERPClientInterface para comunicarse con localhost:8001.
"""
import logging
from typing import Optional
from datetime import date, timedelta

import httpx

from app.adapters.erp_interface import ERPClientInterface
from app.config import settings


logger = logging.getLogger(__name__)


class MockERPAdapter(ERPClientInterface):
    """
    Adaptador para el ERP Mock que corre en localhost:8001.
    Usa httpx para llamadas HTTP async.
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Inicializa el adaptador.
        
        Args:
            base_url: URL base del ERP. Si no se proporciona,
                     usa MOCK_ERP_URL de settings.
        """
        self.base_url = base_url or settings.MOCK_ERP_URL
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(f"MockERPAdapter inicializado con URL: {self.base_url}")
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy initialization del cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={"Content-Type": "application/json"}
            )
        return self._client
    
    async def close(self) -> None:
        """Cierra el cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_alumno(self, alumno_id: str) -> dict:
        """Obtiene datos de un alumno por ID."""
        try:
            response = await self.client.get(f"/api/v1/alumnos/{alumno_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Alumno {alumno_id} no encontrado")
                return {}
            raise
        except Exception as e:
            logger.error(f"Error obteniendo alumno {alumno_id}: {e}")
            raise
    
    async def get_alumno_cuotas(
        self, 
        alumno_id: str, 
        estado: Optional[str] = None
    ) -> list[dict]:
        """Obtiene cuotas de un alumno, opcionalmente filtradas por estado."""
        try:
            params = {"estado": estado} if estado else {}
            response = await self.client.get(
                f"/api/v1/alumnos/{alumno_id}/cuotas",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Alumno {alumno_id} no encontrado")
                return []
            raise
        except Exception as e:
            logger.error(f"Error obteniendo cuotas de {alumno_id}: {e}")
            raise
    
    async def get_responsable_by_whatsapp(self, whatsapp: str) -> dict:
        """Busca responsable por número de WhatsApp."""
        try:
            response = await self.client.get(
                f"/api/v1/responsables/by-whatsapp/{whatsapp}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Responsable con WhatsApp {whatsapp} no encontrado")
                return {}
            raise
        except Exception as e:
            logger.error(f"Error buscando responsable por WhatsApp {whatsapp}: {e}")
            raise
    
    async def get_cuota(self, cuota_id: str) -> dict:
        """Obtiene detalle de una cuota."""
        try:
            response = await self.client.get(f"/api/v1/cuotas/{cuota_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Cuota {cuota_id} no encontrada")
                return {}
            raise
        except Exception as e:
            logger.error(f"Error obteniendo cuota {cuota_id}: {e}")
            raise
    
    async def confirmar_pago(
        self,
        cuota_id: str,
        monto: float,
        metodo: str,
        referencia: str
    ) -> dict:
        """Confirma un pago en el ERP."""
        try:
            payload = {
                "cuota_id": cuota_id,
                "monto": monto,
                "metodo_pago": metodo,
                "referencia_externa": referencia
            }
            response = await self.client.post(
                "/api/v1/pagos/confirmar",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error confirmando pago: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error confirmando pago de cuota {cuota_id}: {e}")
            raise
    
    async def get_cuotas_por_vencer(self, dias: int = 7) -> list[dict]:
        """Obtiene cuotas que vencen en los próximos N días."""
        try:
            fecha_desde = date.today()
            fecha_hasta = fecha_desde + timedelta(days=dias)
            
            params = {
                "estado": "pendiente",
                "vencimiento_desde": fecha_desde.isoformat(),
                "vencimiento_hasta": fecha_hasta.isoformat()
            }
            response = await self.client.get(
                "/api/v1/cuotas",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo cuotas por vencer: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Verifica conectividad con el ERP Mock."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"ERP Mock no disponible: {e}")
            return False


# Singleton del cliente ERP
_erp_client: Optional[MockERPAdapter] = None


def get_erp_client() -> MockERPAdapter:
    """
    Factory para obtener el cliente ERP.
    Retorna singleton del adaptador configurado.
    
    Returns:
        MockERPAdapter: Instancia del cliente ERP
    """
    global _erp_client
    
    if _erp_client is None:
        if settings.ERP_TYPE == "mock":
            _erp_client = MockERPAdapter()
        else:
            raise ValueError(f"ERP_TYPE '{settings.ERP_TYPE}' no soportado")
    
    return _erp_client


async def close_erp_client() -> None:
    """Cierra el cliente ERP."""
    global _erp_client
    if _erp_client:
        await _erp_client.close()
        _erp_client = None


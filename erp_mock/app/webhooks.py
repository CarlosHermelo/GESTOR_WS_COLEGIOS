"""
Cliente para enviar webhooks al servicio Gestor WS.
Implementa retry con backoff exponencial.
"""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx

from app.config import settings
from app.schemas import WebhookPagoConfirmado, WebhookPagoConfirmadoDatos

logger = logging.getLogger(__name__)


class WebhookClient:
    """
    Cliente para enviar webhooks con retry automático.
    Usa backoff exponencial en caso de fallos.
    """
    
    def __init__(
        self,
        base_url: str = None,
        max_retries: int = None,
        base_delay: float = None
    ):
        """
        Inicializa el cliente de webhooks.
        
        Args:
            base_url: URL base del servicio destino
            max_retries: Número máximo de reintentos
            base_delay: Delay base en segundos para backoff
        """
        self.base_url = base_url or settings.gestor_ws_url
        self.max_retries = max_retries or settings.webhook_max_retries
        self.base_delay = base_delay or settings.webhook_base_delay
    
    async def _send_with_retry(
        self,
        endpoint: str,
        payload: dict,
        headers: Optional[dict] = None
    ) -> bool:
        """
        Envía un webhook con reintentos y backoff exponencial.
        
        Args:
            endpoint: Endpoint relativo (ej: /webhook/erp/pago-confirmado)
            payload: Datos a enviar en el body
            headers: Headers adicionales
        
        Returns:
            True si se envió correctamente, False si falló después de reintentos
        """
        url = f"{self.base_url}{endpoint}"
        default_headers = {
            "Content-Type": "application/json",
            "X-Webhook-Source": "erp_mock"
        }
        
        if headers:
            default_headers.update(headers)
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers=default_headers
                    )
                    
                    if response.status_code in (200, 201, 202):
                        logger.info(
                            f"Webhook enviado exitosamente a {url}",
                            extra={
                                "attempt": attempt + 1,
                                "status_code": response.status_code
                            }
                        )
                        return True
                    else:
                        logger.warning(
                            f"Webhook falló con status {response.status_code}",
                            extra={
                                "attempt": attempt + 1,
                                "url": url,
                                "response": response.text[:200]
                            }
                        )
            
            except httpx.TimeoutException:
                logger.warning(
                    f"Timeout enviando webhook a {url}",
                    extra={"attempt": attempt + 1}
                )
            
            except httpx.ConnectError:
                logger.warning(
                    f"Error de conexión enviando webhook a {url}",
                    extra={"attempt": attempt + 1}
                )
            
            except Exception as e:
                logger.error(
                    f"Error inesperado enviando webhook: {e}",
                    extra={"attempt": attempt + 1, "error": str(e)}
                )
            
            # Calcular delay con backoff exponencial
            if attempt < self.max_retries - 1:
                delay = self.base_delay * (2 ** attempt)
                logger.info(f"Reintentando en {delay} segundos...")
                await asyncio.sleep(delay)
        
        logger.error(
            f"Webhook falló después de {self.max_retries} intentos",
            extra={"url": url}
        )
        return False
    
    async def enviar_pago_confirmado(
        self,
        cuota_id: str,
        alumno_id: str,
        monto: Decimal,
        fecha_pago: datetime
    ) -> bool:
        """
        Envía webhook de pago confirmado al Gestor WS.
        
        Args:
            cuota_id: ID de la cuota pagada
            alumno_id: ID del alumno
            monto: Monto del pago
            fecha_pago: Fecha y hora del pago
        
        Returns:
            True si se envió correctamente
        """
        # Construir payload del webhook
        webhook_data = WebhookPagoConfirmado(
            tipo="pago_confirmado",
            timestamp=datetime.utcnow(),
            datos=WebhookPagoConfirmadoDatos(
                cuota_id=cuota_id,
                alumno_id=alumno_id,
                monto=monto,
                fecha_pago=fecha_pago
            )
        )
        
        # Convertir a dict serializable
        payload = webhook_data.model_dump(mode="json")
        
        logger.info(
            f"Enviando webhook de pago confirmado",
            extra={
                "cuota_id": cuota_id,
                "alumno_id": alumno_id,
                "monto": float(monto)
            }
        )
        
        return await self._send_with_retry(
            endpoint="/webhook/erp/pago-confirmado",
            payload=payload
        )


# Instancia global del cliente
webhook_client = WebhookClient()


async def notify_pago_confirmado(
    cuota_id: str,
    alumno_id: str,
    monto: Decimal,
    fecha_pago: datetime
) -> bool:
    """
    Función de conveniencia para enviar notificación de pago.
    
    Args:
        cuota_id: ID de la cuota pagada
        alumno_id: ID del alumno
        monto: Monto del pago
        fecha_pago: Fecha y hora del pago
    
    Returns:
        True si se envió correctamente
    """
    return await webhook_client.enviar_pago_confirmado(
        cuota_id=cuota_id,
        alumno_id=alumno_id,
        monto=monto,
        fecha_pago=fecha_pago
    )


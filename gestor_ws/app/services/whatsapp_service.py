"""
Servicio de WhatsApp.
Maneja el envío de mensajes (simulado por ahora).
"""
import logging
from typing import Optional

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Servicio para envío de mensajes por WhatsApp.
    Usa la Meta Cloud API (simulado por ahora).
    """
    
    def __init__(self):
        """Inicializa el servicio."""
        self.token = settings.WHATSAPP_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.base_url = "https://graph.facebook.com/v18.0"
        self._client: Optional[httpx.AsyncClient] = None
        
        # Modo simulación si token es dummy
        self.simulation_mode = self.token.startswith("dummy")
        
        if self.simulation_mode:
            logger.warning("WhatsApp en modo simulación (token dummy)")
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy initialization del cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
        return self._client
    
    async def close(self) -> None:
        """Cierra el cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def send_message(
        self,
        to_number: str,
        text: str,
        reply_to: Optional[str] = None
    ) -> dict:
        """
        Envía un mensaje de texto por WhatsApp.
        
        Args:
            to_number: Número destino con código de país
            text: Texto del mensaje
            reply_to: ID del mensaje al que responder (opcional)
            
        Returns:
            dict: Respuesta de la API o simulación
        """
        # Normalizar número (quitar +)
        to_number = to_number.replace("+", "")
        
        if self.simulation_mode:
            return await self._simulate_send(to_number, text)
        
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "text",
                "text": {"body": text}
            }
            
            if reply_to:
                payload["context"] = {"message_id": reply_to}
            
            response = await self.client.post(
                f"/{self.phone_number_id}/messages",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Mensaje enviado a {to_number}: {result}")
            
            return {
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id"),
                "to": to_number
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP enviando mensaje: {e.response.text}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
            return {"success": False, "error": str(e)}
    
    async def _simulate_send(self, to_number: str, text: str) -> dict:
        """Simula el envío de mensaje."""
        logger.info(f"[SIMULADO] Mensaje a {to_number}:")
        logger.info(f"  {text[:100]}...")
        
        return {
            "success": True,
            "message_id": f"sim_{to_number}_{hash(text)}",
            "to": to_number,
            "simulated": True
        }
    
    async def send_template(
        self,
        to_number: str,
        template_name: str,
        language_code: str = "es",
        components: Optional[list] = None
    ) -> dict:
        """
        Envía un mensaje de plantilla por WhatsApp.
        
        Args:
            to_number: Número destino
            template_name: Nombre de la plantilla
            language_code: Código de idioma
            components: Componentes de la plantilla
            
        Returns:
            dict: Respuesta de la API
        """
        to_number = to_number.replace("+", "")
        
        if self.simulation_mode:
            logger.info(f"[SIMULADO] Template '{template_name}' a {to_number}")
            return {
                "success": True,
                "message_id": f"sim_tpl_{to_number}",
                "to": to_number,
                "simulated": True
            }
        
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language_code}
                }
            }
            
            if components:
                payload["template"]["components"] = components
            
            response = await self.client.post(
                f"/{self.phone_number_id}/messages",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Template enviado a {to_number}: {result}")
            
            return {
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id"),
                "to": to_number
            }
            
        except Exception as e:
            logger.error(f"Error enviando template: {e}")
            return {"success": False, "error": str(e)}


# Singleton del servicio
_whatsapp_service: Optional[WhatsAppService] = None


def get_whatsapp_service() -> WhatsAppService:
    """Factory para obtener el servicio de WhatsApp."""
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service


async def close_whatsapp_service() -> None:
    """Cierra el servicio de WhatsApp."""
    global _whatsapp_service
    if _whatsapp_service:
        await _whatsapp_service.close()
        _whatsapp_service = None


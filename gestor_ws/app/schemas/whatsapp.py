"""
Schemas para integración con WhatsApp.
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class WhatsAppMessage(BaseModel):
    """
    Mensaje entrante de WhatsApp.
    Formato simplificado para simulación.
    """
    
    from_number: str = Field(
        ...,
        description="Número de WhatsApp del remitente con código de país",
        examples=["+5491112345001"]
    )
    text: str = Field(
        ...,
        description="Contenido del mensaje",
        examples=["Cuánto debo?"]
    )
    message_id: Optional[str] = Field(
        None,
        description="ID único del mensaje de WhatsApp"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp del mensaje"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "from_number": "+5491112345001",
                "text": "Hola, quiero saber cuánto debo"
            }
        }


class WhatsAppResponse(BaseModel):
    """Respuesta a enviar por WhatsApp."""
    
    to_number: str = Field(
        ...,
        description="Número de WhatsApp del destinatario"
    )
    text: str = Field(
        ...,
        description="Contenido del mensaje a enviar"
    )
    reply_to: Optional[str] = Field(
        None,
        description="ID del mensaje al que se responde"
    )


class WebhookPayload(BaseModel):
    """
    Payload completo del webhook de WhatsApp (Meta Cloud API).
    Este es el formato real de Meta, simplificado para simulación.
    """
    
    object: str = "whatsapp_business_account"
    entry: list[dict[str, Any]] = Field(default_factory=list)
    
    @classmethod
    def from_simple_message(cls, from_number: str, text: str) -> "WebhookPayload":
        """
        Crea un WebhookPayload desde un mensaje simple.
        Útil para testing.
        """
        return cls(
            object="whatsapp_business_account",
            entry=[{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "from": from_number.replace("+", ""),
                            "type": "text",
                            "text": {"body": text},
                            "timestamp": str(int(datetime.now().timestamp()))
                        }]
                    }
                }]
            }]
        )


class WebhookVerification(BaseModel):
    """Parámetros para verificación de webhook de Meta."""
    
    hub_mode: str = Field(alias="hub.mode")
    hub_verify_token: str = Field(alias="hub.verify_token")
    hub_challenge: str = Field(alias="hub.challenge")
    
    class Config:
        populate_by_name = True


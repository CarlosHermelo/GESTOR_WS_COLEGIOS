"""
Router de mensajes - Capa 1 (Sin LLM).
Clasifica mensajes por keywords para decidir qué agente procesa.
"""
import logging
from enum import Enum
from typing import Optional


logger = logging.getLogger(__name__)


class RouteType(str, Enum):
    """Tipos de ruta disponibles."""
    ASISTENTE = "asistente"
    AGENTE = "agente"
    SALUDO = "saludo"


class MessageRouter:
    """
    Router de mensajes basado en keywords.
    No usa LLM, solo análisis de texto simple.
    """
    
    # Keywords que indican consultas simples → Asistente
    KEYWORDS_SIMPLE = [
        "cuanto debo",
        "cuánto debo",
        "saldo",
        "link",
        "pagar",
        "vencimiento",
        "cuota",
        "pendiente",
        "deuda",
        "estado de cuenta",
        "mis hijos",
        "alumno"
    ]
    
    # Keywords que indican casos complejos → Agente Coordinador
    KEYWORDS_ESCALAMIENTO = [
        "reclamo",
        "queja",
        "baja",
        "urgente",
        "error",
        "problema",
        "hablar con alguien",
        "humano",
        "plan de pago",
        "plan de pagos",
        "descuento",
        "beca",
        "no puedo pagar",
        "dificultad",
        "injusto",
        "mal cobro"
    ]
    
    # Keywords de saludo
    KEYWORDS_SALUDO = [
        "hola",
        "buenos días",
        "buenas tardes",
        "buenas noches",
        "buen día",
        "hey",
        "hi"
    ]
    
    def __init__(self):
        """Inicializa el router."""
        logger.info("MessageRouter inicializado")
    
    def route(self, message: str) -> RouteType:
        """
        Determina la ruta apropiada para un mensaje.
        
        Args:
            message: Texto del mensaje entrante
            
        Returns:
            RouteType: Tipo de ruta (asistente, agente, saludo)
        """
        msg_lower = message.lower().strip()
        
        # Primero verificar escalamiento (prioridad)
        if self._contains_keywords(msg_lower, self.KEYWORDS_ESCALAMIENTO):
            logger.info(f"Mensaje ruteado a AGENTE: '{message[:50]}...'")
            return RouteType.AGENTE
        
        # Verificar consultas simples
        if self._contains_keywords(msg_lower, self.KEYWORDS_SIMPLE):
            logger.info(f"Mensaje ruteado a ASISTENTE: '{message[:50]}...'")
            return RouteType.ASISTENTE
        
        # Verificar saludos (solo si es muy corto)
        if len(msg_lower) < 30 and self._contains_keywords(msg_lower, self.KEYWORDS_SALUDO):
            logger.info(f"Mensaje detectado como SALUDO: '{message[:50]}...'")
            return RouteType.SALUDO
        
        # Por defecto → Asistente
        logger.info(f"Mensaje ruteado a ASISTENTE (default): '{message[:50]}...'")
        return RouteType.ASISTENTE
    
    def _contains_keywords(self, text: str, keywords: list[str]) -> bool:
        """Verifica si el texto contiene alguna keyword."""
        return any(kw in text for kw in keywords)
    
    def get_route_info(self, message: str) -> dict:
        """
        Retorna información detallada sobre el ruteo.
        Útil para debugging y logging.
        
        Args:
            message: Texto del mensaje
            
        Returns:
            dict: Información del ruteo
        """
        msg_lower = message.lower().strip()
        route = self.route(message)
        
        # Encontrar keywords que matchearon
        matched_simple = [kw for kw in self.KEYWORDS_SIMPLE if kw in msg_lower]
        matched_escalamiento = [kw for kw in self.KEYWORDS_ESCALAMIENTO if kw in msg_lower]
        matched_saludo = [kw for kw in self.KEYWORDS_SALUDO if kw in msg_lower]
        
        return {
            "route": route.value,
            "message_preview": message[:100],
            "matched_keywords": {
                "simple": matched_simple,
                "escalamiento": matched_escalamiento,
                "saludo": matched_saludo
            },
            "reason": self._get_route_reason(route, matched_simple, matched_escalamiento, matched_saludo)
        }
    
    def _get_route_reason(
        self,
        route: RouteType,
        simple: list,
        escalamiento: list,
        saludo: list
    ) -> str:
        """Genera una razón legible para el ruteo."""
        if route == RouteType.AGENTE:
            return f"Escalamiento por keywords: {escalamiento}"
        elif route == RouteType.SALUDO:
            return f"Saludo detectado: {saludo}"
        elif simple:
            return f"Consulta simple por keywords: {simple}"
        else:
            return "Ruta por defecto (sin keywords específicas)"


# Respuestas predefinidas para saludos
RESPUESTAS_SALUDO = [
    "¡Hola! 👋 Soy el asistente de cobranza del Colegio. ¿En qué puedo ayudarte?\n\n"
    "Puedo informarte sobre:\n"
    "• Tu estado de cuenta\n"
    "• Cuotas pendientes\n"
    "• Links de pago\n"
    "• Fechas de vencimiento",
    
    "¡Buen día! 😊 ¿Cómo puedo ayudarte hoy?\n\n"
    "Escribí algo como:\n"
    "• \"Cuánto debo?\"\n"
    "• \"Envíame el link de pago\"\n"
    "• \"Cuándo vence mi cuota?\""
]


def get_saludo_response() -> str:
    """Retorna una respuesta de saludo aleatoria."""
    import random
    return random.choice(RESPUESTAS_SALUDO)


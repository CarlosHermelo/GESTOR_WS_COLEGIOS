"""
Agente Autónomo - Wrapper para Code Planner.

Usa el CodePlannerAgent para procesar consultas generando y ejecutando
código Python que invoca herramientas MCP.
"""
import logging
from typing import Optional

from app.agents.code_planner import CodePlannerAgent, get_code_planner_agent
from app.services.token_tracker import token_tracker
from app.adapters.mock_erp_adapter import get_erp_client

logger = logging.getLogger(__name__)


class AgenteAutonomo:
    """
    Agente Autónomo basado en Code Planner.
    Wrapper simple que delega todo al CodePlannerAgent.
    """
    
    def __init__(self):
        """Inicializa el agente."""
        self._code_planner: Optional[CodePlannerAgent] = None
        # FORCE: Usar localhost explícitamente para pruebas locales
        from app.adapters.mock_erp_adapter import MockERPAdapter
        self.erp = MockERPAdapter(base_url="http://localhost:8001")
        logger.info("AgenteAutonomo inicializado (Code Planner) con ERP local")
    
    def _get_code_planner(self) -> CodePlannerAgent:
        """Obtiene o crea el Code Planner."""
        if self._code_planner is None:
            self._code_planner = get_code_planner_agent()
        return self._code_planner
    
    async def _cargar_contexto_usuario(self, whatsapp: str) -> dict:
        """Carga el contexto del usuario desde el ERP."""
        from app.config import settings
        
        if settings.MOCK_MODE:
            return {
                "phone": whatsapp,
                "responsable_id": "mock-resp-001",
                "nombre": "María García",
                "alumnos": [
                    {"id": "mock-alumno-001", "nombre": "Juan", "apellido": "Pérez García", "grado": "3ro A"},
                    {"id": "mock-alumno-002", "nombre": "Ana", "apellido": "Pérez García", "grado": "1ro B"}
                ]
            }
        
        try:
            responsable = await self.erp.get_responsable_by_whatsapp(whatsapp)
            if responsable:
                return {
                    "phone": whatsapp,
                    "responsable_id": responsable.get("id"),
                    "nombre": responsable.get("nombre", ""),
                    "alumnos": responsable.get("alumnos", [])
                }
        except Exception as e:
            logger.warning(f"Error cargando contexto: {e}")
        
        return {"phone": whatsapp}
    
    async def procesar(
        self,
        whatsapp: str,
        mensaje: str,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Procesa un mensaje del usuario.
        
        Args:
            whatsapp: Número de WhatsApp
            mensaje: Texto del mensaje
            thread_id: ID del thread (no usado, mantenido por compatibilidad)
            
        Returns:
            str: Respuesta del agente
        """
        return await self.procesar_sin_checkpoint(whatsapp, mensaje)
    
    async def procesar_sin_checkpoint(
        self,
        whatsapp: str,
        mensaje: str
    ) -> str:
        """
        Procesa un mensaje usando el Code Planner.
        
        Args:
            whatsapp: Número de WhatsApp
            mensaje: Texto del mensaje
            
        Returns:
            str: Respuesta del agente
        """
        try:
            logger.info(f"Procesando mensaje de {whatsapp}: '{mensaje}'")
            
            # Iniciar sesión de tracking de tokens
            query_id = token_tracker.start_session(
                whatsapp=whatsapp,
                mensaje=mensaje
            )
            
            # Cargar contexto del usuario
            user_context = await self._cargar_contexto_usuario(whatsapp)
            
            # Procesar con Code Planner
            code_planner = self._get_code_planner()
            respuesta = await code_planner.process(
                phone_number=whatsapp,
                mensaje=mensaje,
                user_context=user_context
            )
            
            # Finalizar sesión de tracking
            session = token_tracker.finalize_session()
            if session:
                logger.info(
                    f"[TOKEN_TRACKER] Consulta finalizada: {query_id}, "
                    f"Total tokens: {session.total_tokens:,}"
                )
            
            return respuesta
            
        except Exception as e:
            logger.error(f"Error en AgenteAutonomo: {e}", exc_info=True)
            
            # Finalizar sesión de tracking incluso en caso de error
            try:
                session = token_tracker.finalize_session()
            except Exception:
                pass
            
            return (
                "Disculpá, tuve un problema procesando tu solicitud. 😅\n\n"
                "Por favor, intentá de nuevo."
            )


# ============================================================
# FACTORY
# ============================================================

_agente_instance: Optional[AgenteAutonomo] = None


def get_agente_autonomo() -> AgenteAutonomo:
    """
    Factory para obtener instancia del agente.
    
    Returns:
        AgenteAutonomo: Instancia del agente
    """
    global _agente_instance
    
    if _agente_instance is None:
        _agente_instance = AgenteAutonomo()
    
    return _agente_instance

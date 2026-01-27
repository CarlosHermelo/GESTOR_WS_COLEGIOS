"""
Tests para el Router de mensajes.
"""
import pytest
from app.agents.router import MessageRouter, RouteType


class TestMessageRouter:
    """Tests para MessageRouter."""
    
    @pytest.fixture
    def router(self):
        """Fixture del router."""
        return MessageRouter()
    
    def test_route_consulta_simple_cuanto_debo(self, router):
        """Test que consultas de saldo van al asistente."""
        mensaje = "Cuánto debo?"
        ruta = router.route(mensaje)
        assert ruta == RouteType.ASISTENTE
    
    def test_route_consulta_simple_saldo(self, router):
        """Test keyword saldo."""
        mensaje = "Quiero ver mi saldo"
        ruta = router.route(mensaje)
        assert ruta == RouteType.ASISTENTE
    
    def test_route_consulta_simple_link_pago(self, router):
        """Test keyword link de pago."""
        mensaje = "Pasame el link de pago"
        ruta = router.route(mensaje)
        assert ruta == RouteType.ASISTENTE
    
    def test_route_consulta_simple_vencimiento(self, router):
        """Test keyword vencimiento."""
        mensaje = "Cuándo vence la cuota?"
        ruta = router.route(mensaje)
        assert ruta == RouteType.ASISTENTE
    
    def test_route_escalamiento_reclamo(self, router):
        """Test que reclamos van al agente."""
        mensaje = "Tengo un reclamo sobre el cobro"
        ruta = router.route(mensaje)
        assert ruta == RouteType.AGENTE
    
    def test_route_escalamiento_plan_pago(self, router):
        """Test que solicitudes de plan de pago van al agente."""
        mensaje = "Necesito un plan de pagos"
        ruta = router.route(mensaje)
        assert ruta == RouteType.AGENTE
    
    def test_route_escalamiento_baja(self, router):
        """Test que solicitudes de baja van al agente."""
        mensaje = "Quiero dar de baja a mi hijo"
        ruta = router.route(mensaje)
        assert ruta == RouteType.AGENTE
    
    def test_route_escalamiento_urgente(self, router):
        """Test keyword urgente."""
        mensaje = "Es urgente, necesito hablar con alguien"
        ruta = router.route(mensaje)
        assert ruta == RouteType.AGENTE
    
    def test_route_saludo_hola(self, router):
        """Test saludos cortos."""
        mensaje = "Hola"
        ruta = router.route(mensaje)
        assert ruta == RouteType.SALUDO
    
    def test_route_saludo_buenos_dias(self, router):
        """Test saludo buenos días."""
        mensaje = "Buenos días"
        ruta = router.route(mensaje)
        assert ruta == RouteType.SALUDO
    
    def test_route_default_asistente(self, router):
        """Test que mensajes sin keywords van al asistente por defecto."""
        mensaje = "Tengo una consulta general"
        ruta = router.route(mensaje)
        assert ruta == RouteType.ASISTENTE
    
    def test_route_escalamiento_tiene_prioridad(self, router):
        """Test que escalamiento tiene prioridad sobre consulta simple."""
        mensaje = "Cuánto debo? Tengo un reclamo"
        ruta = router.route(mensaje)
        assert ruta == RouteType.AGENTE
    
    def test_get_route_info(self, router):
        """Test que get_route_info retorna información detallada."""
        mensaje = "Cuánto debo?"
        info = router.get_route_info(mensaje)
        
        assert "route" in info
        assert "message_preview" in info
        assert "matched_keywords" in info
        assert "reason" in info
        
        assert info["route"] == "asistente"
        assert "cuanto debo" in info["matched_keywords"]["simple"] or \
               "cuánto debo" in info["matched_keywords"]["simple"]


class TestRouteTypeEnum:
    """Tests para el enum RouteType."""
    
    def test_values(self):
        """Test valores del enum."""
        assert RouteType.ASISTENTE.value == "asistente"
        assert RouteType.AGENTE.value == "agente"
        assert RouteType.SALUDO.value == "saludo"




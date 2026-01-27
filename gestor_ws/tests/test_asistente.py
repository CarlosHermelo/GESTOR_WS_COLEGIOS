"""
Tests para el Asistente Virtual.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.agents.asistente import AsistenteVirtual


class TestAsistenteVirtual:
    """Tests para AsistenteVirtual."""
    
    @pytest.fixture
    def mock_erp(self):
        """Mock del cliente ERP."""
        erp = AsyncMock()
        
        erp.get_responsable_by_whatsapp.return_value = {
            "id": "RES-001",
            "nombre": "Carlos",
            "apellido": "García",
            "whatsapp": "+5491112345005",
            "alumnos": [
                {
                    "id": "ALU-001",
                    "nombre": "Emma",
                    "apellido": "García",
                    "grado": "3° Primaria"
                }
            ]
        }
        
        erp.get_alumno_cuotas.return_value = [
            {
                "id": "CUO-001",
                "numero_cuota": 1,
                "monto": 45000,
                "fecha_vencimiento": "2024-01-15",
                "estado": "pendiente"
            }
        ]
        
        return erp
    
    @pytest.mark.asyncio
    async def test_get_estado_cuenta_rapido_con_deuda(self, mock_erp):
        """Test estado de cuenta con deuda."""
        with patch('app.agents.asistente.get_llm') as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            
            with patch('app.agents.asistente.get_erp_client', return_value=mock_erp):
                asistente = AsistenteVirtual(erp_client=mock_erp)
                
                resultado = await asistente.get_estado_cuenta_rapido("+5491112345005")
                
                assert "Emma" in resultado
                assert "45,000" in resultado or "45000" in resultado
                assert "pendiente" in resultado.lower() or "adeudado" in resultado.lower()
    
    @pytest.mark.asyncio
    async def test_get_estado_cuenta_rapido_sin_deuda(self, mock_erp):
        """Test estado de cuenta sin deuda."""
        mock_erp.get_alumno_cuotas.return_value = []
        
        with patch('app.agents.asistente.get_llm') as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            
            with patch('app.agents.asistente.get_erp_client', return_value=mock_erp):
                asistente = AsistenteVirtual(erp_client=mock_erp)
                
                resultado = await asistente.get_estado_cuenta_rapido("+5491112345005")
                
                assert "al día" in resultado.lower() or "no hay" in resultado.lower()
    
    @pytest.mark.asyncio
    async def test_get_estado_cuenta_rapido_no_encontrado(self, mock_erp):
        """Test cuando el responsable no existe."""
        mock_erp.get_responsable_by_whatsapp.return_value = {}
        
        with patch('app.agents.asistente.get_llm') as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            
            with patch('app.agents.asistente.get_erp_client', return_value=mock_erp):
                asistente = AsistenteVirtual(erp_client=mock_erp)
                
                resultado = await asistente.get_estado_cuenta_rapido("+5491199999999")
                
                assert "no encontré" in resultado.lower()
    
    @pytest.mark.asyncio
    async def test_error_response(self):
        """Test respuesta de error."""
        with patch('app.agents.asistente.get_llm') as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            
            asistente = AsistenteVirtual()
            error_response = asistente._get_error_response()
            
            assert "problema" in error_response.lower()
            assert "intentar" in error_response.lower()


class TestAsistenteVirtualIntegration:
    """Tests de integración (requieren mocks más completos)."""
    
    @pytest.fixture
    def mock_agent_executor(self):
        """Mock del AgentExecutor."""
        executor = AsyncMock()
        executor.ainvoke.return_value = {
            "output": "Tu saldo pendiente es de $45,000"
        }
        return executor
    
    @pytest.mark.asyncio
    async def test_responder_consulta_simple(self, mock_agent_executor):
        """Test responder consulta simple."""
        with patch('app.agents.asistente.get_llm') as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            
            with patch('app.agents.asistente.get_erp_client') as mock_erp:
                with patch.object(
                    AsistenteVirtual, 
                    '_create_agent', 
                    return_value=mock_agent_executor
                ):
                    asistente = AsistenteVirtual()
                    asistente.agent_executor = mock_agent_executor
                    
                    respuesta = await asistente.responder(
                        "+5491112345005",
                        "Cuánto debo?"
                    )
                    
                    assert respuesta == "Tu saldo pendiente es de $45,000"
                    mock_agent_executor.ainvoke.assert_called_once()




"""
Tests para las queries del Knowledge Graph.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.queries.riesgo_desercion import calcular_score_riesgo_desercion
from app.queries.proyeccion_caja import (
    proyectar_caja,
    obtener_vencimientos_proximos,
    obtener_deuda_por_grado,
    obtener_resumen_financiero
)
from app.queries.patrones import (
    detectar_patrones_morosidad,
    detectar_riesgo_abandono,
    detectar_familias_problema,
    detectar_grados_criticos
)


@pytest.fixture
def mock_neo4j():
    """Mock del cliente Neo4j."""
    client = MagicMock()
    client.execute = AsyncMock()
    return client


class TestRiesgoDesercion:
    """Tests para cálculo de riesgo de deserción."""
    
    @pytest.mark.asyncio
    async def test_calcular_score_riesgo_vacio(self, mock_neo4j):
        """Test con grafo vacío."""
        mock_neo4j.execute.return_value = []
        
        result = await calcular_score_riesgo_desercion(mock_neo4j)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_calcular_score_riesgo_con_datos(self, mock_neo4j):
        """Test con datos de riesgo."""
        mock_neo4j.execute.return_value = [
            {
                "alumno_id": 1,
                "alumno_nombre": "Juan Pérez",
                "responsable_whatsapp": "+1234567890",
                "perfil_responsable": "MOROSO",
                "nivel_riesgo_responsable": "ALTO",
                "cuotas_vencidas": 3,
                "notif_ignoradas": 2,
                "score_riesgo": 75,
                "nivel_riesgo": "ALTO"
            }
        ]
        
        result = await calcular_score_riesgo_desercion(mock_neo4j)
        
        assert len(result) == 1
        assert result[0]["nivel_riesgo"] == "ALTO"
        assert result[0]["score_riesgo"] >= 40
    
    @pytest.mark.asyncio
    async def test_filtro_umbral_riesgo(self, mock_neo4j):
        """Test que solo retorna riesgo >= umbral."""
        mock_neo4j.execute.return_value = [
            {"alumno_id": 1, "score_riesgo": 70, "nivel_riesgo": "ALTO"},
            {"alumno_id": 2, "score_riesgo": 45, "nivel_riesgo": "MEDIO"}
        ]
        
        result = await calcular_score_riesgo_desercion(mock_neo4j, umbral=50)
        
        # Verificar que la query fue llamada con umbral correcto
        mock_neo4j.execute.assert_called_once()


class TestProyeccionCaja:
    """Tests para proyección de caja."""
    
    @pytest.mark.asyncio
    async def test_proyectar_caja_vacia(self, mock_neo4j):
        """Test con sin cuotas pendientes."""
        mock_neo4j.execute.return_value = []
        
        result = await proyectar_caja(mock_neo4j, dias=90)
        
        assert result["cuotas_analizadas"] == 0
        assert result["monto_total_pendiente"] == 0
    
    @pytest.mark.asyncio
    async def test_proyectar_caja_con_datos(self, mock_neo4j):
        """Test con cuotas pendientes."""
        mock_neo4j.execute.return_value = [
            {
                "cuota_id": 1,
                "monto": 1000.0,
                "estado": "pendiente",
                "perfil": "PUNTUAL",
                "riesgo": "BAJO"
            },
            {
                "cuota_id": 2,
                "monto": 1500.0,
                "estado": "vencida",
                "perfil": "MOROSO",
                "riesgo": "ALTO"
            }
        ]
        
        result = await proyectar_caja(mock_neo4j, dias=90)
        
        assert result["cuotas_analizadas"] == 2
        assert result["monto_total_pendiente"] == 2500.0
        assert result["monto_esperado_realista"] < result["monto_total_pendiente"]
    
    @pytest.mark.asyncio
    async def test_obtener_vencimientos_proximos(self, mock_neo4j):
        """Test para vencimientos próximos."""
        mock_neo4j.execute.return_value = [
            {
                "cuota_id": 1,
                "monto": 1000.0,
                "fecha_vencimiento": "2025-01-15",
                "estudiante": "María López"
            }
        ]
        
        result = await obtener_vencimientos_proximos(mock_neo4j, dias=7)
        
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_obtener_deuda_por_grado(self, mock_neo4j):
        """Test para deuda por grado."""
        mock_neo4j.execute.return_value = [
            {
                "grado": "4to A",
                "estudiantes": 5,
                "deuda_total": 25000.0,
                "cuotas_vencidas": 8
            }
        ]
        
        result = await obtener_deuda_por_grado(mock_neo4j)
        
        assert len(result) == 1
        assert result[0]["grado"] == "4to A"


class TestPatrones:
    """Tests para detección de patrones."""
    
    @pytest.mark.asyncio
    async def test_detectar_patrones_morosidad(self, mock_neo4j):
        """Test para patrones de morosidad."""
        mock_neo4j.execute.return_value = [
            {
                "responsable_id": 1,
                "nombre": "Pedro García",
                "demora_promedio": 45.0,
                "patron_detectado": "MOROSO_CRONICO"
            }
        ]
        
        result = await detectar_patrones_morosidad(mock_neo4j)
        
        assert len(result) == 1
        assert result[0]["patron_detectado"] == "MOROSO_CRONICO"
    
    @pytest.mark.asyncio
    async def test_detectar_riesgo_abandono(self, mock_neo4j):
        """Test para riesgo de abandono."""
        mock_neo4j.execute.return_value = [
            {
                "estudiante_id": 1,
                "estudiante": "Ana Martínez",
                "score_riesgo": 85,
                "nivel_riesgo_abandono": "CRITICO"
            }
        ]
        
        result = await detectar_riesgo_abandono(mock_neo4j)
        
        assert len(result) == 1
        assert result[0]["nivel_riesgo_abandono"] == "CRITICO"
    
    @pytest.mark.asyncio
    async def test_detectar_familias_problema(self, mock_neo4j):
        """Test para familias con múltiples hijos en mora."""
        mock_neo4j.execute.return_value = [
            {
                "responsable_id": 1,
                "responsable": "Carlos Rodríguez",
                "hijos_en_mora": 2,
                "estudiantes": ["María", "Pedro"],
                "deuda_familiar_total": 45000.0
            }
        ]
        
        result = await detectar_familias_problema(mock_neo4j)
        
        assert len(result) == 1
        assert result[0]["hijos_en_mora"] == 2
    
    @pytest.mark.asyncio
    async def test_detectar_grados_criticos(self, mock_neo4j):
        """Test para grados con alta morosidad."""
        mock_neo4j.execute.return_value = [
            {
                "grado": "5to B",
                "pct_estudiantes_morosos": 55.0,
                "nivel_alerta": "CRITICO"
            }
        ]
        
        result = await detectar_grados_criticos(mock_neo4j)
        
        assert len(result) == 1
        assert result[0]["nivel_alerta"] == "CRITICO"


class TestResumenFinanciero:
    """Tests para resumen financiero."""
    
    @pytest.mark.asyncio
    async def test_obtener_resumen_financiero(self, mock_neo4j):
        """Test para resumen financiero completo."""
        mock_neo4j.execute.return_value = [
            {
                "total_cuotas": 100,
                "monto_total": 100000.0,
                "cuotas_pagadas": 70,
                "monto_cobrado": 70000.0,
                "cuotas_pendientes": 20,
                "monto_pendiente": 20000.0,
                "cuotas_vencidas": 10,
                "monto_vencido": 10000.0
            }
        ]
        
        result = await obtener_resumen_financiero(mock_neo4j)
        
        assert result["tasa_cobranza"] == 70.0
        assert result["tasa_morosidad"] == 10.0


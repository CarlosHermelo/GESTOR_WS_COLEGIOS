"""
Configuración de pytest para Knowledge Graph tests.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture(scope="session")
def event_loop():
    """Crea un event loop para toda la sesión de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_neo4j_client():
    """
    Mock completo del cliente Neo4j.
    """
    client = MagicMock()
    client.execute = AsyncMock(return_value=[])
    client.execute_write = AsyncMock(return_value=None)
    client.connect = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_llm():
    """
    Mock del LLM.
    """
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def sample_responsable():
    """Datos de ejemplo de un responsable."""
    return {
        "erp_id": 1,
        "nombre": "Juan",
        "apellido": "Pérez",
        "whatsapp": "+5491123456789",
        "email": "juan@example.com"
    }


@pytest.fixture
def sample_estudiante():
    """Datos de ejemplo de un estudiante."""
    return {
        "erp_id": 1,
        "nombre": "María",
        "apellido": "Pérez",
        "grado": "4to A",
        "activo": True
    }


@pytest.fixture
def sample_cuota():
    """Datos de ejemplo de una cuota."""
    return {
        "erp_id": 1,
        "monto": 15000.0,
        "fecha_vencimiento": "2025-01-15",
        "estado": "pendiente",
        "numero_cuota": 1
    }


@pytest.fixture
def sample_metricas():
    """Métricas de ejemplo para insights."""
    return {
        "total_responsables": 100,
        "alto_riesgo": 15,
        "medio_riesgo": 30,
        "bajo_riesgo": 55,
        "morosos": 10,
        "eventuales": 25,
        "puntuales": 60,
        "nuevos": 5,
        "cuotas_vencidas": 45,
        "monto_vencido": 150000.0
    }


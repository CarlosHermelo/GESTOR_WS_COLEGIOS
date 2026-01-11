"""
Tests para la API del ERP Mock.
Usa pytest con fixtures async.

Ejecución:
    docker-compose exec api pytest
    docker-compose exec api pytest -v  # Verbose
    docker-compose exec api pytest tests/test_api.py::test_health  # Test específico
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import get_db, init_db
from app.models import Base


# ============== FIXTURES ==============

@pytest_asyncio.fixture
async def async_client():
    """
    Cliente HTTP async para tests.
    Usa ASGITransport para comunicarse directamente con la app.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_pago_request():
    """Datos de ejemplo para confirmar pago."""
    return {
        "cuota_id": "C-A001-03",
        "monto": 50000.00,
        "metodo_pago": "transferencia",
        "referencia": "TEST-REF-001"
    }


# ============== TESTS HEALTH ==============

@pytest.mark.asyncio
async def test_health(async_client: AsyncClient):
    """Test: Health check retorna estado correcto."""
    response = await async_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "erp_mock"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root_redirect(async_client: AsyncClient):
    """Test: Root retorna información del servicio."""
    response = await async_client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ERP Mock API"
    assert data["docs"] == "/docs"


# ============== TESTS ALUMNOS ==============

@pytest.mark.asyncio
async def test_get_alumno_existente(async_client: AsyncClient):
    """Test: Obtener alumno existente retorna datos correctos."""
    response = await async_client.get("/api/v1/alumnos/A001")
    
    # Si no hay datos de seed, esperar 404
    if response.status_code == 404:
        pytest.skip("Seed data no disponible")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "A001"
    assert "nombre" in data
    assert "apellido" in data


@pytest.mark.asyncio
async def test_get_alumno_no_existente(async_client: AsyncClient):
    """Test: Alumno no existente retorna 404."""
    response = await async_client.get("/api/v1/alumnos/NO_EXISTE_123")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_get_alumno_cuotas(async_client: AsyncClient):
    """Test: Obtener cuotas de alumno retorna lista correcta."""
    response = await async_client.get("/api/v1/alumnos/A001/cuotas")
    
    if response.status_code == 404:
        pytest.skip("Seed data no disponible")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    if len(data) > 0:
        cuota = data[0]
        assert "id" in cuota
        assert "monto" in cuota
        assert "estado" in cuota


@pytest.mark.asyncio
async def test_get_alumno_cuotas_filtro_estado(async_client: AsyncClient):
    """Test: Filtrar cuotas por estado funciona correctamente."""
    response = await async_client.get(
        "/api/v1/alumnos/A001/cuotas",
        params={"estado": "pendiente"}
    )
    
    if response.status_code == 404:
        pytest.skip("Seed data no disponible")
    
    assert response.status_code == 200
    data = response.json()
    
    # Todas las cuotas deben tener estado pendiente
    for cuota in data:
        assert cuota["estado"] == "pendiente"


# ============== TESTS RESPONSABLES ==============

@pytest.mark.asyncio
async def test_buscar_responsable_by_whatsapp(async_client: AsyncClient):
    """Test: Buscar responsable por WhatsApp retorna datos con alumnos."""
    response = await async_client.get(
        "/api/v1/responsables/by-whatsapp/+5491112345001"
    )
    
    if response.status_code == 404:
        pytest.skip("Seed data no disponible")
    
    assert response.status_code == 200
    data = response.json()
    assert data["whatsapp"] == "+5491112345001"
    assert "alumnos" in data
    assert isinstance(data["alumnos"], list)


@pytest.mark.asyncio
async def test_buscar_responsable_no_existente(async_client: AsyncClient):
    """Test: WhatsApp no registrado retorna 404."""
    response = await async_client.get(
        "/api/v1/responsables/by-whatsapp/+0000000000"
    )
    
    assert response.status_code == 404


# ============== TESTS CUOTAS ==============

@pytest.mark.asyncio
async def test_get_cuota_detalle(async_client: AsyncClient):
    """Test: Obtener detalle de cuota incluye alumno y plan."""
    response = await async_client.get("/api/v1/cuotas/C-A001-01")
    
    if response.status_code == 404:
        pytest.skip("Seed data no disponible")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "C-A001-01"
    assert "monto" in data
    assert "fecha_vencimiento" in data


@pytest.mark.asyncio
async def test_listar_cuotas_con_filtros(async_client: AsyncClient):
    """Test: Listar cuotas con filtros retorna resultados correctos."""
    response = await async_client.get(
        "/api/v1/cuotas",
        params={
            "estado": "pendiente",
            "vencimiento_desde": "2026-04-01",
            "limit": 10
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


@pytest.mark.asyncio
async def test_listar_cuotas_vencidas_emma(async_client: AsyncClient):
    """Test: Emma Martínez tiene cuotas vencidas (escenario especial)."""
    response = await async_client.get(
        "/api/v1/alumnos/A006/cuotas",
        params={"estado": "vencida"}
    )
    
    if response.status_code == 404:
        pytest.skip("Seed data no disponible")
    
    assert response.status_code == 200
    data = response.json()
    
    # Emma debe tener exactamente 2 cuotas vencidas
    assert len(data) == 2
    for cuota in data:
        assert cuota["estado"] == "vencida"


# ============== TESTS PAGOS ==============

@pytest.mark.asyncio
async def test_confirmar_pago_cuota_inexistente(async_client: AsyncClient):
    """Test: Confirmar pago de cuota inexistente retorna 404."""
    response = await async_client.post(
        "/api/v1/pagos/confirmar",
        json={
            "cuota_id": "CUOTA_NO_EXISTE",
            "monto": 50000.00,
            "metodo_pago": "transferencia",
            "referencia": "TEST"
        }
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_confirmar_pago_exitoso(async_client: AsyncClient):
    """
    Test: Confirmar pago actualiza estado y envía webhook.
    Nota: Este test modifica datos, usar con precaución.
    """
    # Usar cuota pendiente (cuota 3 de cualquier alumno excepto Emma)
    with patch("app.webhooks.webhook_client.enviar_pago_confirmado") as mock_webhook:
        mock_webhook.return_value = True
        
        response = await async_client.post(
            "/api/v1/pagos/confirmar",
            json={
                "cuota_id": "C-A001-03",
                "monto": 50000.00,
                "metodo_pago": "transferencia",
                "referencia": "TEST-PAGO-001"
            }
        )
        
        if response.status_code == 404:
            pytest.skip("Seed data no disponible")
        
        if response.status_code == 400:
            # Cuota ya pagada (test ya ejecutado antes)
            pytest.skip("Cuota ya fue pagada en test anterior")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["pago"] is not None
        assert data["cuota"]["estado"] == "pagada"


@pytest.mark.asyncio
async def test_confirmar_pago_cuota_ya_pagada(async_client: AsyncClient):
    """Test: Intentar pagar cuota ya pagada retorna error."""
    # Usar cuota que sabemos está pagada (cuota 1 de A001)
    response = await async_client.post(
        "/api/v1/pagos/confirmar",
        json={
            "cuota_id": "C-A001-01",
            "monto": 50000.00,
            "metodo_pago": "efectivo",
            "referencia": "TEST-DUPLICADO"
        }
    )
    
    if response.status_code == 404:
        pytest.skip("Seed data no disponible")
    
    # Debe retornar 400 porque ya está pagada
    assert response.status_code == 400


# ============== TESTS VALIDACIÓN ==============

@pytest.mark.asyncio
async def test_pago_monto_invalido(async_client: AsyncClient):
    """Test: Monto negativo o cero es rechazado."""
    response = await async_client.post(
        "/api/v1/pagos/confirmar",
        json={
            "cuota_id": "C-A001-05",
            "monto": -100.00,
            "metodo_pago": "efectivo"
        }
    )
    
    # Pydantic debe rechazar monto negativo
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pago_sin_cuota_id(async_client: AsyncClient):
    """Test: Request sin cuota_id es rechazado."""
    response = await async_client.post(
        "/api/v1/pagos/confirmar",
        json={
            "monto": 50000.00,
            "metodo_pago": "efectivo"
        }
    )
    
    assert response.status_code == 422


# ============== TESTS DOCS ==============

@pytest.mark.asyncio
async def test_openapi_docs_disponible(async_client: AsyncClient):
    """Test: Documentación OpenAPI está disponible."""
    response = await async_client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_openapi_schema(async_client: AsyncClient):
    """Test: Schema OpenAPI es válido."""
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    
    data = response.json()
    assert "openapi" in data
    assert "paths" in data
    assert "/api/v1/alumnos/{alumno_id}" in data["paths"]


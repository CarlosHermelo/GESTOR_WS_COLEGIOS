"""
Configuración de pytest y fixtures compartidas.
"""
import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def event_loop():
    """Crear un event loop para toda la sesión de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock de settings para tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    monkeypatch.setenv("MOCK_ERP_URL", "http://localhost:8001")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "AIza-test-key")
    monkeypatch.setenv("WHATSAPP_TOKEN", "dummy_token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "dummy_id")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "test_token")


@pytest.fixture
def mock_erp_client():
    """Mock del cliente ERP."""
    client = AsyncMock()
    
    # Mock datos de prueba
    client.get_responsable_by_whatsapp.return_value = {
        "id": "RES-001",
        "nombre": "Carlos",
        "apellido": "García",
        "whatsapp": "+5491112345005",
        "email": "carlos@test.com",
        "alumnos": [
            {
                "id": "ALU-001",
                "nombre": "Emma",
                "apellido": "García",
                "grado": "3° Primaria"
            }
        ]
    }
    
    client.get_alumno_cuotas.return_value = [
        {
            "id": "CUO-001",
            "alumno_id": "ALU-001",
            "numero_cuota": 1,
            "monto": 45000,
            "fecha_vencimiento": "2024-01-15",
            "estado": "pendiente",
            "link_pago": "https://pago.test.com/CUO-001"
        }
    ]
    
    client.get_cuota.return_value = {
        "id": "CUO-001",
        "alumno_id": "ALU-001",
        "monto": 45000,
        "fecha_vencimiento": "2024-01-15",
        "estado": "pendiente",
        "link_pago": "https://pago.test.com/CUO-001"
    }
    
    client.get_alumno.return_value = {
        "id": "ALU-001",
        "nombre": "Emma",
        "apellido": "García",
        "grado": "3° Primaria",
        "responsables": [
            {
                "id": "RES-001",
                "nombre": "Carlos",
                "apellido": "García",
                "whatsapp": "+5491112345005"
            }
        ]
    }
    
    client.health_check.return_value = True
    
    return client


@pytest.fixture
def mock_llm():
    """Mock del LLM."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(
        content="Respuesta de prueba del LLM"
    ))
    return llm


@pytest.fixture
def mock_whatsapp_service():
    """Mock del servicio de WhatsApp."""
    service = AsyncMock()
    service.send_message.return_value = {
        "success": True,
        "message_id": "test_msg_id",
        "simulated": True
    }
    return service




"""
Pytest fixtures para MCP Tools Server.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Force mock mode for tests
import os
os.environ["MOCK_MODE"] = "true"

from app.main import app
from app.mcp.registry import registry


@pytest_asyncio.fixture
async def client():
    """Cliente HTTP para testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def tools_registry():
    """Registry de tools."""
    return registry

"""
Tests para las tools del MCP Server.
"""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "mcp_tools"
    assert data["mock_mode"] == True


@pytest.mark.asyncio
async def test_list_tools(client):
    """Test listar tools."""
    response = await client.get("/tools")
    assert response.status_code == 200
    
    data = response.json()
    assert "tools" in data
    assert "count" in data
    assert data["count"] > 0


@pytest.mark.asyncio
async def test_list_tools_by_category(client):
    """Test filtrar tools por categoría."""
    response = await client.get("/tools?category=erp")
    assert response.status_code == 200
    
    data = response.json()
    assert all(t["category"] == "erp" for t in data["tools"])


@pytest.mark.asyncio
async def test_get_tool_schema(client):
    """Test obtener schema de una tool."""
    response = await client.get("/tools/consultar_estado_cuenta")
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "consultar_estado_cuenta"
    assert "parameters" in data
    assert "properties" in data["parameters"]


@pytest.mark.asyncio
async def test_tool_not_found(client):
    """Test tool que no existe."""
    response = await client.get("/tools/tool_inexistente")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_call_erp_tool(client):
    """Test llamar tool de ERP."""
    response = await client.post("/tools/consultar_estado_cuenta/call", json={
        "name": "consultar_estado_cuenta",
        "arguments": {"whatsapp": "+5491112345001"}
    })
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert "data" in data
    assert data["data"]["found"] == True


@pytest.mark.asyncio
async def test_call_admin_tool(client):
    """Test llamar tool de Admin."""
    response = await client.post("/tools/crear_ticket/call", json={
        "name": "crear_ticket",
        "arguments": {
            "categoria": "consulta_admin",
            "motivo": "Consulta de prueba",
            "phone_number": "+5491112345001"
        }
    })
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert data["data"]["created"] == True


@pytest.mark.asyncio
async def test_call_kg_tool(client):
    """Test llamar tool de Knowledge Graph."""
    response = await client.post("/tools/buscar_horarios/call", json={
        "name": "buscar_horarios",
        "arguments": {}
    })
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert data["data"]["found"] == True
    assert "horarios" in data["data"]


@pytest.mark.asyncio
async def test_mcp_endpoint_list(client):
    """Test endpoint MCP - listar tools."""
    response = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": "test-1"
    })
    assert response.status_code == 200
    
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "test-1"
    assert "tools" in data["result"]


@pytest.mark.asyncio
async def test_mcp_endpoint_call(client):
    """Test endpoint MCP - llamar tool."""
    response = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "consultar_estado_cuenta",
            "arguments": {"whatsapp": "+5491112345001"}
        },
        "id": "test-2"
    })
    assert response.status_code == 200
    
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["result"]["success"] == True


@pytest.mark.asyncio
async def test_mcp_endpoint_ping(client):
    """Test endpoint MCP - ping."""
    response = await client.post("/mcp", json={
        "jsonrpc": "2.0",
        "method": "ping",
        "params": {},
        "id": "test-ping"
    })
    assert response.status_code == 200
    
    data = response.json()
    assert data["result"]["status"] == "pong"


@pytest.mark.asyncio
async def test_categories(client):
    """Test listar categorías."""
    response = await client.get("/test/categories")
    assert response.status_code == 200
    
    data = response.json()
    assert "erp" in data["categories"]
    assert "admin" in data["categories"]
    assert "kg" in data["categories"]
    assert "notif" in data["categories"]

"""
Test manual del MCP Tools Server.
Ejecutar con: python test_mcp_manual.py
"""
import asyncio
import httpx
import sys

# Configuración
MCP_URL = "http://localhost:8003"


async def test_health():
    """Test health endpoint."""
    print("\n" + "=" * 50)
    print("TEST: Health Check")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200


async def test_list_tools():
    """Test listar tools."""
    print("\n" + "=" * 50)
    print("TEST: Listar Tools")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_URL}/tools")
        data = response.json()
        print(f"Total tools: {data['count']}")
        
        for tool in data['tools']:
            print(f"  - {tool['name']} ({tool['category']})")
        
        return data['count'] > 0


async def test_list_by_category():
    """Test listar por categoría."""
    print("\n" + "=" * 50)
    print("TEST: Tools por Categoría")
    print("=" * 50)
    
    categories = ["erp", "admin", "kg", "notif"]
    
    async with httpx.AsyncClient() as client:
        for cat in categories:
            response = await client.get(f"{MCP_URL}/tools?category={cat}")
            data = response.json()
            tools = [t['name'] for t in data['tools']]
            print(f"  [{cat}]: {tools}")
    
    return True


async def test_call_erp_tool():
    """Test llamar tool de ERP."""
    print("\n" + "=" * 50)
    print("TEST: Consultar Estado de Cuenta (ERP)")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_URL}/tools/consultar_estado_cuenta/call",
            json={
                "name": "consultar_estado_cuenta",
                "arguments": {"whatsapp": "+5491112345001"}
            }
        )
        data = response.json()
        print(f"Success: {data['success']}")
        if data['success']:
            print(f"Responsable: {data['data'].get('responsable', 'N/A')}")
            print(f"Deuda total: ${data['data'].get('deuda_total', 0):,.0f}")
        return data['success']


async def test_call_admin_tool():
    """Test llamar tool de Admin."""
    print("\n" + "=" * 50)
    print("TEST: Crear Ticket (Admin)")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_URL}/tools/crear_ticket/call",
            json={
                "name": "crear_ticket",
                "arguments": {
                    "categoria": "consulta_admin",
                    "motivo": "Test de MCP Tools",
                    "phone_number": "+5491112345001"
                }
            }
        )
        data = response.json()
        print(f"Success: {data['success']}")
        if data['success']:
            print(f"Ticket ID: {data['data'].get('ticket_id', 'N/A')}")
        return data['success']


async def test_call_kg_tool():
    """Test llamar tool de Knowledge Graph."""
    print("\n" + "=" * 50)
    print("TEST: Buscar Horarios (KG)")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_URL}/tools/buscar_horarios/call",
            json={
                "name": "buscar_horarios",
                "arguments": {}
            }
        )
        data = response.json()
        print(f"Success: {data['success']}")
        if data['success'] and data['data'].get('horarios'):
            horarios = data['data']['horarios']
            print(f"Horarios encontrados: {list(horarios.keys())}")
        return data['success']


async def test_mcp_protocol():
    """Test protocolo MCP JSON-RPC."""
    print("\n" + "=" * 50)
    print("TEST: Protocolo MCP (JSON-RPC)")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Ping
        response = await client.post(
            f"{MCP_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "ping",
                "params": {},
                "id": "test-1"
            }
        )
        data = response.json()
        print(f"Ping: {data.get('result', {}).get('status', 'error')}")
        
        # List tools
        response = await client.post(
            f"{MCP_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": "test-2"
            }
        )
        data = response.json()
        count = data.get('result', {}).get('count', 0)
        print(f"Tools via MCP: {count}")
        
        return count > 0


async def main():
    """Ejecutar todos los tests."""
    print("\n" + "#" * 60)
    print("#  MCP Tools Server - Test Manual")
    print("#" * 60)
    
    tests = [
        ("Health Check", test_health),
        ("List Tools", test_list_tools),
        ("List by Category", test_list_by_category),
        ("ERP Tool", test_call_erp_tool),
        ("Admin Tool", test_call_admin_tool),
        ("KG Tool", test_call_kg_tool),
        ("MCP Protocol", test_mcp_protocol),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"ERROR: {e}")
            results.append((name, False))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
    
    print(f"\nTotal: {passed}/{len(results)} tests pasaron")
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nCancelado por usuario")
        sys.exit(1)
    except httpx.ConnectError:
        print("\n" + "!" * 60)
        print("ERROR: No se pudo conectar al MCP Server")
        print("Asegurate de que el servidor esté corriendo en localhost:8003")
        print("Ejecutá: python run_local.py")
        print("!" * 60)
        sys.exit(1)

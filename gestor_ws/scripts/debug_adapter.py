import asyncio
import logging
import sys
import os

# Agregar directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.adapters.mock_erp_adapter import MockERPAdapter

# Configurar logging
logging.basicConfig(level=logging.INFO)

async def test_adapter():
    print("🧪 Probando MockERPAdapter...")
    
    # Forzar URL local
    adapter = MockERPAdapter(base_url="http://localhost:8001")
    whatsapp = "+5491199999999"
    
    try:
        print(f"🔍 Buscando {whatsapp}...")
        data = await adapter.get_responsable_by_whatsapp(whatsapp)
        print(f"✅ Resultado: {data}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(test_adapter())

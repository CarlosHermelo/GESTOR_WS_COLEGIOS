"""
Script para ejecutar el MCP Tools Server localmente.
"""
import os
import sys

# Configurar entorno para modo mock
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("LOG_LEVEL", "INFO")

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("MCP Tools Server - Modo Local")
    print("=" * 60)
    print(f"MOCK_MODE: {os.environ.get('MOCK_MODE')}")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    )

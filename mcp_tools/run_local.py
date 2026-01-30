"""
Script para ejecutar el MCP Tools Server localmente.
"""
import os
import sys

from app.config import settings

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("MCP Tools Server - Modo Local")
    print("=" * 60)
    print(f"MOCK_MODE: {settings.MOCK_MODE}")
    print(f"LOG_LEVEL: {settings.LOG_LEVEL}")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    )

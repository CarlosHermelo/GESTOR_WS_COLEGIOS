"""
Script para resetear la base de datos.
Elimina todos los datos de las tablas manteniendo la estructura.

Uso:
    docker-compose exec api python scripts/reset.py
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import get_db_context, engine
from app.models import Base


async def reset_database(drop_tables: bool = False):
    """
    Resetea la base de datos.
    
    Args:
        drop_tables: Si True, elimina las tablas completamente.
                    Si False, solo trunca los datos.
    """
    print("\n" + "="*60)
    print("🗑️  RESET - ERP Mock Database")
    print("="*60)
    
    async with get_db_context() as db:
        if drop_tables:
            print("\n⚠️  Modo: DROP TABLES (eliminando estructura)")
            
            # Orden inverso de dependencias
            tables = [
                "erp_pagos",
                "erp_cuotas",
                "erp_planes_pago",
                "erp_responsabilidad",
                "erp_alumnos",
                "erp_responsables"
            ]
            
            for table in tables:
                try:
                    await db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    print(f"   ✅ Eliminada tabla: {table}")
                except Exception as e:
                    print(f"   ⚠️  Error eliminando {table}: {e}")
            
            await db.commit()
            
            # Recrear tablas
            print("\n📝 Recreando estructura de tablas...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("   ✅ Tablas recreadas")
            
        else:
            print("\n⚠️  Modo: TRUNCATE (conservando estructura)")
            
            # Orden de truncado respetando foreign keys
            tables = [
                "erp_pagos",
                "erp_cuotas",
                "erp_planes_pago",
                "erp_responsabilidad",
                "erp_alumnos",
                "erp_responsables"
            ]
            
            for table in tables:
                try:
                    await db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                    print(f"   ✅ Truncada tabla: {table}")
                except Exception as e:
                    print(f"   ⚠️  Error truncando {table}: {e}")
            
            await db.commit()
    
    print("\n" + "="*60)
    print("✅ RESET COMPLETADO")
    print("="*60)
    print("\n💡 Para volver a poblar la BD ejecuta:")
    print("   docker-compose exec api python scripts/seed.py")
    print("")


async def confirm_and_reset():
    """Solicita confirmación antes de resetear."""
    print("\n⚠️  ¡ATENCIÓN!")
    print("Esta acción eliminará TODOS los datos de la base de datos.")
    
    # En modo no interactivo, proceder directamente
    if not sys.stdin.isatty():
        print("Modo no interactivo detectado, procediendo...")
        await reset_database(drop_tables=False)
        return
    
    respuesta = input("\n¿Desea continuar? (s/N): ").strip().lower()
    
    if respuesta in ("s", "si", "sí", "yes", "y"):
        drop = input("¿Eliminar también la estructura de tablas? (s/N): ").strip().lower()
        await reset_database(drop_tables=(drop in ("s", "si", "sí", "yes", "y")))
    else:
        print("\n❌ Operación cancelada")


if __name__ == "__main__":
    # Si se pasa --force como argumento, no pedir confirmación
    if "--force" in sys.argv:
        asyncio.run(reset_database(drop_tables=("--drop" in sys.argv)))
    else:
        asyncio.run(confirm_and_reset())


import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import sys

# Agregar el directorio raíz al path para poder importar la app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.cache import CacheResponsable, CacheAlumno, CacheCuota

async def verify():
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://gestor_user:gestor_pass@localhost:5432/gestor_ws")
    print(f"Verificando datos en {url}...")
    engine = create_async_engine(url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Contar registros
        resp_count = await session.scalar(select(func.count()).select_from(CacheResponsable))
        alumni_count = await session.scalar(select(func.count()).select_from(CacheAlumno))
        cuota_count = await session.scalar(select(func.count()).select_from(CacheCuota))
        
        print(f"📊 Resumen de BD:")
        print(f" - Responsables: {resp_count}")
        print(f" - Alumnos: {alumni_count}")
        print(f" - Cuotas: {cuota_count}")
        
        # Mostrar responsables
        print("\n👪 Responsables:")
        result = await session.execute(select(CacheResponsable))
        for r in result.scalars():
            print(f"   - {r.nombre} {r.apellido} ({r.whatsapp})")
            
        # Mostrar alumnos
        print("\n🎓 Alumnos:")
        result = await session.execute(select(CacheAlumno))
        for a in result.scalars():
            print(f"   - {a.nombre} {a.apellido} (Grado: {a.grado}, Responsable ID: {a.erp_responsable_id})")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify())

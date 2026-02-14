import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    url = "postgresql+asyncpg://gestor_user:gestor_pass@localhost:5432/gestor_ws"
    print(f"Probando conexión a {url}...")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"✅ Conexión exitosa! Resultado: {result.scalar()}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())

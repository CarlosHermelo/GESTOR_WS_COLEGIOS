"""
Configuración de conexión a PostgreSQL usando SQLAlchemy async.
Incluye manejo de sesiones y creación de tablas.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models import Base

# Configurar logging
logger = logging.getLogger(__name__)

# Crear engine async para PostgreSQL
# Usar NullPool para mejor manejo en entornos containerizados
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Cambiar a True para debug SQL
    poolclass=NullPool,  # Recomendado para async
    future=True
)

# Crear session maker async
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def init_db() -> None:
    """
    Inicializa la base de datos creando todas las tablas.
    Se ejecuta al iniciar la aplicación.
    """
    logger.info("Inicializando base de datos...")
    async with engine.begin() as conn:
        # Crear todas las tablas si no existen
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Base de datos inicializada correctamente")


async def close_db() -> None:
    """
    Cierra las conexiones a la base de datos.
    Se ejecuta al detener la aplicación.
    """
    logger.info("Cerrando conexiones a base de datos...")
    await engine.dispose()
    logger.info("Conexiones cerradas")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency de FastAPI para obtener una sesión de BD.
    Maneja automáticamente commit/rollback y cierre.
    
    Uso:
        @app.get("/ejemplo")
        async def ejemplo(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager para usar fuera de FastAPI (ej: scripts).
    
    Uso:
        async with get_db_context() as db:
            resultado = await db.execute(query)
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """
    Verifica si la conexión a la BD está activa.
    Útil para health checks.
    """
    try:
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Error verificando conexión a BD: {e}")
        return False


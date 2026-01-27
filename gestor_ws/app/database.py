"""
Configuración de base de datos PostgreSQL con SQLAlchemy async.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import settings


logger = logging.getLogger(__name__)


# Motor de base de datos async
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency que proporciona una sesión de base de datos.
    Se usa con FastAPI Depends().
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


async def init_db() -> None:
    """
    Inicializa la base de datos.
    Crea todas las tablas definidas en los modelos.
    """
    logger.info("Inicializando base de datos...")
    
    async with engine.begin() as conn:
        # Importar modelos para que se registren en Base.metadata
        from app.models import cache, interacciones, tickets  # noqa
        
        # Crear tablas
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Base de datos inicializada correctamente")


async def close_db() -> None:
    """Cierra las conexiones de la base de datos."""
    logger.info("Cerrando conexiones de base de datos...")
    await engine.dispose()
    logger.info("Conexiones cerradas")


async def check_db_connection() -> bool:
    """Verifica la conexión a la base de datos."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Error de conexión a BD: {e}")
        return False


# SQL para crear las tablas manualmente si es necesario
CREATE_TABLES_SQL = """
-- CACHE del ERP (réplica parcial)
CREATE TABLE IF NOT EXISTS cache_responsables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_responsable_id VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(200),
    apellido VARCHAR(200),
    whatsapp VARCHAR(20) UNIQUE,
    email VARCHAR(200),
    ultima_sync TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cache_alumnos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_alumno_id VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(200),
    apellido VARCHAR(200),
    grado VARCHAR(100),
    erp_responsable_id VARCHAR(100),
    ultima_sync TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cache_cuotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_cuota_id VARCHAR(100) UNIQUE NOT NULL,
    erp_alumno_id VARCHAR(100),
    monto DECIMAL(10,2),
    fecha_vencimiento DATE,
    estado VARCHAR(50),
    link_pago TEXT,
    fecha_pago TIMESTAMP,
    ultima_sync TIMESTAMP DEFAULT NOW()
);

-- DATOS PROPIOS del Gestor WS
CREATE TABLE IF NOT EXISTS interacciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_from VARCHAR(20) NOT NULL,
    erp_alumno_id VARCHAR(100),
    erp_cuota_id VARCHAR(100),
    tipo VARCHAR(50),
    contenido TEXT,
    agente VARCHAR(20),
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_alumno_id VARCHAR(100) NOT NULL,
    erp_responsable_id VARCHAR(100),
    categoria VARCHAR(50),
    motivo TEXT,
    contexto JSONB,
    estado VARCHAR(20) DEFAULT 'pendiente',
    prioridad VARCHAR(20) DEFAULT 'media',
    respuesta_admin TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notificaciones_enviadas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_cuota_id VARCHAR(100) NOT NULL,
    whatsapp_to VARCHAR(20),
    tipo VARCHAR(50),
    fecha_envio TIMESTAMP DEFAULT NOW(),
    leido BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS sincronizaciones_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo VARCHAR(50),
    erp_id VARCHAR(100),
    accion VARCHAR(20),
    timestamp TIMESTAMP DEFAULT NOW(),
    payload JSONB
);
"""




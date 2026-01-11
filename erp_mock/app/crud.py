"""
Operaciones CRUD (Create, Read, Update, Delete) para el ERP Mock.
Todas las operaciones son async para mejor rendimiento.
"""
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
import uuid

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models import (
    Responsable, Alumno, Responsabilidad, 
    PlanPago, Cuota, Pago
)
from app.schemas import ConfirmarPagoRequest, EstadoCuota

logger = logging.getLogger(__name__)


# ============== ALUMNOS ==============

async def get_alumno_by_id(
    db: AsyncSession, 
    alumno_id: str,
    include_responsables: bool = False
) -> Optional[Alumno]:
    """
    Obtiene un alumno por su ID.
    
    Args:
        db: Sesión de base de datos
        alumno_id: ID del alumno
        include_responsables: Si incluir responsables en la respuesta
    
    Returns:
        Alumno o None si no existe
    """
    query = select(Alumno).where(Alumno.id == alumno_id)
    
    if include_responsables:
        query = query.options(selectinload(Alumno.responsables))
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_alumnos_activos(db: AsyncSession) -> List[Alumno]:
    """Obtiene todos los alumnos activos."""
    query = select(Alumno).where(Alumno.activo == True)
    result = await db.execute(query)
    return list(result.scalars().all())


# ============== RESPONSABLES ==============

async def get_responsable_by_whatsapp(
    db: AsyncSession, 
    whatsapp: str
) -> Optional[Responsable]:
    """
    Busca un responsable por su número de WhatsApp.
    Incluye los alumnos a su cargo.
    
    Args:
        db: Sesión de base de datos
        whatsapp: Número de WhatsApp (ej: +5491112345001)
    
    Returns:
        Responsable con alumnos o None si no existe
    """
    # Normalizar número (remover espacios, guiones)
    whatsapp_normalizado = whatsapp.replace(" ", "").replace("-", "")
    
    query = (
        select(Responsable)
        .where(Responsable.whatsapp == whatsapp_normalizado)
        .options(selectinload(Responsable.alumnos))
    )
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_responsable_by_id(
    db: AsyncSession, 
    responsable_id: str
) -> Optional[Responsable]:
    """Obtiene un responsable por su ID."""
    query = (
        select(Responsable)
        .where(Responsable.id == responsable_id)
        .options(selectinload(Responsable.alumnos))
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


# ============== CUOTAS ==============

async def get_cuota_by_id(
    db: AsyncSession, 
    cuota_id: str,
    include_alumno: bool = False,
    include_plan: bool = False
) -> Optional[Cuota]:
    """
    Obtiene una cuota por su ID.
    
    Args:
        db: Sesión de base de datos
        cuota_id: ID de la cuota
        include_alumno: Si incluir datos del alumno
        include_plan: Si incluir datos del plan de pago
    
    Returns:
        Cuota o None si no existe
    """
    query = select(Cuota).where(Cuota.id == cuota_id)
    
    if include_alumno:
        query = query.options(joinedload(Cuota.alumno))
    if include_plan:
        query = query.options(joinedload(Cuota.plan_pago))
    
    result = await db.execute(query)
    return result.unique().scalar_one_or_none()


async def get_cuotas_alumno(
    db: AsyncSession,
    alumno_id: str,
    estado: Optional[str] = None
) -> List[Cuota]:
    """
    Obtiene las cuotas de un alumno.
    
    Args:
        db: Sesión de base de datos
        alumno_id: ID del alumno
        estado: Filtrar por estado (pendiente, pagada, vencida)
    
    Returns:
        Lista de cuotas
    """
    query = select(Cuota).where(Cuota.alumno_id == alumno_id)
    
    if estado:
        query = query.where(Cuota.estado == estado)
    
    query = query.order_by(Cuota.numero_cuota)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_cuotas_filtradas(
    db: AsyncSession,
    estado: Optional[str] = None,
    vencimiento_desde: Optional[date] = None,
    vencimiento_hasta: Optional[date] = None,
    limit: int = 100
) -> List[Cuota]:
    """
    Obtiene cuotas con filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        estado: Filtrar por estado
        vencimiento_desde: Fecha de vencimiento mínima
        vencimiento_hasta: Fecha de vencimiento máxima
        limit: Máximo de resultados
    
    Returns:
        Lista de cuotas filtradas
    """
    query = select(Cuota)
    
    conditions = []
    if estado:
        conditions.append(Cuota.estado == estado)
    if vencimiento_desde:
        conditions.append(Cuota.fecha_vencimiento >= vencimiento_desde)
    if vencimiento_hasta:
        conditions.append(Cuota.fecha_vencimiento <= vencimiento_hasta)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(Cuota.fecha_vencimiento).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def actualizar_estado_cuota(
    db: AsyncSession,
    cuota_id: str,
    nuevo_estado: str,
    fecha_pago: Optional[datetime] = None
) -> Optional[Cuota]:
    """
    Actualiza el estado de una cuota.
    
    Args:
        db: Sesión de base de datos
        cuota_id: ID de la cuota
        nuevo_estado: Nuevo estado (pendiente, pagada, vencida)
        fecha_pago: Fecha de pago si aplica
    
    Returns:
        Cuota actualizada o None
    """
    cuota = await get_cuota_by_id(db, cuota_id)
    if not cuota:
        return None
    
    cuota.estado = nuevo_estado
    if fecha_pago:
        cuota.fecha_pago = fecha_pago
    
    await db.flush()
    return cuota


# ============== PAGOS ==============

async def crear_pago(
    db: AsyncSession,
    pago_data: ConfirmarPagoRequest
) -> tuple[Optional[Pago], Optional[Cuota]]:
    """
    Crea un nuevo pago y actualiza el estado de la cuota.
    
    Args:
        db: Sesión de base de datos
        pago_data: Datos del pago a crear
    
    Returns:
        Tupla (Pago creado, Cuota actualizada) o (None, None) si error
    """
    # Verificar que la cuota existe
    cuota = await get_cuota_by_id(db, pago_data.cuota_id, include_alumno=True)
    if not cuota:
        logger.warning(f"Cuota no encontrada: {pago_data.cuota_id}")
        return None, None
    
    # Verificar que la cuota no esté ya pagada
    if cuota.estado == EstadoCuota.PAGADA.value:
        logger.warning(f"Cuota ya pagada: {pago_data.cuota_id}")
        return None, cuota
    
    # Generar ID único para el pago
    pago_id = f"PAG-{uuid.uuid4().hex[:8].upper()}"
    fecha_pago = datetime.utcnow()
    
    # Crear el pago
    nuevo_pago = Pago(
        id=pago_id,
        cuota_id=pago_data.cuota_id,
        monto=pago_data.monto,
        fecha_pago=fecha_pago,
        metodo_pago=pago_data.metodo_pago,
        referencia=pago_data.referencia
    )
    
    db.add(nuevo_pago)
    
    # Actualizar estado de la cuota
    cuota.estado = EstadoCuota.PAGADA.value
    cuota.fecha_pago = fecha_pago
    
    await db.flush()
    
    logger.info(f"Pago creado: {pago_id} para cuota {pago_data.cuota_id}")
    
    return nuevo_pago, cuota


async def get_pagos_cuota(
    db: AsyncSession,
    cuota_id: str
) -> List[Pago]:
    """Obtiene todos los pagos de una cuota."""
    query = select(Pago).where(Pago.cuota_id == cuota_id)
    result = await db.execute(query)
    return list(result.scalars().all())


# ============== PLANES DE PAGO ==============

async def get_plan_pago_by_id(
    db: AsyncSession,
    plan_id: str
) -> Optional[PlanPago]:
    """Obtiene un plan de pago por su ID."""
    query = select(PlanPago).where(PlanPago.id == plan_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_planes_pago(db: AsyncSession) -> List[PlanPago]:
    """Obtiene todos los planes de pago."""
    query = select(PlanPago)
    result = await db.execute(query)
    return list(result.scalars().all())


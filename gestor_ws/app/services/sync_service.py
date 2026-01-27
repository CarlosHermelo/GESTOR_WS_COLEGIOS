"""
Servicio de sincronización con el ERP.
Mantiene el cache actualizado con datos del ERP.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.cache import CacheResponsable, CacheAlumno, CacheCuota
from app.models.interacciones import SincronizacionLog
from app.adapters.mock_erp_adapter import get_erp_client


logger = logging.getLogger(__name__)


class SyncService:
    """
    Servicio para sincronizar datos del ERP al cache local.
    """
    
    def __init__(self):
        """Inicializa el servicio."""
        self.erp = get_erp_client()
    
    async def sync_responsable(
        self,
        erp_responsable_id: str,
        data: dict,
        session: Optional[AsyncSession] = None
    ) -> CacheResponsable:
        """
        Sincroniza un responsable al cache.
        
        Args:
            erp_responsable_id: ID del responsable en ERP
            data: Datos del responsable
            session: Sesión de BD opcional
            
        Returns:
            CacheResponsable: Registro actualizado/creado
        """
        async def _sync(sess: AsyncSession):
            # Buscar existente
            result = await sess.execute(
                select(CacheResponsable).where(
                    CacheResponsable.erp_responsable_id == erp_responsable_id
                )
            )
            responsable = result.scalar_one_or_none()
            
            if responsable:
                # Actualizar
                responsable.nombre = data.get("nombre")
                responsable.apellido = data.get("apellido")
                responsable.whatsapp = data.get("whatsapp")
                responsable.email = data.get("email")
                responsable.ultima_sync = datetime.now()
                accion = "update"
            else:
                # Crear
                responsable = CacheResponsable(
                    erp_responsable_id=erp_responsable_id,
                    nombre=data.get("nombre"),
                    apellido=data.get("apellido"),
                    whatsapp=data.get("whatsapp"),
                    email=data.get("email")
                )
                sess.add(responsable)
                accion = "create"
            
            # Log de sincronización
            log = SincronizacionLog(
                tipo="responsable",
                erp_id=erp_responsable_id,
                accion=accion,
                payload=data
            )
            sess.add(log)
            
            await sess.commit()
            await sess.refresh(responsable)
            
            logger.info(f"Responsable {erp_responsable_id} sincronizado ({accion})")
            return responsable
        
        if session:
            return await _sync(session)
        else:
            async with async_session_maker() as sess:
                return await _sync(sess)
    
    async def sync_alumno(
        self,
        erp_alumno_id: str,
        data: dict,
        session: Optional[AsyncSession] = None
    ) -> CacheAlumno:
        """
        Sincroniza un alumno al cache.
        
        Args:
            erp_alumno_id: ID del alumno en ERP
            data: Datos del alumno
            session: Sesión de BD opcional
            
        Returns:
            CacheAlumno: Registro actualizado/creado
        """
        async def _sync(sess: AsyncSession):
            result = await sess.execute(
                select(CacheAlumno).where(
                    CacheAlumno.erp_alumno_id == erp_alumno_id
                )
            )
            alumno = result.scalar_one_or_none()
            
            if alumno:
                alumno.nombre = data.get("nombre")
                alumno.apellido = data.get("apellido")
                alumno.grado = data.get("grado")
                alumno.erp_responsable_id = data.get("responsable_id")
                alumno.ultima_sync = datetime.now()
                accion = "update"
            else:
                alumno = CacheAlumno(
                    erp_alumno_id=erp_alumno_id,
                    nombre=data.get("nombre"),
                    apellido=data.get("apellido"),
                    grado=data.get("grado"),
                    erp_responsable_id=data.get("responsable_id")
                )
                sess.add(alumno)
                accion = "create"
            
            log = SincronizacionLog(
                tipo="alumno",
                erp_id=erp_alumno_id,
                accion=accion,
                payload=data
            )
            sess.add(log)
            
            await sess.commit()
            await sess.refresh(alumno)
            
            logger.info(f"Alumno {erp_alumno_id} sincronizado ({accion})")
            return alumno
        
        if session:
            return await _sync(session)
        else:
            async with async_session_maker() as sess:
                return await _sync(sess)
    
    async def sync_cuota(
        self,
        erp_cuota_id: str,
        data: dict,
        session: Optional[AsyncSession] = None
    ) -> CacheCuota:
        """
        Sincroniza una cuota al cache.
        
        Args:
            erp_cuota_id: ID de la cuota en ERP
            data: Datos de la cuota
            session: Sesión de BD opcional
            
        Returns:
            CacheCuota: Registro actualizado/creado
        """
        async def _sync(sess: AsyncSession):
            result = await sess.execute(
                select(CacheCuota).where(
                    CacheCuota.erp_cuota_id == erp_cuota_id
                )
            )
            cuota = result.scalar_one_or_none()
            
            if cuota:
                cuota.erp_alumno_id = data.get("alumno_id")
                cuota.monto = data.get("monto")
                cuota.fecha_vencimiento = data.get("fecha_vencimiento")
                cuota.estado = data.get("estado")
                cuota.link_pago = data.get("link_pago")
                cuota.fecha_pago = data.get("fecha_pago")
                cuota.ultima_sync = datetime.now()
                accion = "update"
            else:
                cuota = CacheCuota(
                    erp_cuota_id=erp_cuota_id,
                    erp_alumno_id=data.get("alumno_id"),
                    monto=data.get("monto"),
                    fecha_vencimiento=data.get("fecha_vencimiento"),
                    estado=data.get("estado"),
                    link_pago=data.get("link_pago"),
                    fecha_pago=data.get("fecha_pago")
                )
                sess.add(cuota)
                accion = "create"
            
            log = SincronizacionLog(
                tipo="cuota",
                erp_id=erp_cuota_id,
                accion=accion,
                payload=data
            )
            sess.add(log)
            
            await sess.commit()
            await sess.refresh(cuota)
            
            logger.info(f"Cuota {erp_cuota_id} sincronizada ({accion})")
            return cuota
        
        if session:
            return await _sync(session)
        else:
            async with async_session_maker() as sess:
                return await _sync(sess)
    
    async def actualizar_estado_cuota(
        self,
        erp_cuota_id: str,
        estado: str
    ) -> Optional[CacheCuota]:
        """
        Actualiza el estado de una cuota en cache.
        
        Args:
            erp_cuota_id: ID de la cuota
            estado: Nuevo estado
            
        Returns:
            CacheCuota: Cuota actualizada o None
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(CacheCuota).where(
                    CacheCuota.erp_cuota_id == erp_cuota_id
                )
            )
            cuota = result.scalar_one_or_none()
            
            if cuota:
                cuota.estado = estado
                cuota.ultima_sync = datetime.now()
                if estado == "pagada":
                    cuota.fecha_pago = datetime.now()
                
                log = SincronizacionLog(
                    tipo="cuota",
                    erp_id=erp_cuota_id,
                    accion="update",
                    payload={"estado": estado}
                )
                session.add(log)
                
                await session.commit()
                await session.refresh(cuota)
                
                logger.info(f"Estado de cuota {erp_cuota_id} actualizado a {estado}")
                return cuota
            
            return None




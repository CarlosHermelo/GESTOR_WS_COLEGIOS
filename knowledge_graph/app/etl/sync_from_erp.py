"""
ETL desde Cache de Gestor WS hacia Neo4j.
Lee los datos cacheados del ERP y los sincroniza al Knowledge Graph.
"""
import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.neo4j_client import Neo4jClient
from app.config import settings

logger = logging.getLogger(__name__)


class ETLFromERP:
    """Sincroniza datos desde cache de Gestor WS hacia Neo4j."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j = neo4j_client
        self.engine = create_async_engine(settings.DATABASE_URL)
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def _query_cache(self, query: str) -> list[dict]:
        """Ejecuta query en la BD de cache de Gestor WS."""
        async with self.async_session() as session:
            result = await session.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
    
    async def sync_all(self) -> dict[str, int]:
        """
        Sincroniza todo desde cache.
        
        Returns:
            Diccionario con conteos de elementos sincronizados
        """
        logger.info("🔄 Iniciando ETL desde Cache de Gestor WS...")
        
        counts = {
            "responsables": 0,
            "estudiantes": 0,
            "cuotas": 0,
            "pagos": 0,
            "grados": 0
        }
        
        # 1. Sincronizar responsables
        counts["responsables"] = await self.sync_responsables()
        
        # 2. Sincronizar estudiantes (con relaciones)
        result = await self.sync_estudiantes()
        counts["estudiantes"] = result["estudiantes"]
        counts["grados"] = result["grados"]
        
        # 3. Sincronizar cuotas
        counts["cuotas"] = await self.sync_cuotas()
        
        # 4. Sincronizar pagos (desde cuotas pagadas)
        counts["pagos"] = await self.sync_pagos()
        
        logger.info(f"✅ ETL desde Cache completado: {counts}")
        return counts
    
    async def sync_responsables(self) -> int:
        """
        Sincroniza responsables desde cache → Neo4j.
        
        Returns:
            Número de responsables sincronizados
        """
        logger.info("   📥 Sincronizando responsables...")
        
        responsables = await self._query_cache("""
            SELECT erp_responsable_id, nombre, apellido, whatsapp, email 
            FROM cache_responsables
        """)
        count = 0
        
        for resp in responsables:
            try:
                await self.neo4j.execute_write("""
                    MERGE (r:Responsable {erp_id: $erp_id})
                    SET r.nombre = $nombre,
                        r.apellido = $apellido,
                        r.whatsapp = $whatsapp,
                        r.email = $email,
                        r.ultima_sync = datetime()
                """, {
                    "erp_id": resp.get("erp_responsable_id"),
                    "nombre": resp.get("nombre"),
                    "apellido": resp.get("apellido"),
                    "whatsapp": resp.get("whatsapp"),
                    "email": resp.get("email")
                })
                count += 1
            except Exception as e:
                logger.error(f"Error sincronizando responsable {resp.get('erp_responsable_id')}: {e}")
        
        logger.info(f"   ✅ {count} responsables sincronizados")
        return count
    
    async def sync_estudiantes(self) -> dict[str, int]:
        """
        Sincroniza estudiantes y crea relaciones:
        - RESPONSABLE_DE (Responsable -> Estudiante)
        - CURSA (Estudiante -> Grado)
        
        Returns:
            Diccionario con conteos
        """
        logger.info("   📥 Sincronizando estudiantes...")
        
        alumnos = await self._query_cache("""
            SELECT erp_alumno_id, nombre, apellido, grado, erp_responsable_id 
            FROM cache_alumnos
        """)
        estudiantes_count = 0
        grados = set()
        
        for alumno in alumnos:
            try:
                grado = alumno.get("grado") or "Sin grado"
                grados.add(grado)
                
                # Crear/actualizar estudiante y grado
                await self.neo4j.execute_write("""
                    MERGE (e:Estudiante {erp_id: $erp_id})
                    SET e.nombre = $nombre,
                        e.apellido = $apellido,
                        e.grado = $grado,
                        e.ultima_sync = datetime()
                    
                    WITH e
                    MERGE (g:Grado {nombre: $grado})
                    MERGE (e)-[:CURSA]->(g)
                """, {
                    "erp_id": alumno.get("erp_alumno_id"),
                    "nombre": alumno.get("nombre"),
                    "apellido": alumno.get("apellido"),
                    "grado": grado
                })
                
                # Crear relación con responsable si existe
                resp_id = alumno.get("erp_responsable_id")
                if resp_id:
                    await self.neo4j.execute_write("""
                        MATCH (r:Responsable {erp_id: $responsable_id})
                        MATCH (e:Estudiante {erp_id: $estudiante_id})
                        MERGE (r)-[:RESPONSABLE_DE]->(e)
                    """, {
                        "responsable_id": resp_id,
                        "estudiante_id": alumno.get("erp_alumno_id")
                    })
                
                estudiantes_count += 1
            except Exception as e:
                logger.error(f"Error sincronizando alumno {alumno.get('erp_alumno_id')}: {e}")
        
        logger.info(f"   ✅ {estudiantes_count} estudiantes, {len(grados)} grados")
        return {"estudiantes": estudiantes_count, "grados": len(grados)}
    
    async def sync_cuotas(self) -> int:
        """
        Sincroniza cuotas y crea relación DEBE (Estudiante -> Cuota).
        
        Returns:
            Número de cuotas sincronizadas
        """
        logger.info("   📥 Sincronizando cuotas...")
        
        cuotas = await self._query_cache("""
            SELECT erp_cuota_id, erp_alumno_id, monto, fecha_vencimiento, 
                   estado, fecha_pago, link_pago
            FROM cache_cuotas
        """)
        count = 0
        
        for cuota in cuotas:
            try:
                fecha_venc = cuota.get("fecha_vencimiento")
                if hasattr(fecha_venc, 'isoformat'):
                    fecha_venc = fecha_venc.isoformat()
                else:
                    fecha_venc = str(fecha_venc)[:10] if fecha_venc else None
                
                if not fecha_venc:
                    continue
                
                await self.neo4j.execute_write("""
                    MERGE (c:Cuota {erp_id: $erp_id})
                    SET c.monto = $monto,
                        c.fecha_vencimiento = date($fecha_vencimiento),
                        c.estado = $estado,
                        c.link_pago = $link_pago,
                        c.ultima_sync = datetime()
                    
                    WITH c
                    MATCH (e:Estudiante {erp_id: $alumno_id})
                    MERGE (e)-[:DEBE]->(c)
                """, {
                    "erp_id": cuota.get("erp_cuota_id"),
                    "monto": float(cuota.get("monto") or 0),
                    "fecha_vencimiento": fecha_venc,
                    "estado": cuota.get("estado") or "pendiente",
                    "link_pago": cuota.get("link_pago"),
                    "alumno_id": cuota.get("erp_alumno_id")
                })
                count += 1
            except Exception as e:
                logger.error(f"Error sincronizando cuota {cuota.get('erp_cuota_id')}: {e}")
        
        logger.info(f"   ✅ {count} cuotas sincronizadas")
        return count
    
    async def sync_pagos(self) -> int:
        """
        Crea relaciones de PAGO para cuotas pagadas.
        
        Returns:
            Número de pagos sincronizados
        """
        logger.info("   📥 Sincronizando pagos...")
        
        # Obtener cuotas pagadas con información del responsable
        pagos = await self._query_cache("""
            SELECT c.erp_cuota_id, c.erp_alumno_id, c.monto, 
                   c.fecha_vencimiento, c.fecha_pago, c.estado,
                   a.erp_responsable_id
            FROM cache_cuotas c
            JOIN cache_alumnos a ON c.erp_alumno_id = a.erp_alumno_id
            WHERE c.estado = 'pagada' AND c.fecha_pago IS NOT NULL
        """)
        count = 0
        
        for pago in pagos:
            try:
                fecha_pago = pago.get("fecha_pago")
                fecha_venc = pago.get("fecha_vencimiento")
                
                # Calcular días de demora
                dias_demora = 0
                if fecha_pago and fecha_venc:
                    try:
                        if hasattr(fecha_pago, 'date'):
                            fp = fecha_pago.date() if hasattr(fecha_pago, 'date') else fecha_pago
                        else:
                            fp = datetime.fromisoformat(str(fecha_pago)[:19]).date()
                        
                        if hasattr(fecha_venc, 'isoformat'):
                            fv = fecha_venc
                        else:
                            fv = datetime.fromisoformat(str(fecha_venc)).date()
                        
                        dias_demora = max(0, (fp - fv).days)
                    except Exception:
                        pass
                
                resp_id = pago.get("erp_responsable_id")
                if not resp_id:
                    continue
                
                fecha_pago_str = str(fecha_pago)[:19] if fecha_pago else None
                if not fecha_pago_str:
                    continue
                
                await self.neo4j.execute_write("""
                    MATCH (r:Responsable {erp_id: $responsable_id})
                    MATCH (c:Cuota {erp_id: $cuota_id})
                    MERGE (r)-[p:PAGO]->(c)
                    SET p.fecha = datetime($fecha_pago),
                        p.monto = $monto,
                        p.dias_demora = $dias_demora
                """, {
                    "responsable_id": resp_id,
                    "cuota_id": pago.get("erp_cuota_id"),
                    "fecha_pago": fecha_pago_str,
                    "monto": float(pago.get("monto") or 0),
                    "dias_demora": dias_demora
                })
                count += 1
                
            except Exception as e:
                logger.error(f"Error sincronizando pago de cuota {pago.get('erp_cuota_id')}: {e}")
        
        logger.info(f"   ✅ {count} pagos sincronizados")
        return count

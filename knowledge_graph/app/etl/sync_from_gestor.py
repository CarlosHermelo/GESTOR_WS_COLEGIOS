"""
ETL desde Gestor WS hacia Neo4j.
Sincroniza interacciones, tickets y notificaciones.
"""
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.neo4j_client import Neo4jClient
from app.config import settings

logger = logging.getLogger(__name__)


class ETLFromGestor:
    """Sincroniza datos desde Gestor WS hacia Neo4j."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j = neo4j_client
        self.engine = create_async_engine(settings.DATABASE_URL)
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def _query_gestor_db(self, query: str) -> list[dict]:
        """Ejecuta query en la BD de Gestor WS."""
        async with self.async_session() as session:
            result = await session.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
    
    async def sync_all(self) -> dict[str, int]:
        """
        Sincroniza todo desde Gestor WS.
        
        Returns:
            Diccionario con conteos
        """
        logger.info("🔄 Iniciando ETL desde Gestor WS...")
        
        counts = {
            "interacciones": 0,
            "notif_ignoradas": 0,
            "tickets": 0
        }
        
        counts["interacciones"] = await self.sync_interacciones()
        counts["notif_ignoradas"] = await self.detectar_notificaciones_ignoradas()
        counts["tickets"] = await self.sync_tickets()
        
        logger.info(f"✅ ETL desde Gestor WS completado: {counts}")
        return counts
    
    async def sync_interacciones(self, dias: int = 30) -> int:
        """
        Sincroniza interacciones de WhatsApp.
        Crea relación INTERACTUO (Responsable -> Cuota).
        
        Args:
            dias: Días hacia atrás a sincronizar
            
        Returns:
            Número de interacciones sincronizadas
        """
        logger.info("   📥 Sincronizando interacciones...")
        
        # Query para obtener interacciones con responsable asociado
        interacciones = await self._query_gestor_db(f"""
            SELECT 
                i.id,
                i.whatsapp_from,
                i.erp_cuota_id,
                i.tipo,
                i.agente,
                i.contenido,
                i.timestamp,
                cr.erp_responsable_id
            FROM interacciones i
            LEFT JOIN cache_responsables cr ON i.whatsapp_from = cr.whatsapp
            WHERE i.timestamp > NOW() - INTERVAL '{dias} days'
              AND i.erp_cuota_id IS NOT NULL
              AND cr.erp_responsable_id IS NOT NULL
        """)
        
        count = 0
        for inter in interacciones:
            try:
                await self.neo4j.execute_write("""
                    MATCH (r:Responsable {erp_id: $responsable_id})
                    MATCH (c:Cuota {erp_id: $cuota_id})
                    MERGE (r)-[i:INTERACTUO {id: $id}]->(c)
                    SET i.timestamp = datetime($timestamp),
                        i.tipo = $tipo,
                        i.agente = $agente,
                        i.contenido_preview = $contenido
                """, {
                    "id": str(inter["id"]),
                    "responsable_id": inter["erp_responsable_id"],
                    "cuota_id": inter["erp_cuota_id"],
                    "timestamp": inter["timestamp"].isoformat() if inter["timestamp"] else None,
                    "tipo": inter["tipo"],
                    "agente": inter["agente"],
                    "contenido": inter["contenido"][:100] if inter["contenido"] else None
                })
                count += 1
            except Exception as e:
                logger.error(f"Error sincronizando interacción {inter['id']}: {e}")
        
        logger.info(f"   ✅ {count} interacciones sincronizadas")
        return count
    
    async def detectar_notificaciones_ignoradas(self, horas: int = 48) -> int:
        """
        Detecta responsables que no respondieron a notificaciones.
        Crea relación IGNORO_NOTIFICACION (Responsable -> Cuota).
        
        Args:
            horas: Horas después de las cuales se considera ignorada
            
        Returns:
            Número de notificaciones ignoradas detectadas
        """
        logger.info("   📥 Detectando notificaciones ignoradas...")
        
        ignoradas = await self._query_gestor_db(f"""
            SELECT 
                n.id,
                n.erp_cuota_id,
                n.whatsapp_to,
                n.tipo,
                n.fecha_envio,
                cr.erp_responsable_id
            FROM notificaciones_enviadas n
            LEFT JOIN cache_responsables cr ON n.whatsapp_to = cr.whatsapp
            WHERE n.leido = FALSE
              AND n.fecha_envio < NOW() - INTERVAL '{horas} hours'
              AND cr.erp_responsable_id IS NOT NULL
        """)
        
        count = 0
        for ign in ignoradas:
            try:
                await self.neo4j.execute_write("""
                    MATCH (r:Responsable {erp_id: $responsable_id})
                    MATCH (c:Cuota {erp_id: $cuota_id})
                    MERGE (r)-[ig:IGNORO_NOTIFICACION {id: $id}]->(c)
                    SET ig.fecha = datetime($fecha),
                        ig.tipo_notif = $tipo
                """, {
                    "id": str(ign["id"]),
                    "responsable_id": ign["erp_responsable_id"],
                    "cuota_id": ign["erp_cuota_id"],
                    "fecha": ign["fecha_envio"].isoformat() if ign["fecha_envio"] else None,
                    "tipo": ign["tipo"]
                })
                count += 1
            except Exception as e:
                logger.error(f"Error sincronizando notificación ignorada {ign['id']}: {e}")
        
        logger.info(f"   ✅ {count} notificaciones ignoradas detectadas")
        return count
    
    async def sync_tickets(self) -> int:
        """
        Sincroniza tickets para análisis de patrones.
        
        Returns:
            Número de tickets sincronizados
        """
        logger.info("   📥 Sincronizando tickets...")
        
        tickets = await self._query_gestor_db("""
            SELECT 
                t.id,
                t.erp_alumno_id,
                t.erp_responsable_id,
                t.categoria,
                t.prioridad,
                t.estado,
                t.created_at,
                t.resolved_at
            FROM tickets t
            WHERE t.erp_responsable_id IS NOT NULL
        """)
        
        count = 0
        for ticket in tickets:
            try:
                # Crear nodo de ticket y conectar con responsable
                await self.neo4j.execute_write("""
                    MERGE (t:Ticket {id: $id})
                    SET t.categoria = $categoria,
                        t.prioridad = $prioridad,
                        t.estado = $estado,
                        t.created_at = datetime($created_at),
                        t.resolved_at = CASE 
                            WHEN $resolved_at IS NOT NULL 
                            THEN datetime($resolved_at) 
                            ELSE null 
                        END
                    
                    WITH t
                    MATCH (r:Responsable {erp_id: $responsable_id})
                    MERGE (r)-[:CREO_TICKET]->(t)
                """, {
                    "id": str(ticket["id"]),
                    "categoria": ticket["categoria"],
                    "prioridad": ticket["prioridad"],
                    "estado": ticket["estado"],
                    "created_at": ticket["created_at"].isoformat() if ticket["created_at"] else None,
                    "resolved_at": ticket["resolved_at"].isoformat() if ticket["resolved_at"] else None,
                    "responsable_id": ticket["erp_responsable_id"]
                })
                count += 1
            except Exception as e:
                logger.error(f"Error sincronizando ticket {ticket['id']}: {e}")
        
        logger.info(f"   ✅ {count} tickets sincronizados")
        return count


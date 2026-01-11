"""
Cliente Neo4j asíncrono para el Knowledge Graph.
"""
import logging
from typing import Any, Optional
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Cliente asíncrono para Neo4j."""
    
    _driver: Optional[AsyncDriver] = None
    _instance: Optional["Neo4jClient"] = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self) -> None:
        """Conecta al servidor Neo4j."""
        if self._driver is not None:
            return
        
        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            
            # Verificar conexión
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.consume()
            
            logger.info(f"✅ Conectado a Neo4j: {settings.NEO4J_URI}")
            
        except AuthError as e:
            logger.error(f"❌ Error de autenticación Neo4j: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"❌ Neo4j no disponible: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error conectando a Neo4j: {e}")
            raise
    
    async def close(self) -> None:
        """Cierra la conexión a Neo4j."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("🔌 Desconectado de Neo4j")
    
    @asynccontextmanager
    async def session(self):
        """Context manager para obtener una sesión."""
        if self._driver is None:
            await self.connect()
        
        session = self._driver.session()
        try:
            yield session
        finally:
            await session.close()
    
    async def execute(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta una query Cypher y retorna los resultados.
        
        Args:
            query: Query Cypher a ejecutar
            parameters: Parámetros para la query
            
        Returns:
            Lista de diccionarios con los resultados
        """
        if self._driver is None:
            await self.connect()
        
        async with self.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records
    
    async def execute_write(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Ejecuta una query de escritura y retorna estadísticas.
        
        Args:
            query: Query Cypher de escritura
            parameters: Parámetros para la query
            
        Returns:
            Diccionario con estadísticas de la operación
        """
        if self._driver is None:
            await self.connect()
        
        async with self.session() as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()
            
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }
    
    async def health_check(self) -> bool:
        """Verifica que la conexión esté activa."""
        try:
            result = await self.execute("RETURN 1 as health")
            return len(result) > 0
        except Exception as e:
            logger.error(f"Health check Neo4j falló: {e}")
            return False
    
    async def get_node_counts(self) -> dict[str, int]:
        """Retorna conteo de nodos por label."""
        result = await self.execute("""
            CALL db.labels() YIELD label
            CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {}) YIELD value
            RETURN label, value.count as count
        """)
        return {r["label"]: r["count"] for r in result}
    
    async def get_relationship_counts(self) -> dict[str, int]:
        """Retorna conteo de relaciones por tipo."""
        result = await self.execute("""
            CALL db.relationshipTypes() YIELD relationshipType
            CALL apoc.cypher.run('MATCH ()-[r:`' + relationshipType + '`]->() RETURN count(r) as count', {}) YIELD value
            RETURN relationshipType, value.count as count
        """)
        return {r["relationshipType"]: r["count"] for r in result}


# Instancia global
neo4j_client = Neo4jClient()


async def get_neo4j_client() -> Neo4jClient:
    """Retorna el cliente Neo4j (singleton)."""
    if neo4j_client._driver is None:
        await neo4j_client.connect()
    return neo4j_client


#!/usr/bin/env python3
"""
Script para inicializar el Knowledge Graph.
Crea constraints e índices en Neo4j.
"""
import asyncio
import logging
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.neo4j_client import neo4j_client
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CONSTRAINTS = [
    # Unicidad por erp_id
    "CREATE CONSTRAINT responsable_erp_id IF NOT EXISTS FOR (r:Responsable) REQUIRE r.erp_id IS UNIQUE",
    "CREATE CONSTRAINT estudiante_erp_id IF NOT EXISTS FOR (e:Estudiante) REQUIRE e.erp_id IS UNIQUE",
    "CREATE CONSTRAINT cuota_erp_id IF NOT EXISTS FOR (c:Cuota) REQUIRE c.erp_id IS UNIQUE",
    "CREATE CONSTRAINT cluster_tipo IF NOT EXISTS FOR (c:ClusterComportamiento) REQUIRE c.tipo IS UNIQUE",
    "CREATE CONSTRAINT grado_nombre IF NOT EXISTS FOR (g:Grado) REQUIRE g.nombre IS UNIQUE",
]

INDEXES = [
    # Índices de performance
    "CREATE INDEX responsable_whatsapp IF NOT EXISTS FOR (r:Responsable) ON (r.whatsapp)",
    "CREATE INDEX responsable_perfil IF NOT EXISTS FOR (r:Responsable) ON (r.perfil_pagador)",
    "CREATE INDEX responsable_riesgo IF NOT EXISTS FOR (r:Responsable) ON (r.nivel_riesgo)",
    "CREATE INDEX cuota_estado IF NOT EXISTS FOR (c:Cuota) ON (c.estado)",
    "CREATE INDEX cuota_vencimiento IF NOT EXISTS FOR (c:Cuota) ON (c.fecha_vencimiento)",
    "CREATE INDEX estudiante_grado IF NOT EXISTS FOR (e:Estudiante) ON (e.grado)",
    "CREATE INDEX ticket_estado IF NOT EXISTS FOR (t:Ticket) ON (t.estado)",
]


async def init_graph():
    """Inicializa el Knowledge Graph con constraints e índices."""
    
    print("=" * 60)
    print("INICIALIZACIÓN DEL KNOWLEDGE GRAPH")
    print("=" * 60)
    print(f"Neo4j URI: {settings.NEO4J_URI}")
    print(f"Usuario: {settings.NEO4J_USER}")
    print()
    
    try:
        # Conectar
        print("📦 Conectando a Neo4j...")
        await neo4j_client.connect()
        print("   ✅ Conectado")
        print()
        
        # Crear constraints
        print("🔒 Creando constraints...")
        for constraint in CONSTRAINTS:
            try:
                await neo4j_client.execute_write(constraint)
                nombre = constraint.split("IF NOT EXISTS")[0].split("CREATE CONSTRAINT")[1].strip()
                print(f"   ✅ {nombre}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"   ⚠️  Ya existe: {constraint[:50]}...")
                else:
                    print(f"   ❌ Error: {e}")
        print()
        
        # Crear índices
        print("📇 Creando índices...")
        for index in INDEXES:
            try:
                await neo4j_client.execute_write(index)
                nombre = index.split("IF NOT EXISTS")[0].split("CREATE INDEX")[1].strip()
                print(f"   ✅ {nombre}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"   ⚠️  Ya existe: {index[:50]}...")
                else:
                    print(f"   ❌ Error: {e}")
        print()
        
        # Verificar
        print("📊 Verificando estructura...")
        
        constraints = await neo4j_client.execute("SHOW CONSTRAINTS")
        print(f"   Constraints: {len(constraints)}")
        
        indexes = await neo4j_client.execute("SHOW INDEXES")
        print(f"   Índices: {len(indexes)}")
        
        print()
        print("=" * 60)
        print("✅ INICIALIZACIÓN COMPLETADA")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(init_graph())


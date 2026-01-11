#!/usr/bin/env python3
"""
Script para poblar las tablas de cache de Gestor WS 
con datos del ERP Mock.
"""
import asyncio
import asyncpg
import os

# Conexiones
ERP_DB = os.getenv("ERP_DATABASE_URL", "postgresql://erp_user:erp_pass@host.docker.internal:5433/erp_mock")
GESTOR_DB = os.getenv("DATABASE_URL", "postgresql://gestor_user:gestor_pass@host.docker.internal:5432/gestor_ws")


async def sync_cache():
    """Sincroniza datos desde ERP Mock a cache de Gestor WS."""
    
    print("=" * 60)
    print("SINCRONIZAR CACHE - ERP Mock → Gestor WS")
    print("=" * 60)
    
    # Conectar a ERP Mock
    print(f"\n📦 Conectando a ERP Mock...")
    erp_conn = await asyncpg.connect(ERP_DB)
    print(f"   ✅ Conectado")
    
    # Conectar a Gestor WS
    print(f"📦 Conectando a Gestor WS...")
    gestor_conn = await asyncpg.connect(GESTOR_DB)
    print(f"   ✅ Conectado")
    
    try:
        # 1. Sincronizar responsables
        print("\n📥 Sincronizando responsables...")
        responsables = await erp_conn.fetch("""
            SELECT id, nombre, apellido, whatsapp, email 
            FROM erp_responsables
        """)
        
        for r in responsables:
            await gestor_conn.execute("""
                INSERT INTO cache_responsables 
                    (erp_responsable_id, nombre, apellido, whatsapp, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (erp_responsable_id) 
                DO UPDATE SET 
                    nombre = EXCLUDED.nombre,
                    apellido = EXCLUDED.apellido,
                    whatsapp = EXCLUDED.whatsapp,
                    updated_at = NOW()
            """, r['id'], r['nombre'], r['apellido'], r['whatsapp'])
        print(f"   ✅ {len(responsables)} responsables sincronizados")
        
        # 2. Sincronizar alumnos
        print("📥 Sincronizando alumnos...")
        alumnos = await erp_conn.fetch("""
            SELECT a.id, a.nombre, a.apellido, a.grado, r.responsable_id
            FROM erp_alumnos a
            LEFT JOIN erp_responsabilidad r ON a.id = r.alumno_id
        """)
        
        for a in alumnos:
            await gestor_conn.execute("""
                INSERT INTO cache_alumnos 
                    (erp_alumno_id, nombre, apellido, grado, erp_responsable_id, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (erp_alumno_id) 
                DO UPDATE SET 
                    nombre = EXCLUDED.nombre,
                    apellido = EXCLUDED.apellido,
                    grado = EXCLUDED.grado,
                    erp_responsable_id = EXCLUDED.erp_responsable_id,
                    updated_at = NOW()
            """, a['id'], a['nombre'], a['apellido'], a['grado'], a['responsable_id'])
        print(f"   ✅ {len(alumnos)} alumnos sincronizados")
        
        # 3. Sincronizar cuotas
        print("📥 Sincronizando cuotas...")
        cuotas = await erp_conn.fetch("""
            SELECT id, alumno_id, monto, fecha_vencimiento, estado, fecha_pago, link_pago
            FROM erp_cuotas
        """)
        
        for c in cuotas:
            await gestor_conn.execute("""
                INSERT INTO cache_cuotas 
                    (erp_cuota_id, erp_alumno_id, monto, fecha_vencimiento, estado, fecha_pago, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (erp_cuota_id) 
                DO UPDATE SET 
                    erp_alumno_id = EXCLUDED.erp_alumno_id,
                    monto = EXCLUDED.monto,
                    fecha_vencimiento = EXCLUDED.fecha_vencimiento,
                    estado = EXCLUDED.estado,
                    fecha_pago = EXCLUDED.fecha_pago,
                    updated_at = NOW()
            """, c['id'], c['alumno_id'], c['monto'], c['fecha_vencimiento'], 
                c['estado'], c['fecha_pago'])
        print(f"   ✅ {len(cuotas)} cuotas sincronizadas")
        
        # Resumen
        print("\n" + "=" * 60)
        print("✅ SINCRONIZACIÓN COMPLETADA")
        print("=" * 60)
        print(f"\n📊 Resumen:")
        print(f"   • {len(responsables)} responsables")
        print(f"   • {len(alumnos)} alumnos")
        print(f"   • {len(cuotas)} cuotas")
        
    finally:
        await erp_conn.close()
        await gestor_conn.close()


if __name__ == "__main__":
    asyncio.run(sync_cache())


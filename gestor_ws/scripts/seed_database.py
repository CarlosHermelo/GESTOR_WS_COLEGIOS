"""
Script para poblar la base de datos de gestor_ws con datos de prueba.
Crea 3 responsables (padres) con sus respectivos alumnos y cuotas en la cache.
"""
import asyncio
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
import os
import sys

# Agregar el directorio raíz al path para poder importar la app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete
from app.database import async_session_maker, init_db, Base, engine
from app.models.cache import CacheResponsable, CacheAlumno, CacheCuota

async def seed_data():
    print("🚀 Iniciando seeding de base de datos...")
    
    # Asegurar que las tablas existen
    await init_db()
    
    async with async_session_maker() as session:
        # 1. Limpiar datos previos de cache para evitar duplicados
        print("🧹 Limpiando datos previos de cache...")
        await session.execute(delete(CacheCuota))
        await session.execute(delete(CacheAlumno))
        await session.execute(delete(CacheResponsable))
        await session.commit()
        
        # 2. Definir Datos de Prueba
        print("📝 Creando nuevos datos de prueba...")
        
        # --- RESPONSABLE 1: Carlos (2 hijos) ---
        resp1 = CacheResponsable(
            erp_responsable_id="R-001",
            nombre="Carlos",
            apellido="Hermelo",
            whatsapp="+5491199999999",
            email="carlos@ejemplo.com"
        )
        
        # --- RESPONSABLE 2: María (1 hijo) ---
        resp2 = CacheResponsable(
            erp_responsable_id="R-002",
            nombre="María",
            apellido="García",
            whatsapp="+5491188888888",
            email="maria@ejemplo.com"
        )
        
        # --- RESPONSABLE 3: José (1 hijo) ---
        resp3 = CacheResponsable(
            erp_responsable_id="R-003",
            nombre="José",
            apellido="Rodríguez",
            whatsapp="+5491177777777",
            email="jose@ejemplo.com"
        )
        
        session.add_all([resp1, resp2, resp3])
        await session.flush() # Para asegurar IDs antes de crear alumnos
        
        # --- ALUMNOS ---
        alumnos = [
            # Hijos de Carlos
            CacheAlumno(erp_alumno_id="A-001", nombre="Juan", apellido="Hermelo", grado="3ro A", erp_responsable_id="R-001"),
            CacheAlumno(erp_alumno_id="A-002", nombre="Ana", apellido="Hermelo", grado="1ro B", erp_responsable_id="R-001"),
            # Hijo de María
            CacheAlumno(erp_alumno_id="A-003", nombre="Pedro", apellido="García", grado="5to C", erp_responsable_id="R-002"),
            # Hija de José
            CacheAlumno(erp_alumno_id="A-004", nombre="Lucía", apellido="Rodríguez", grado="2do B", erp_responsable_id="R-003"),
        ]
        
        session.add_all(alumnos)
        await session.flush()
        
        # --- CUOTAS ---
        hoy = date.today()
        mes_pasado = hoy.replace(day=1) - timedelta(days=1)
        
        cuotas = [
            # Cuotas para Juan (vencida y pendiente)
            CacheCuota(
                erp_cuota_id="C-001", erp_alumno_id="A-001", monto=Decimal("45000.00"), 
                fecha_vencimiento=mes_pasado.replace(day=10), estado="vencida", 
                link_pago="https://pagos.colegio.com/C-001"
            ),
            CacheCuota(
                erp_cuota_id="C-002", erp_alumno_id="A-001", monto=Decimal("45000.00"), 
                fecha_vencimiento=hoy.replace(day=10), estado="pendiente", 
                link_pago="https://pagos.colegio.com/C-002"
            ),
            # Cuota para Ana (pagada)
            CacheCuota(
                erp_cuota_id="C-003", erp_alumno_id="A-002", monto=Decimal("42000.00"), 
                fecha_vencimiento=mes_pasado.replace(day=10), estado="pagada", 
                fecha_pago=datetime.now() - timedelta(days=15)
            ),
            # Cuota para Pedro (pendiente)
            CacheCuota(
                erp_cuota_id="C-004", erp_alumno_id="A-003", monto=Decimal("48000.00"), 
                fecha_vencimiento=hoy.replace(day=10), estado="pendiente", 
                link_pago="https://pagos.colegio.com/C-004"
            ),
        ]
        
        session.add_all(cuotas)
        await session.commit()
        
        print("✅ Seeding completado con éxito!")
        print(f"📊 Resumen: 3 Responsables, 4 Alumnos, 4 Cuotas.")

if __name__ == "__main__":
    asyncio.run(seed_data())

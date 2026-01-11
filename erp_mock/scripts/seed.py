"""
Script para poblar la base de datos con datos de prueba.
Es idempotente: puede ejecutarse múltiples veces sin duplicar datos.

Uso:
    docker-compose exec api python scripts/seed.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from app.database import get_db_context, init_db
from app.models import (
    Responsable, Alumno, Responsabilidad,
    PlanPago, Cuota, Pago
)


# ============== DATOS DE PRUEBA ==============

RESPONSABLES_DATA = [
    {
        "id": "R001",
        "nombre": "María",
        "apellido": "González",
        "whatsapp": "+5491112345001",
        "email": "maria.gonzalez@email.com",
        "tipo": "madre"
    },
    {
        "id": "R002",
        "nombre": "Juan",
        "apellido": "Pérez",
        "whatsapp": "+5491112345002",
        "email": "juan.perez@email.com",
        "tipo": "padre"
    },
    {
        "id": "R003",
        "nombre": "Ana",
        "apellido": "Rodríguez",
        "whatsapp": "+5491112345003",
        "email": "ana.rodriguez@email.com",
        "tipo": "madre"
    },
    {
        "id": "R004",
        "nombre": "Carlos",
        "apellido": "López",
        "whatsapp": "+5491112345004",
        "email": "carlos.lopez@email.com",
        "tipo": "padre"
    },
    {
        "id": "R005",
        "nombre": "Laura",
        "apellido": "Martínez",
        "whatsapp": "+5491112345005",
        "email": "laura.martinez@email.com",
        "tipo": "madre"
    }
]

ALUMNOS_DATA = [
    {
        "id": "A001",
        "nombre": "Martín",
        "apellido": "González",
        "fecha_nacimiento": date(2015, 3, 15),
        "grado": "4to A",
        "activo": True,
        "responsable_id": "R001"
    },
    {
        "id": "A002",
        "nombre": "Sofía",
        "apellido": "Pérez",
        "fecha_nacimiento": date(2016, 7, 22),
        "grado": "3ro B",
        "activo": True,
        "responsable_id": "R002"
    },
    {
        "id": "A003",
        "nombre": "Lucas",
        "apellido": "Rodríguez",
        "fecha_nacimiento": date(2014, 11, 8),
        "grado": "5to A",
        "activo": True,
        "responsable_id": "R003"
    },
    {
        "id": "A004",
        "nombre": "Valentina",
        "apellido": "López",
        "fecha_nacimiento": date(2017, 5, 30),
        "grado": "2do C",
        "activo": True,
        "responsable_id": "R004"
    },
    {
        "id": "A005",
        "nombre": "Tomás",
        "apellido": "López",
        "fecha_nacimiento": date(2015, 9, 12),
        "grado": "4to B",
        "activo": True,
        "responsable_id": "R004"
    },
    {
        "id": "A006",
        "nombre": "Emma",
        "apellido": "Martínez",
        "fecha_nacimiento": date(2016, 1, 25),
        "grado": "3ro A",
        "activo": True,
        "responsable_id": "R005"
    }
]

PLAN_PAGO_DATA = {
    "id": "PP001",
    "nombre": "Plan Primaria 2026",
    "cantidad_cuotas": 10,
    "monto_cuota": Decimal("50000.00"),
    "anio": 2026
}


def generar_cuotas_alumno(alumno_id: str, plan_id: str, es_emma: bool = False) -> list:
    """
    Genera las 10 cuotas para un alumno.
    
    Args:
        alumno_id: ID del alumno
        plan_id: ID del plan de pago
        es_emma: Si es Emma Martínez (caso especial con cuotas vencidas)
    
    Returns:
        Lista de diccionarios con datos de cuotas
    """
    cuotas = []
    monto = Decimal("50000.00")
    # Fecha base: 10 de febrero 2026
    fecha_base = date(2026, 2, 10)
    
    for i in range(1, 11):
        # Calcular fecha de vencimiento (mes a mes)
        fecha_vencimiento = fecha_base + relativedelta(months=i-1)
        
        # Determinar estado según reglas
        if i <= 2:
            if es_emma:
                # Emma tiene cuotas 1 y 2 VENCIDAS
                estado = "vencida"
                fecha_pago = None
            else:
                # Resto tiene cuotas 1 y 2 PAGADAS
                estado = "pagada"
                fecha_pago = datetime(2026, fecha_vencimiento.month, 5, 10, 0, 0)
        else:
            estado = "pendiente"
            fecha_pago = None
        
        cuota = {
            "id": f"C-{alumno_id}-{i:02d}",
            "alumno_id": alumno_id,
            "plan_pago_id": plan_id,
            "numero_cuota": i,
            "monto": monto,
            "fecha_vencimiento": fecha_vencimiento,
            "estado": estado,
            "link_pago": f"https://pagos.colegio.edu/cuota/{alumno_id}/{i}",
            "fecha_pago": fecha_pago
        }
        cuotas.append(cuota)
    
    return cuotas


async def check_existing_data(db) -> bool:
    """Verifica si ya existen datos en la BD."""
    result = await db.execute(select(Responsable).limit(1))
    return result.scalar_one_or_none() is not None


async def seed_responsables(db) -> None:
    """Inserta responsables si no existen."""
    print("📝 Insertando responsables...")
    
    for data in RESPONSABLES_DATA:
        # Verificar si ya existe
        result = await db.execute(
            select(Responsable).where(Responsable.id == data["id"])
        )
        if result.scalar_one_or_none():
            print(f"   ⏭️  Responsable {data['id']} ya existe, omitiendo...")
            continue
        
        responsable = Responsable(**data)
        db.add(responsable)
        print(f"   ✅ Creado: {data['nombre']} {data['apellido']} ({data['whatsapp']})")
    
    await db.flush()


async def seed_alumnos(db) -> None:
    """Inserta alumnos y sus relaciones con responsables."""
    print("\n📝 Insertando alumnos...")
    
    for data in ALUMNOS_DATA:
        responsable_id = data.pop("responsable_id")
        
        # Verificar si ya existe
        result = await db.execute(
            select(Alumno).where(Alumno.id == data["id"])
        )
        if result.scalar_one_or_none():
            print(f"   ⏭️  Alumno {data['id']} ya existe, omitiendo...")
            continue
        
        alumno = Alumno(**data)
        db.add(alumno)
        await db.flush()
        
        # Crear relación con responsable
        responsabilidad = Responsabilidad(
            responsable_id=responsable_id,
            alumno_id=data["id"]
        )
        db.add(responsabilidad)
        
        print(f"   ✅ Creado: {data['nombre']} {data['apellido']} ({data['grado']})")
    
    await db.flush()


async def seed_plan_pago(db) -> None:
    """Inserta el plan de pago si no existe."""
    print("\n📝 Insertando plan de pago...")
    
    result = await db.execute(
        select(PlanPago).where(PlanPago.id == PLAN_PAGO_DATA["id"])
    )
    if result.scalar_one_or_none():
        print(f"   ⏭️  Plan de pago {PLAN_PAGO_DATA['id']} ya existe, omitiendo...")
        return
    
    plan = PlanPago(**PLAN_PAGO_DATA)
    db.add(plan)
    await db.flush()
    
    print(f"   ✅ Creado: {PLAN_PAGO_DATA['nombre']} - {PLAN_PAGO_DATA['cantidad_cuotas']} cuotas de ${PLAN_PAGO_DATA['monto_cuota']}")


async def seed_cuotas(db) -> None:
    """Genera cuotas para todos los alumnos."""
    print("\n📝 Generando cuotas...")
    
    for alumno_data in ALUMNOS_DATA:
        alumno_id = alumno_data["id"]
        
        # Verificar si ya tiene cuotas
        result = await db.execute(
            select(Cuota).where(Cuota.alumno_id == alumno_id).limit(1)
        )
        if result.scalar_one_or_none():
            print(f"   ⏭️  Cuotas para alumno {alumno_id} ya existen, omitiendo...")
            continue
        
        # Emma Martínez (A006) tiene caso especial
        es_emma = alumno_id == "A006"
        
        cuotas_data = generar_cuotas_alumno(
            alumno_id=alumno_id,
            plan_id=PLAN_PAGO_DATA["id"],
            es_emma=es_emma
        )
        
        for cuota_data in cuotas_data:
            cuota = Cuota(**cuota_data)
            db.add(cuota)
        
        estado_especial = " (con cuotas VENCIDAS)" if es_emma else ""
        print(f"   ✅ Generadas 10 cuotas para {alumno_data['nombre']} {alumno_data['apellido']}{estado_especial}")
    
    await db.flush()


async def seed_pagos_historicos(db) -> None:
    """Crea registros de pagos para las cuotas pagadas."""
    print("\n📝 Registrando pagos históricos...")
    
    # Buscar cuotas pagadas
    result = await db.execute(
        select(Cuota).where(Cuota.estado == "pagada")
    )
    cuotas_pagadas = result.scalars().all()
    
    for cuota in cuotas_pagadas:
        # Verificar si ya tiene pago
        result = await db.execute(
            select(Pago).where(Pago.cuota_id == cuota.id).limit(1)
        )
        if result.scalar_one_or_none():
            continue
        
        pago = Pago(
            id=f"PAG-{cuota.id}",
            cuota_id=cuota.id,
            monto=cuota.monto,
            fecha_pago=cuota.fecha_pago or datetime.now(),
            metodo_pago="transferencia",
            referencia=f"SEED-{cuota.id}"
        )
        db.add(pago)
    
    await db.flush()
    print(f"   ✅ Registrados pagos para {len(cuotas_pagadas)} cuotas")


async def run_seed():
    """Ejecuta el proceso completo de seed."""
    print("\n" + "="*60)
    print("🌱 SEED - ERP Mock Database")
    print("="*60)
    
    # Inicializar BD (crear tablas si no existen)
    await init_db()
    
    async with get_db_context() as db:
        # Ejecutar seeds en orden
        await seed_responsables(db)
        await seed_alumnos(db)
        await seed_plan_pago(db)
        await seed_cuotas(db)
        await seed_pagos_historicos(db)
        
        # Commit final
        await db.commit()
    
    print("\n" + "="*60)
    print("✅ SEED COMPLETADO EXITOSAMENTE")
    print("="*60)
    print("\n📊 Resumen de datos creados:")
    print(f"   • {len(RESPONSABLES_DATA)} responsables")
    print(f"   • {len(ALUMNOS_DATA)} alumnos")
    print(f"   • 1 plan de pago")
    print(f"   • {len(ALUMNOS_DATA) * 10} cuotas (10 por alumno)")
    print("\n📌 Escenario especial:")
    print("   • Emma Martínez (A006): Cuotas 1 y 2 VENCIDAS sin pagar")
    print("   • Resto de alumnos: Cuotas 1 y 2 PAGADAS")
    print("")


if __name__ == "__main__":
    asyncio.run(run_seed())


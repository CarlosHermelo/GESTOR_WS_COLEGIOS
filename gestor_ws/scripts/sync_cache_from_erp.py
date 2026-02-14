import asyncio
import sys
import os
import requests
from datetime import datetime

# Agregar directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import init_db, async_session_maker
from app.models.cache import CacheResponsable, CacheAlumno, CacheCuota
from sqlalchemy import text, delete

ERP_URL = "http://localhost:8001/api/v1"

async def sync():
    print("🔄 Iniciando sincronización de Caché desde ERP Mock...")
    
    # Asegurar que el ERP esté arriba
    try:
        health = requests.get("http://localhost:8001/health")
        if health.status_code != 200:
            print("❌ El ERP no responde correctamente.")
            return
    except Exception as e:
        print(f"❌ No se pudo conectar con el ERP en localhost:8001: {e}")
        return

    # Inicializar BD del Gestor
    await init_db()

    async with async_session_maker() as db:
        print("🧹 Limpiando caché actual...")
        await db.execute(delete(CacheCuota))
        await db.execute(delete(CacheAlumno))
        await db.execute(delete(CacheResponsable))
        await db.commit()

        # 1. Obtener todos los responsables (vía endpoint de health o recorriendo IDs si fuera necesario)
        # En este mock, sabemos que son 15. Vamos a usar una lista conocida para el seed.
        resp_ids = [f"resp-{str(i).zfill(3)}" for i in range(1, 16)]
        
        for rid in resp_ids:
            # En la vida real habría un endpoint /responsables, aquí usamos by-whatsapp o detalle
            # Pero para el sync masivo, simularemos obtener la lista
            pass

        # Nota: El ERP Mock no tiene un endpoint "listar todos" público fácilmente, 
        # así que para este script de test usaremos la lista de WhatsApps de los 15 casos.
        whatsapps = [
            "+5491199999999", "+5491188888888", "+5491177777777", "+5491166666666",
            "+5491155555555", "+5491144444444", "+5491133333333", "+5491122222222",
            "+5491111111111", "+5491100000000", "+5491112223333", "+5491144455566",
            "+5491177788899", "+5491122244466", "+5491133366699"
        ]

        from urllib.parse import quote_plus
        for ws in whatsapps:
            print(f"📥 Sincronizando responsable: {ws}...")
            ws_encoded = quote_plus(ws)
            res = requests.get(f"{ERP_URL}/responsables/by-whatsapp/{ws_encoded}")
            if res.status_code == 200:
                data = res.json()
                
                # Guardar Responsable
                cache_resp = CacheResponsable(
                    erp_responsable_id=data["id"],
                    nombre=data["nombre"],
                    apellido=data["apellido"],
                    whatsapp=data["whatsapp"],
                    email=data["email"]
                )
                db.add(cache_resp)
                
                # Guardar Alumnos
                for alu in data.get("alumnos", []):
                    cache_alu = CacheAlumno(
                        erp_alumno_id=alu["id"],
                        nombre=alu["nombre"],
                        apellido=alu["apellido"],
                        grado=alu["grado"],
                        erp_responsable_id=data["id"]
                    )
                    db.add(cache_alu)
                    
                    # Cargar cuotas del alumno
                    c_res = requests.get(f"{ERP_URL}/alumnos/{alu['id']}/cuotas")
                    if c_res.status_code == 200:
                        for cuota in c_res.json():
                            # Parsear fecha pago si existe
                            fp = None
                            if cuota.get("fecha_pago"):
                                try:
                                    fp = datetime.fromisoformat(cuota["fecha_pago"].replace("Z", "+00:00"))
                                except:
                                    pass
                                    
                            cache_cuota = CacheCuota(
                                erp_cuota_id=cuota["id"],
                                erp_alumno_id=alu["id"],
                                monto=cuota["monto"],
                                fecha_vencimiento=datetime.strptime(cuota["fecha_vencimiento"], "%Y-%m-%d").date(),
                                estado=cuota["estado"],
                                link_pago=cuota.get("link_pago"),
                                fecha_pago=fp
                            )
                            db.add(cache_cuota)
            else:
                print(f"⚠️ No se pudo obtener datos para {ws}")

        await db.commit()
    print("✅ Caché sincronizada correctamente!")

if __name__ == "__main__":
    asyncio.run(sync())

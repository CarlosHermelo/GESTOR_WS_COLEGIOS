"""
Tools para interacción con el ERP.
Categoría: erp
"""
import logging
from typing import Optional

from app.mcp.registry import tool
from app.config import settings
from app.tools.base import erp_client, MOCK_RESPONSABLE, MOCK_CUOTAS

logger = logging.getLogger(__name__)


@tool(
    category="erp",
    mock_response={
        "found": True,
        "responsable": "María García",
        "alumnos": [
            {
                "id": "mock-alumno-001",
                "nombre": "Juan Pérez García",
                "grado": "3ro A",
                "cuotas_pendientes": [
                    {"id": "c003", "numero": 3, "monto": 45000, "vencimiento": "15/03/2026"},
                    {"id": "c004", "numero": 4, "monto": 45000, "vencimiento": "15/04/2026"}
                ]
            },
            {
                "id": "mock-alumno-002",
                "nombre": "Ana Pérez García",
                "grado": "1ro B",
                "cuotas_pendientes": [
                    {"id": "c103", "numero": 3, "monto": 42000, "vencimiento": "15/03/2026"}
                ]
            }
        ],
        "deuda_total": 132000
    }
)
async def consultar_estado_cuenta(whatsapp: str) -> dict:
    """
    Consulta el estado de cuenta de un responsable por su WhatsApp.
    Retorna información de alumnos y cuotas pendientes.
    
    Args:
        whatsapp: Número de WhatsApp del responsable (ej: +5491112345001)
    
    Returns:
        dict con found, responsable, alumnos, cuotas_pendientes y deuda_total
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] consultar_estado_cuenta({whatsapp})")
        return {
            "found": True,
            "responsable": MOCK_RESPONSABLE["nombre"],
            "alumnos": [
                {
                    "id": a["id"],
                    "nombre": f"{a['nombre']} {a['apellido']}",
                    "grado": a["grado"],
                    "cuotas_pendientes": [
                        {
                            "id": c["id"],
                            "numero": c["numero_cuota"],
                            "monto": c["monto"],
                            "vencimiento": c["fecha_vencimiento"],
                            "link_pago": c["link_pago"]
                        }
                        for c in MOCK_CUOTAS
                    ]
                }
                for a in MOCK_RESPONSABLE["alumnos"]
            ],
            "deuda_total": sum(c["monto"] for c in MOCK_CUOTAS) * len(MOCK_RESPONSABLE["alumnos"])
        }
    
    try:
        response = await erp_client.get(f"/api/v1/responsables/by-whatsapp/{whatsapp}")
        
        # Transformar respuesta del ERP al formato esperado
        if not response:
            return {"found": False, "error": "Responsable no encontrado"}
        
        # Calcular deuda total y cuotas pendientes
        alumnos_data = []
        deuda_total = 0
        
        for alumno in response.get("alumnos", []):
            cuotas_pendientes = []
            for cuota in alumno.get("cuotas", []):
                if cuota.get("estado") == "pendiente":
                    cuotas_pendientes.append({
                        "id": cuota.get("id"),
                        "numero": cuota.get("numero_cuota"),
                        "monto": cuota.get("monto"),
                        "vencimiento": cuota.get("fecha_vencimiento"),
                        "link_pago": cuota.get("link_pago", "")
                    })
                    deuda_total += cuota.get("monto", 0)
            
            alumnos_data.append({
                "id": alumno.get("id"),
                "nombre": f"{alumno.get('nombre', '')} {alumno.get('apellido', '')}",
                "grado": alumno.get("grado", ""),
                "cuotas_pendientes": cuotas_pendientes
            })
        
        return {
            "found": True,
            "responsable": response.get("nombre", ""),
            "alumnos": alumnos_data,
            "deuda_total": deuda_total
        }
    except Exception as e:
        logger.error(f"Error consultando ERP: {e}")
        return {"found": False, "error": str(e)}


@tool(
    category="erp",
    mock_response={
        "found": True,
        "cuota_id": "mock-cuota-003",
        "monto": 45000,
        "vencimiento": "15/03/2026",
        "link_pago": "https://pago.mock/cuota-003"
    }
)
async def obtener_link_pago(cuota_id: str) -> dict:
    """
    Obtiene el link de pago para una cuota específica.
    
    Args:
        cuota_id: ID de la cuota
    
    Returns:
        dict con found, cuota_id, monto, vencimiento y link_pago
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] obtener_link_pago({cuota_id})")
        return {
            "found": True,
            "cuota_id": cuota_id,
            "monto": 45000,
            "vencimiento": "15/03/2026",
            "link_pago": f"https://pago.mock/{cuota_id}"
        }
    
    try:
        response = await erp_client.get(f"/api/v1/cuotas/{cuota_id}")
        return {
            "found": True,
            "cuota_id": cuota_id,
            "monto": response.get("monto", 0),
            "vencimiento": response.get("fecha_vencimiento", ""),
            "link_pago": response.get("link_pago", "")
        }
    except Exception as e:
        logger.error(f"Error obteniendo link de pago: {e}")
        return {"found": False, "error": str(e)}


@tool(
    category="erp",
    mock_response={
        "registered": True,
        "cuota_id": "mock-cuota-003",
        "message": "Pago registrado, pendiente de validación"
    }
)
async def registrar_confirmacion_pago(cuota_id: str, whatsapp: str) -> dict:
    """
    Registra que el padre confirmó haber realizado un pago.
    El pago queda pendiente de validación.
    
    Args:
        cuota_id: ID de la cuota pagada
        whatsapp: WhatsApp del responsable
    
    Returns:
        dict con registered y message
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] registrar_confirmacion_pago({cuota_id}, {whatsapp})")
        return {
            "registered": True,
            "cuota_id": cuota_id,
            "message": "Pago registrado (MOCK), pendiente de validación"
        }
    
    try:
        # El ERP real espera: cuota_id, monto, metodo, referencia
        # Por ahora enviamos solo cuota_id y whatsapp, el ERP puede inferir el resto
        response = await erp_client.post("/api/v1/pagos/confirmar", {
            "cuota_id": cuota_id,
            "whatsapp": whatsapp,
            "estado": "pendiente_validacion"
        })
        return {
            "registered": True,
            "cuota_id": cuota_id,
            "message": "Pago registrado, pendiente de validación"
        }
    except Exception as e:
        logger.error(f"Error registrando pago: {e}")
        return {"registered": False, "error": str(e)}


@tool(
    category="erp",
    mock_response={
        "found": True,
        "alumno": {
            "id": "mock-alumno-001",
            "nombre": "Juan Pérez García",
            "grado": "3ro A",
            "responsable": "María García"
        }
    }
)
async def buscar_alumno(alumno_id: str) -> dict:
    """
    Busca información de un alumno por su ID.
    
    Args:
        alumno_id: ID del alumno
    
    Returns:
        dict con información del alumno
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] buscar_alumno({alumno_id})")
        alumno = MOCK_RESPONSABLE["alumnos"][0]
        return {
            "found": True,
            "alumno": {
                "id": alumno_id,
                "nombre": f"{alumno['nombre']} {alumno['apellido']}",
                "grado": alumno["grado"],
                "responsable": MOCK_RESPONSABLE["nombre"]
            }
        }
    
    try:
        response = await erp_client.get(f"/api/v1/alumnos/{alumno_id}")
        return {
            "found": True,
            "alumno": {
                "id": response.get("id"),
                "nombre": f"{response.get('nombre', '')} {response.get('apellido', '')}",
                "grado": response.get("grado", ""),
                "responsable": response.get("responsable", {}).get("nombre", "")
            }
        }
    except Exception as e:
        logger.error(f"Error buscando alumno: {e}")
        return {"found": False, "error": str(e)}

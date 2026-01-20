"""
Tools para interacción con el Knowledge Graph.
Categoría: kg
"""
import logging
from typing import Optional

from app.mcp.registry import tool
from app.config import settings
from app.tools.base import kg_client, MOCK_INFO_INSTITUCIONAL

logger = logging.getLogger(__name__)


@tool(
    category="kg",
    mock_response={
        "found": True,
        "horarios": {
            "primaria": {"turno_mañana": "7:30 - 12:30", "turno_tarde": "13:00 - 18:00"},
            "secundaria": {"turno_mañana": "7:15 - 13:15", "turno_tarde": "13:30 - 19:30"},
            "administracion": "8:00 - 17:00 (Lunes a Viernes)"
        }
    }
)
async def buscar_horarios(nivel: str = None) -> dict:
    """
    Busca horarios de clases del colegio.
    
    Args:
        nivel: Nivel educativo (primaria, secundaria, administracion). Si no se especifica, retorna todos.
    
    Returns:
        dict con horarios encontrados
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] buscar_horarios({nivel})")
        
        horarios = MOCK_INFO_INSTITUCIONAL["horarios"]
        
        if nivel and nivel.lower() in horarios:
            return {
                "found": True,
                "nivel": nivel,
                "horarios": horarios[nivel.lower()]
            }
        
        return {"found": True, "horarios": horarios}
    
    try:
        params = {}
        if nivel:
            params["nivel"] = nivel
        
        response = await kg_client.get("/info/horarios", params=params)
        return {"found": True, **response}
    except Exception as e:
        logger.error(f"Error buscando horarios: {e}")
        return {"found": False, "error": str(e)}


@tool(
    category="kg",
    mock_response={
        "found": True,
        "calendario": {
            "inicio_clases": "4 de marzo de 2026",
            "fin_clases": "11 de diciembre de 2026",
            "receso_invierno": "14 al 25 de julio de 2026"
        }
    }
)
async def buscar_calendario(tipo: str = None) -> dict:
    """
    Busca información del calendario escolar.
    
    Args:
        tipo: Tipo de fecha a buscar (inicio_clases, fin_clases, receso_invierno). Si no se especifica, retorna todo.
    
    Returns:
        dict con información del calendario
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] buscar_calendario({tipo})")
        
        calendario = MOCK_INFO_INSTITUCIONAL["calendario"]
        
        if tipo:
            tipo_lower = tipo.lower().replace(" ", "_")
            for key, value in calendario.items():
                if tipo_lower in key.lower():
                    return {"found": True, "tipo": key, "fecha": value}
        
        return {"found": True, "calendario": calendario}
    
    try:
        response = await kg_client.get("/info/calendario")
        return {"found": True, **response}
    except Exception as e:
        logger.error(f"Error buscando calendario: {e}")
        return {"found": False, "error": str(e)}


@tool(
    category="kg",
    mock_response={
        "found": True,
        "autoridades": {
            "Director General": "Dr. Roberto Martínez",
            "Directora Primaria": "Lic. María García",
            "Director Secundaria": "Prof. Juan López",
            "Coordinadora Administrativa": "Sra. Ana Fernández"
        }
    }
)
async def buscar_autoridades(cargo: str = None) -> dict:
    """
    Busca información de autoridades del colegio.
    
    Args:
        cargo: Cargo específico a buscar. Si no se especifica, retorna todas las autoridades.
    
    Returns:
        dict con información de autoridades
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] buscar_autoridades({cargo})")
        
        autoridades = MOCK_INFO_INSTITUCIONAL["autoridades"]
        
        if cargo:
            cargo_lower = cargo.lower()
            for key, value in autoridades.items():
                if cargo_lower in key.lower():
                    return {
                        "found": True,
                        "cargo": key.replace("_", " ").title(),
                        "nombre": value
                    }
        
        return {
            "found": True,
            "autoridades": {
                k.replace("_", " ").title(): v 
                for k, v in autoridades.items()
            }
        }
    
    try:
        response = await kg_client.get("/info/autoridades")
        return {"found": True, **response}
    except Exception as e:
        logger.error(f"Error buscando autoridades: {e}")
        return {"found": False, "error": str(e)}


@tool(
    category="kg",
    mock_response={
        "found": True,
        "contacto": {
            "telefono": "(011) 4555-1234",
            "email": "info@colegio.edu.ar",
            "direccion": "Av. Siempreviva 742, CABA"
        }
    }
)
async def buscar_contacto() -> dict:
    """
    Busca información de contacto del colegio.
    
    Returns:
        dict con teléfono, email y dirección
    """
    if settings.MOCK_MODE:
        logger.info("[MOCK] buscar_contacto()")
        return {"found": True, "contacto": MOCK_INFO_INSTITUCIONAL["contacto"]}
    
    try:
        response = await kg_client.get("/info/contacto")
        return {"found": True, **response}
    except Exception as e:
        logger.error(f"Error buscando contacto: {e}")
        return {"found": False, "error": str(e)}


@tool(
    category="kg",
    mock_response={
        "found": True,
        "query": "horarios de primaria",
        "resultados": {"horarios": {"primaria": {"turno_mañana": "7:30 - 12:30"}}}
    }
)
async def buscar_info_general(query: str) -> dict:
    """
    Búsqueda semántica de información general del colegio.
    
    Args:
        query: Consulta en lenguaje natural
    
    Returns:
        dict con resultados de la búsqueda
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] buscar_info_general({query})")
        
        query_lower = query.lower()
        resultados = {}
        
        # Matching simple por keywords
        if any(kw in query_lower for kw in ["horario", "hora", "clase", "turno"]):
            resultados["horarios"] = MOCK_INFO_INSTITUCIONAL["horarios"]
        
        if any(kw in query_lower for kw in ["inicio", "fin", "vacacion", "feriado", "calendario"]):
            resultados["calendario"] = MOCK_INFO_INSTITUCIONAL["calendario"]
        
        if any(kw in query_lower for kw in ["director", "autoridad", "cargo"]):
            resultados["autoridades"] = MOCK_INFO_INSTITUCIONAL["autoridades"]
        
        if any(kw in query_lower for kw in ["contacto", "telefono", "email", "direccion"]):
            resultados["contacto"] = MOCK_INFO_INSTITUCIONAL["contacto"]
        
        if not resultados:
            resultados = MOCK_INFO_INSTITUCIONAL
        
        return {"found": True, "query": query, "resultados": resultados}
    
    try:
        response = await kg_client.post("/search", {"query": query})
        return {"found": True, "query": query, **response}
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        return {"found": False, "query": query, "error": str(e)}


@tool(
    category="kg",
    mock_response={
        "patrones": [
            {"tipo": "morosidad_recurrente", "alumnos": 15, "monto_promedio": 85000},
            {"tipo": "pago_puntual", "alumnos": 120, "tasa": 0.85}
        ]
    }
)
async def analizar_patrones_pago(periodo: str = None) -> dict:
    """
    Analiza patrones de pago usando el Knowledge Graph.
    
    Args:
        periodo: Período a analizar (ej: "2026-Q1", "2026-03"). Si no se especifica, usa el actual.
    
    Returns:
        dict con patrones identificados
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] analizar_patrones_pago({periodo})")
        return {
            "patrones": [
                {"tipo": "morosidad_recurrente", "alumnos": 15, "monto_promedio": 85000},
                {"tipo": "pago_puntual", "alumnos": 120, "tasa": 0.85},
                {"tipo": "pago_parcial", "alumnos": 8, "porcentaje_promedio": 0.6}
            ],
            "periodo": periodo or "actual"
        }
    
    try:
        params = {}
        if periodo:
            params["periodo"] = periodo
        
        response = await kg_client.get("/analytics/patrones", params=params)
        return response
    except Exception as e:
        logger.error(f"Error analizando patrones: {e}")
        return {"patrones": [], "error": str(e)}


@tool(
    category="kg",
    mock_response={
        "alumno_id": "mock-alumno-001",
        "riesgo": "bajo",
        "score": 0.15,
        "factores": ["pago_puntual_historico", "sin_cuotas_vencidas"]
    }
)
async def calcular_riesgo_desercion(alumno_id: str) -> dict:
    """
    Calcula el riesgo de deserción de un alumno basándose en el Knowledge Graph.
    
    Args:
        alumno_id: ID del alumno
    
    Returns:
        dict con nivel de riesgo, score y factores
    """
    if settings.MOCK_MODE:
        logger.info(f"[MOCK] calcular_riesgo_desercion({alumno_id})")
        return {
            "alumno_id": alumno_id,
            "riesgo": "bajo",
            "score": 0.15,
            "factores": ["pago_puntual_historico", "sin_cuotas_vencidas"]
        }
    
    try:
        response = await kg_client.get(f"/analytics/riesgo/{alumno_id}")
        return response
    except Exception as e:
        logger.error(f"Error calculando riesgo: {e}")
        return {"alumno_id": alumno_id, "riesgo": "desconocido", "error": str(e)}

"""
API de reportes y analytics del Knowledge Graph.
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.neo4j_client import get_neo4j_client
from app.queries.riesgo_desercion import (
    calcular_score_riesgo_desercion,
    obtener_alumnos_alto_riesgo,
    obtener_estadisticas_riesgo
)
from app.queries.proyeccion_caja import (
    proyectar_caja,
    obtener_vencimientos_proximos,
    obtener_deuda_por_grado,
    obtener_resumen_financiero
)
from app.queries.patrones import (
    detectar_patrones,
    obtener_clusters,
    detectar_riesgo_abandono,
    detectar_familias_problema,
    detectar_grados_criticos
)
from app.queries.insights_llm import (
    generar_resumen_ejecutivo,
    obtener_insights_almacenados,
    generar_recomendaciones_personalizadas
)
from app.etl.sync_from_erp import ETLFromERP
from app.etl.sync_from_gestor import ETLFromGestor
from app.etl.llm_enrichment import LLMEnrichment
from app.llm.factory import get_provider_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reportes", tags=["Reportes"])


# ============== MODELOS ==============

class ETLResponse(BaseModel):
    status: str
    message: str
    results: Optional[dict] = None


class InsightsResponse(BaseModel):
    tendencias: list[str]
    riesgos: list[str]
    oportunidades: list[str]
    acciones: list[str]
    generado_por: Optional[str] = None
    timestamp: Optional[str] = None


# ============== ENDPOINTS RIESGO ==============

@router.get("/riesgo-desercion")
async def get_riesgo_desercion(
    umbral: int = Query(40, description="Score mínimo para incluir", ge=0, le=100)
):
    """
    Lista alumnos en riesgo de deserción con scores calculados.
    Enriquecido con clasificación LLM del responsable.
    """
    neo4j = await get_neo4j_client()
    scores = await calcular_score_riesgo_desercion(neo4j, umbral_minimo=umbral)
    
    return {
        "total": len(scores),
        "umbral_aplicado": umbral,
        "alumnos_riesgo": scores
    }


@router.get("/riesgo-desercion/alto")
async def get_alto_riesgo():
    """Lista alumnos en riesgo ALTO (score >= 70)."""
    neo4j = await get_neo4j_client()
    alumnos = await obtener_alumnos_alto_riesgo(neo4j)
    
    return {
        "total": len(alumnos),
        "alumnos_alto_riesgo": alumnos
    }


@router.get("/riesgo-desercion/estadisticas")
async def get_estadisticas_riesgo():
    """Estadísticas agregadas de riesgo."""
    neo4j = await get_neo4j_client()
    stats = await obtener_estadisticas_riesgo(neo4j)
    
    return {"estadisticas": stats}


# ============== ENDPOINTS CAJA ==============

@router.get("/proyeccion-caja")
async def get_proyeccion_caja(
    dias: int = Query(90, description="Días a proyectar", ge=7, le=365)
):
    """
    Proyección de flujo de caja para los próximos N días.
    Considera probabilidad de pago según perfil del responsable.
    """
    neo4j = await get_neo4j_client()
    proyeccion = await proyectar_caja(neo4j, dias=dias)
    
    return {"proyeccion": proyeccion}


@router.get("/vencimientos-proximos")
async def get_vencimientos_proximos(
    dias: int = Query(7, description="Días hacia adelante", ge=1, le=30)
):
    """Cuotas próximas a vencer."""
    neo4j = await get_neo4j_client()
    vencimientos = await obtener_vencimientos_proximos(neo4j, dias=dias)
    
    return {
        "total": len(vencimientos),
        "dias_consultados": dias,
        "vencimientos": vencimientos
    }


@router.get("/deuda-por-grado")
async def get_deuda_por_grado():
    """Deuda agregada por grado."""
    neo4j = await get_neo4j_client()
    deuda = await obtener_deuda_por_grado(neo4j)
    
    return {"deuda_por_grado": deuda}


# ============== ENDPOINTS PATRONES ==============

@router.get("/patrones")
async def get_patrones():
    """Detecta patrones de comportamiento en el grafo."""
    neo4j = await get_neo4j_client()
    patrones = await detectar_patrones(neo4j)
    
    return {"patrones": patrones}


@router.get("/clusters")
async def get_clusters():
    """Obtiene clusters de comportamiento con descripciones LLM."""
    neo4j = await get_neo4j_client()
    clusters = await obtener_clusters(neo4j)
    
    return {
        "total": len(clusters),
        "clusters": clusters
    }


# ============== ENDPOINTS INSIGHTS LLM ==============

@router.get("/resumen-ejecutivo")
async def get_resumen_ejecutivo():
    """
    Genera resumen ejecutivo con LLM en tiempo real.
    Incluye métricas clave y análisis.
    """
    neo4j = await get_neo4j_client()
    resumen = await generar_resumen_ejecutivo(neo4j)
    
    return resumen


@router.get("/insights-predictivos")
async def get_insights_predictivos():
    """Obtiene últimos insights generados por LLM."""
    neo4j = await get_neo4j_client()
    insights = await obtener_insights_almacenados(neo4j)
    
    return insights


@router.get("/recomendaciones/{responsable_id}")
async def get_recomendaciones(responsable_id: str):
    """
    Genera recomendaciones personalizadas para un responsable.
    """
    neo4j = await get_neo4j_client()
    recomendaciones = await generar_recomendaciones_personalizadas(
        neo4j, responsable_id
    )
    
    if "error" in recomendaciones:
        raise HTTPException(status_code=404, detail=recomendaciones["error"])
    
    return recomendaciones


# ============== ENDPOINTS ETL ==============

@router.post("/etl/sync-erp", response_model=ETLResponse)
async def trigger_sync_erp(background_tasks: BackgroundTasks):
    """
    Dispara sincronización desde ERP Mock.
    Se ejecuta en background.
    """
    async def _sync():
        neo4j = await get_neo4j_client()
        etl = ETLFromERP(neo4j)
        return await etl.sync_all()
    
    background_tasks.add_task(_sync)
    
    return ETLResponse(
        status="accepted",
        message="Sincronización ERP iniciada en background"
    )


@router.post("/etl/sync-gestor", response_model=ETLResponse)
async def trigger_sync_gestor(background_tasks: BackgroundTasks):
    """
    Dispara sincronización desde Gestor WS.
    Se ejecuta en background.
    """
    async def _sync():
        neo4j = await get_neo4j_client()
        etl = ETLFromGestor(neo4j)
        return await etl.sync_all()
    
    background_tasks.add_task(_sync)
    
    return ETLResponse(
        status="accepted",
        message="Sincronización Gestor WS iniciada en background"
    )


@router.post("/etl/enrich-llm", response_model=ETLResponse)
async def trigger_llm_enrichment(background_tasks: BackgroundTasks):
    """
    Dispara enriquecimiento con LLM.
    Clasifica perfiles, genera clusters e insights.
    """
    async def _enrich():
        neo4j = await get_neo4j_client()
        enrichment = LLMEnrichment(neo4j)
        return await enrichment.enrich_all()
    
    background_tasks.add_task(_enrich)
    
    provider_info = get_provider_info()
    
    return ETLResponse(
        status="accepted",
        message=f"Enriquecimiento LLM iniciado ({provider_info['provider']}/{provider_info['model']})"
    )


@router.post("/etl/full")
async def trigger_full_etl(background_tasks: BackgroundTasks):
    """
    Dispara ETL completo: ERP + Gestor + LLM.
    """
    async def _full_etl():
        neo4j = await get_neo4j_client()
        
        results = {}
        
        # 1. ERP
        etl_erp = ETLFromERP(neo4j)
        results["erp"] = await etl_erp.sync_all()
        
        # 2. Gestor
        etl_gestor = ETLFromGestor(neo4j)
        results["gestor"] = await etl_gestor.sync_all()
        
        # 3. LLM
        enrichment = LLMEnrichment(neo4j)
        results["llm"] = await enrichment.enrich_all()
        
        return results
    
    background_tasks.add_task(_full_etl)
    
    return ETLResponse(
        status="accepted",
        message="ETL completo iniciado en background"
    )


# ============== ENDPOINTS STATUS ==============

@router.get("/status/grafo")
async def get_grafo_status():
    """Estado del Knowledge Graph."""
    neo4j = await get_neo4j_client()
    
    try:
        # Conteo de nodos
        nodos = await neo4j.execute("""
            MATCH (n)
            WITH labels(n)[0] as label, count(n) as count
            RETURN label, count
            ORDER BY count DESC
        """)
        
        # Conteo de relaciones
        relaciones = await neo4j.execute("""
            MATCH ()-[r]->()
            WITH type(r) as tipo, count(r) as count
            RETURN tipo, count
            ORDER BY count DESC
        """)
        
        return {
            "status": "connected",
            "nodos": {r["label"]: r["count"] for r in nodos},
            "relaciones": {r["tipo"]: r["count"] for r in relaciones},
            "total_nodos": sum(r["count"] for r in nodos),
            "total_relaciones": sum(r["count"] for r in relaciones)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/status/llm")
async def get_llm_status():
    """Estado de la configuración LLM."""
    info = get_provider_info()
    
    return {
        "provider": info["provider"],
        "model": info["model"],
        "temperature": info["temperature"],
        "max_tokens": info["max_tokens"],
        "available_providers": info["available_providers"]
    }


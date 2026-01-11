"""
Celery scheduler para tareas ETL periódicas.
"""
import logging
import asyncio
from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

# Crear instancia de Celery
celery_app = Celery(
    'knowledge_graph',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configuración
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Argentina/Buenos_Aires',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hora máximo por tarea
)


def run_async(coro):
    """Helper para ejecutar corrutinas en Celery."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name='etl_nocturno')
def etl_nocturno():
    """
    ETL completo cada noche a las 2 AM.
    Sincroniza ERP + Gestor WS y enriquece con LLM.
    """
    logger.info("🌙 Iniciando ETL nocturno...")
    
    async def _run():
        from app.neo4j_client import get_neo4j_client
        from app.etl.sync_from_erp import ETLFromERP
        from app.etl.sync_from_gestor import ETLFromGestor
        from app.etl.llm_enrichment import LLMEnrichment
        from app.llm.factory import validate_llm_config
        
        # Validar LLM
        validate_llm_config()
        
        # Obtener cliente Neo4j
        neo4j = await get_neo4j_client()
        
        results = {
            "erp": {},
            "gestor": {},
            "llm": {}
        }
        
        try:
            # 1. Sincronizar desde ERP
            etl_erp = ETLFromERP(neo4j)
            results["erp"] = await etl_erp.sync_all()
            
            # 2. Sincronizar desde Gestor WS
            etl_gestor = ETLFromGestor(neo4j)
            results["gestor"] = await etl_gestor.sync_all()
            
            # 3. Enriquecer con LLM
            llm_enrich = LLMEnrichment(neo4j)
            results["llm"] = await llm_enrich.enrich_all()
            
            logger.info(f"✅ ETL nocturno completado: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en ETL nocturno: {e}")
            raise
    
    return run_async(_run())


@celery_app.task(name='sync_erp_incremental')
def sync_erp_incremental():
    """
    Sincronización incremental desde ERP cada 6 horas.
    Solo sincroniza cambios recientes.
    """
    logger.info("🔄 Sincronización incremental ERP...")
    
    async def _run():
        from app.neo4j_client import get_neo4j_client
        from app.etl.sync_from_erp import ETLFromERP
        
        neo4j = await get_neo4j_client()
        etl_erp = ETLFromERP(neo4j)
        
        # Solo cuotas y pagos (cambian más frecuentemente)
        results = {
            "cuotas": await etl_erp.sync_cuotas(),
            "pagos": await etl_erp.sync_pagos()
        }
        
        logger.info(f"✅ Sync incremental completado: {results}")
        return results
    
    return run_async(_run())


@celery_app.task(name='calcular_scores_riesgo')
def calcular_scores_riesgo():
    """
    Recalcula scores de riesgo cada 6 horas.
    """
    logger.info("📊 Calculando scores de riesgo...")
    
    async def _run():
        from app.neo4j_client import get_neo4j_client
        from app.queries.riesgo_desercion import calcular_score_riesgo_desercion
        
        neo4j = await get_neo4j_client()
        scores = await calcular_score_riesgo_desercion(neo4j)
        
        # Alertar si hay nuevos alumnos en riesgo ALTO
        alto_riesgo = [s for s in scores if s.get('nivel_riesgo') == 'ALTO']
        
        if alto_riesgo:
            logger.warning(f"⚠️ {len(alto_riesgo)} alumnos en riesgo ALTO detectados")
        
        return {
            "total_evaluados": len(scores),
            "alto_riesgo": len(alto_riesgo),
            "scores": scores[:10]  # Top 10
        }
    
    return run_async(_run())


@celery_app.task(name='generar_resumen_semanal')
def generar_resumen_semanal():
    """
    Genera resumen ejecutivo semanal con LLM.
    """
    logger.info("📝 Generando resumen semanal...")
    
    async def _run():
        from app.neo4j_client import get_neo4j_client
        from app.queries.insights_llm import generar_resumen_ejecutivo
        
        neo4j = await get_neo4j_client()
        resumen = await generar_resumen_ejecutivo(neo4j)
        
        logger.info("✅ Resumen semanal generado")
        return resumen
    
    return run_async(_run())


@celery_app.task(name='actualizar_clusters')
def actualizar_clusters():
    """
    Actualiza clusters de comportamiento semanalmente.
    """
    logger.info("👥 Actualizando clusters...")
    
    async def _run():
        from app.neo4j_client import get_neo4j_client
        from app.etl.llm_enrichment import LLMEnrichment
        
        neo4j = await get_neo4j_client()
        enrichment = LLMEnrichment(neo4j)
        
        return await enrichment.generar_clusters_comportamiento()
    
    return run_async(_run())


# Configuración de schedule
celery_app.conf.beat_schedule = {
    'etl-nocturno': {
        'task': 'etl_nocturno',
        'schedule': crontab(hour=2, minute=0),  # 2 AM diario
    },
    'sync-erp-incremental': {
        'task': 'sync_erp_incremental',
        'schedule': crontab(minute=0, hour='*/6'),  # Cada 6 horas
    },
    'scores-riesgo': {
        'task': 'calcular_scores_riesgo',
        'schedule': crontab(minute=30, hour='*/6'),  # Cada 6 horas (offset 30min)
    },
    'resumen-semanal': {
        'task': 'generar_resumen_semanal',
        'schedule': crontab(day_of_week='monday', hour=8, minute=0),  # Lunes 8 AM
    },
    'actualizar-clusters': {
        'task': 'actualizar_clusters',
        'schedule': crontab(day_of_week='sunday', hour=3, minute=0),  # Domingo 3 AM
    },
}


"""
Queries y generación de insights con LLM.
"""
import json
import logging
from datetime import datetime
from typing import Any

from app.neo4j_client import Neo4jClient
from app.llm.factory import get_llm
from app.config import settings

logger = logging.getLogger(__name__)


async def generar_resumen_ejecutivo(neo4j: Neo4jClient) -> dict[str, Any]:
    """
    Genera un resumen ejecutivo usando LLM sobre los datos del grafo.
    
    Args:
        neo4j: Cliente Neo4j
        
    Returns:
        Diccionario con resumen ejecutivo
    """
    # 1. Obtener métricas clave del grafo
    metricas = await _obtener_metricas_grafo(neo4j)
    
    if not metricas:
        return {"error": "No hay datos suficientes"}
    
    # 2. Generar resumen con LLM
    llm = get_llm()
    
    prompt = f"""
Genera un resumen ejecutivo conciso para el director administrativo de un colegio:

MÉTRICAS ACTUALES DEL SISTEMA DE COBRANZA:
- Total de responsables: {metricas.get('total_responsables', 0)}
- Responsables en riesgo ALTO: {metricas.get('alto_riesgo', 0)} ({metricas.get('pct_alto_riesgo', 0):.1f}%)
- Responsables en riesgo MEDIO: {metricas.get('medio_riesgo', 0)}
- Perfil MOROSO: {metricas.get('morosos', 0)}
- Perfil PUNTUAL: {metricas.get('puntuales', 0)}
- Cuotas vencidas: {metricas.get('cuotas_vencidas', 0)}
- Monto total vencido: ${metricas.get('monto_vencido', 0):,.0f}

Genera un resumen con:
1. SITUACIÓN ACTUAL (2-3 oraciones)
2. PRINCIPALES RIESGOS (3 bullet points)
3. ACCIONES RECOMENDADAS (3 acciones priorizadas)

Tono: profesional, directo, accionable.
Máximo 200 palabras.
Responde en texto plano, no JSON.
"""
    
    try:
        response = await llm.ainvoke(prompt)
        resumen_texto = response.content
        
        return {
            "metricas": metricas,
            "resumen_ejecutivo": resumen_texto,
            "generado_por": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generando resumen ejecutivo: {e}")
        return {
            "metricas": metricas,
            "error": str(e)
        }


async def _obtener_metricas_grafo(neo4j: Neo4jClient) -> dict[str, Any]:
    """Obtiene métricas agregadas del grafo."""
    query = """
    MATCH (r:Responsable)
    WITH count(r) as total_responsables,
         count(CASE WHEN r.nivel_riesgo = 'ALTO' THEN 1 END) as alto_riesgo,
         count(CASE WHEN r.nivel_riesgo = 'MEDIO' THEN 1 END) as medio_riesgo,
         count(CASE WHEN r.perfil_pagador = 'MOROSO' THEN 1 END) as morosos,
         count(CASE WHEN r.perfil_pagador = 'PUNTUAL' THEN 1 END) as puntuales
    
    OPTIONAL MATCH (c:Cuota)
    WHERE c.estado = 'vencida'
    
    WITH total_responsables, alto_riesgo, medio_riesgo, morosos, puntuales,
         count(c) as cuotas_vencidas,
         coalesce(sum(c.monto), 0) as monto_vencido
    
    RETURN total_responsables,
           alto_riesgo,
           medio_riesgo,
           morosos,
           puntuales,
           cuotas_vencidas,
           monto_vencido,
           CASE WHEN total_responsables > 0 
                THEN toFloat(alto_riesgo) / total_responsables * 100 
                ELSE 0 
           END as pct_alto_riesgo
    """
    
    try:
        results = await neo4j.execute(query)
        return results[0] if results else {}
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        return {}


async def obtener_insights_almacenados(neo4j: Neo4jClient) -> dict[str, Any]:
    """
    Obtiene los últimos insights predictivos almacenados.
    
    Returns:
        Diccionario con insights
    """
    query = """
    MATCH (i:InsightsPredictivos {id: 'latest'})
    RETURN i.tendencias as tendencias,
           i.riesgos as riesgos,
           i.oportunidades as oportunidades,
           i.acciones as acciones,
           i.metricas as metricas,
           i.generado_por_llm as generado_por,
           i.timestamp as timestamp
    """
    
    try:
        results = await neo4j.execute(query)
        if results:
            r = results[0]
            return {
                "tendencias": r.get("tendencias", []),
                "riesgos": r.get("riesgos", []),
                "oportunidades": r.get("oportunidades", []),
                "acciones": r.get("acciones", []),
                "metricas": json.loads(r.get("metricas", "{}")),
                "generado_por": r.get("generado_por"),
                "timestamp": r.get("timestamp")
            }
        return {"error": "No hay insights disponibles"}
    except Exception as e:
        logger.error(f"Error obteniendo insights: {e}")
        return {"error": str(e)}


async def generar_recomendaciones_personalizadas(
    neo4j: Neo4jClient,
    responsable_id: str
) -> dict[str, Any]:
    """
    Genera recomendaciones personalizadas para un responsable específico.
    
    Args:
        neo4j: Cliente Neo4j
        responsable_id: ID del responsable
        
    Returns:
        Diccionario con recomendaciones
    """
    # Obtener datos del responsable
    query = """
    MATCH (r:Responsable {erp_id: $responsable_id})
    OPTIONAL MATCH (r)-[:RESPONSABLE_DE]->(e:Estudiante)
    OPTIONAL MATCH (r)-[p:PAGO]->(c:Cuota)
    OPTIONAL MATCH (r)-[:PERTENECE_A]->(cluster:ClusterComportamiento)
    
    RETURN r.nombre + ' ' + r.apellido as nombre,
           r.perfil_pagador as perfil,
           r.nivel_riesgo as riesgo,
           r.patrones_detectados as patrones,
           collect(DISTINCT e.nombre + ' ' + e.apellido) as hijos,
           count(DISTINCT p) as pagos_realizados,
           avg(p.dias_demora) as demora_promedio,
           cluster.recomendaciones as recomendaciones_cluster
    """
    
    try:
        results = await neo4j.execute(query, {"responsable_id": responsable_id})
        
        if not results:
            return {"error": "Responsable no encontrado"}
        
        data = results[0]
        
        # Si ya tiene recomendaciones del cluster, usarlas
        if data.get("recomendaciones_cluster"):
            return {
                "responsable": data["nombre"],
                "perfil": data["perfil"],
                "recomendaciones": data["recomendaciones_cluster"],
                "fuente": "cluster"
            }
        
        # Si no, generar con LLM
        llm = get_llm()
        prompt = f"""
Genera 3 recomendaciones específicas para mejorar la comunicación con este responsable:

- Nombre: {data['nombre']}
- Perfil de pago: {data['perfil']}
- Nivel de riesgo: {data['riesgo']}
- Hijos: {', '.join(data['hijos']) if data['hijos'] else 'Sin datos'}
- Pagos realizados: {data['pagos_realizados']}
- Demora promedio: {data['demora_promedio']:.1f if data['demora_promedio'] else 0} días

Responde SOLO con un JSON válido:
{{"recomendaciones": ["recomendación 1", "recomendación 2", "recomendación 3"]}}
"""
        
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # Limpiar respuesta
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        recs = json.loads(content)
        
        return {
            "responsable": data["nombre"],
            "perfil": data["perfil"],
            "recomendaciones": recs.get("recomendaciones", []),
            "fuente": "llm"
        }
        
    except Exception as e:
        logger.error(f"Error generando recomendaciones: {e}")
        return {"error": str(e)}


"""
Queries para cálculo de riesgo de deserción.
"""
import logging
from typing import Any

from app.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


async def calcular_score_riesgo_desercion(
    neo4j: Neo4jClient,
    umbral_minimo: int = 40
) -> list[dict[str, Any]]:
    """
    Calcula score de riesgo (0-100) para cada estudiante.
    Enriquecido con clasificación LLM del responsable.
    
    Factores de riesgo:
    - Cuotas vencidas (20 pts c/u)
    - Notificaciones ignoradas (15 pts c/u)
    - Cuotas vencidas de hermanos (10 pts c/u)
    - Nivel de riesgo del responsable (0-30 pts)
    - Tickets de soporte (5 pts c/u)
    
    Args:
        neo4j: Cliente Neo4j
        umbral_minimo: Score mínimo para incluir en resultados
        
    Returns:
        Lista de estudiantes con score de riesgo
    """
    query = """
    // Obtener estudiantes con cuotas vencidas
    MATCH (e:Estudiante)-[:DEBE]->(c:Cuota)
    WHERE c.estado IN ['vencida', 'pendiente'] 
      AND c.fecha_vencimiento < date()
    
    WITH e, count(c) as cuotas_vencidas, sum(c.monto) as deuda_vencida
    
    // Obtener responsable
    MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e)
    
    // Notificaciones ignoradas
    OPTIONAL MATCH (r)-[ig:IGNORO_NOTIFICACION]->(:Cuota)
    WITH e, r, cuotas_vencidas, deuda_vencida, count(ig) as notif_ignoradas
    
    // Tickets creados
    OPTIONAL MATCH (r)-[:CREO_TICKET]->(t:Ticket)
    WITH e, r, cuotas_vencidas, deuda_vencida, notif_ignoradas, count(t) as tickets
    
    // Hermanos en mora
    OPTIONAL MATCH (r)-[:RESPONSABLE_DE]->(hermano:Estudiante)
    WHERE hermano <> e
    OPTIONAL MATCH (hermano)-[:DEBE]->(c_hermano:Cuota)
    WHERE c_hermano.estado = 'vencida'
    
    WITH e, r, cuotas_vencidas, deuda_vencida, notif_ignoradas, tickets,
         count(c_hermano) as cuotas_vencidas_hermanos
    
    // Calcular score con factores enriquecidos por LLM
    WITH e, r,
         cuotas_vencidas,
         deuda_vencida,
         notif_ignoradas,
         tickets,
         cuotas_vencidas_hermanos,
         (cuotas_vencidas * 20) +
         (notif_ignoradas * 15) +
         (cuotas_vencidas_hermanos * 10) +
         (tickets * 5) +
         (CASE r.nivel_riesgo 
            WHEN 'ALTO' THEN 30
            WHEN 'MEDIO' THEN 15
            ELSE 0
          END) as score_riesgo
    
    WHERE score_riesgo >= $umbral_minimo
    
    RETURN e.erp_id as alumno_id,
           e.nombre + ' ' + e.apellido as alumno_nombre,
           e.grado as grado,
           r.erp_id as responsable_id,
           r.nombre + ' ' + r.apellido as responsable_nombre,
           r.whatsapp as responsable_whatsapp,
           r.perfil_pagador as perfil_responsable,
           r.nivel_riesgo as nivel_riesgo_responsable,
           r.patrones_detectados as patrones,
           cuotas_vencidas,
           deuda_vencida,
           notif_ignoradas,
           tickets,
           cuotas_vencidas_hermanos,
           score_riesgo,
           CASE
             WHEN score_riesgo >= 70 THEN 'ALTO'
             WHEN score_riesgo >= 40 THEN 'MEDIO'
             ELSE 'BAJO'
           END as nivel_riesgo
    ORDER BY score_riesgo DESC
    """
    
    try:
        results = await neo4j.execute(query, {"umbral_minimo": umbral_minimo})
        logger.info(f"Score de riesgo calculado para {len(results)} estudiantes")
        return results
    except Exception as e:
        logger.error(f"Error calculando scores de riesgo: {e}")
        return []


async def obtener_alumnos_alto_riesgo(neo4j: Neo4jClient) -> list[dict[str, Any]]:
    """
    Obtiene alumnos en riesgo ALTO con información completa.
    
    Returns:
        Lista de alumnos en riesgo alto
    """
    return await calcular_score_riesgo_desercion(neo4j, umbral_minimo=70)


async def obtener_estadisticas_riesgo(neo4j: Neo4jClient) -> dict[str, Any]:
    """
    Obtiene estadísticas agregadas de riesgo.
    
    Returns:
        Diccionario con estadísticas
    """
    query = """
    MATCH (e:Estudiante)-[:DEBE]->(c:Cuota)
    WHERE c.estado = 'vencida'
    
    WITH e, count(c) as cuotas_vencidas
    
    MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e)
    
    RETURN count(DISTINCT e) as total_alumnos_deuda,
           sum(cuotas_vencidas) as total_cuotas_vencidas,
           count(DISTINCT CASE WHEN r.nivel_riesgo = 'ALTO' THEN e END) as alumnos_riesgo_alto,
           count(DISTINCT CASE WHEN r.nivel_riesgo = 'MEDIO' THEN e END) as alumnos_riesgo_medio,
           count(DISTINCT CASE WHEN r.nivel_riesgo = 'BAJO' THEN e END) as alumnos_riesgo_bajo
    """
    
    try:
        results = await neo4j.execute(query)
        return results[0] if results else {}
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de riesgo: {e}")
        return {}


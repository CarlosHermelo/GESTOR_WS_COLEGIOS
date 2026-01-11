"""
Consultas para detección de patrones en el Knowledge Graph.
"""
import logging
from typing import Any

from app.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


async def detectar_patrones(neo4j: Neo4jClient) -> dict[str, Any]:
    """
    Detecta todos los patrones principales en el grafo.
    
    Returns:
        Diccionario con diferentes tipos de patrones
    """
    patrones = {}
    
    # Patrones de morosidad
    patrones["morosidad"] = await detectar_patrones_morosidad(neo4j)
    
    # Familias con múltiples hijos en mora
    patrones["familias_problema"] = await detectar_familias_problema(neo4j)
    
    # Grados críticos
    patrones["grados_criticos"] = await detectar_grados_criticos(neo4j)
    
    # Resumen
    patrones["resumen"] = await obtener_resumen_patrones(neo4j)
    
    return patrones


async def obtener_clusters(neo4j: Neo4jClient) -> list[dict]:
    """
    Obtiene clusters de comportamiento con descripciones LLM.
    
    Returns:
        Lista de clusters
    """
    clusters = await neo4j.execute("""
        MATCH (c:ClusterComportamiento)
        
        OPTIONAL MATCH (r:Responsable)-[:PERTENECE_A]->(c)
        
        WITH c, count(r) as miembros_actuales
        
        RETURN c.tipo as tipo,
               c.perfil as perfil,
               c.riesgo as riesgo,
               c.descripcion as descripcion,
               c.caracteristicas as caracteristicas,
               c.recomendaciones as recomendaciones,
               c.estrategia as estrategia,
               miembros_actuales as cantidad,
               c.generado_por_llm as generado_por,
               c.ultima_actualizacion as actualizado
        
        ORDER BY miembros_actuales DESC
    """)
    
    return clusters


async def detectar_patrones_morosidad(neo4j: Neo4jClient) -> list[dict]:
    """
    Detecta patrones de morosidad recurrente.
    Identifica responsables con comportamiento repetitivo de mora.
    
    Returns:
        Lista de patrones detectados
    """
    patrones = await neo4j.execute("""
        MATCH (r:Responsable)-[p:PAGO]->(c:Cuota)
        
        WITH r,
             count(p) as total_pagos,
             avg(p.dias_demora) as demora_promedio,
             collect(p.dias_demora) as demoras,
             stdev(p.dias_demora) as variabilidad
        
        WHERE total_pagos >= 3
        
        WITH r, total_pagos, demora_promedio, demoras, variabilidad,
             CASE
                 WHEN demora_promedio > 30 AND variabilidad < 10 THEN 'MOROSO_CRONICO'
                 WHEN demora_promedio > 15 AND variabilidad > 15 THEN 'PAGADOR_IRREGULAR'
                 WHEN demora_promedio <= 5 THEN 'PAGADOR_PUNTUAL'
                 ELSE 'PAGADOR_PROMEDIO'
             END as patron_detectado
        
        WHERE patron_detectado IN ['MOROSO_CRONICO', 'PAGADOR_IRREGULAR']
        
        RETURN r.erp_id as responsable_id,
               r.nombre + ' ' + r.apellido as nombre,
               r.whatsapp as whatsapp,
               total_pagos,
               round(demora_promedio, 1) as demora_promedio,
               round(variabilidad, 1) as variabilidad,
               patron_detectado,
               r.perfil_pagador as perfil_actual
        
        ORDER BY demora_promedio DESC
        LIMIT 50
    """)
    
    return patrones


async def detectar_riesgo_abandono(neo4j: Neo4jClient) -> list[dict]:
    """
    Detecta estudiantes con alto riesgo de abandono escolar.
    Considera múltiples factores: mora, interacciones, tickets.
    
    Returns:
        Lista de estudiantes en riesgo
    """
    riesgo = await neo4j.execute("""
        MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e:Estudiante)
        MATCH (e)-[:DEBE]->(c:Cuota)
        
        WHERE c.estado = 'vencida'
        
        OPTIONAL MATCH (r)-[ig:IGNORO_NOTIFICACION]->(:Cuota)
        OPTIONAL MATCH (r)-[:CREO_TICKET]->(t:Ticket)
        
        WITH e, r,
             count(DISTINCT c) as cuotas_vencidas,
             sum(c.monto) as deuda_total,
             count(DISTINCT ig) as notif_ignoradas,
             count(DISTINCT t) as tickets
        
        WITH e, r, cuotas_vencidas, deuda_total, notif_ignoradas, tickets,
             (cuotas_vencidas * 20) + 
             (notif_ignoradas * 15) +
             (CASE WHEN r.nivel_riesgo = 'ALTO' THEN 30 
                   WHEN r.nivel_riesgo = 'MEDIO' THEN 15 
                   ELSE 0 END) as score_riesgo
        
        WHERE score_riesgo >= 50
        
        RETURN e.erp_id as estudiante_id,
               e.nombre + ' ' + e.apellido as estudiante,
               e.grado as grado,
               r.erp_id as responsable_id,
               r.nombre + ' ' + r.apellido as responsable,
               r.whatsapp as whatsapp,
               r.perfil_pagador as perfil,
               cuotas_vencidas,
               round(deuda_total, 2) as deuda_total,
               notif_ignoradas,
               tickets,
               score_riesgo,
               CASE
                   WHEN score_riesgo >= 80 THEN 'CRITICO'
                   WHEN score_riesgo >= 60 THEN 'ALTO'
                   ELSE 'MODERADO'
               END as nivel_riesgo_abandono
        
        ORDER BY score_riesgo DESC
        LIMIT 100
    """)
    
    return riesgo


async def detectar_familias_problema(neo4j: Neo4jClient) -> list[dict]:
    """
    Detecta familias con múltiples hijos en mora.
    (Patrón: hermanos en mora simultáneamente)
    
    Returns:
        Lista de familias con problemas de pago
    """
    familias = await neo4j.execute("""
        MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e:Estudiante)-[:DEBE]->(c:Cuota)
        WHERE c.estado = 'vencida'
        
        WITH r,
             count(DISTINCT e) as hijos_en_mora,
             collect(DISTINCT e.nombre + ' ' + e.apellido) as estudiantes,
             collect(DISTINCT e.grado) as grados,
             count(c) as cuotas_vencidas_total,
             sum(c.monto) as deuda_familiar_total
        
        WHERE hijos_en_mora > 1
        
        RETURN r.erp_id as responsable_id,
               r.nombre + ' ' + r.apellido as responsable,
               r.whatsapp as whatsapp,
               r.perfil_pagador as perfil,
               hijos_en_mora,
               estudiantes,
               grados,
               cuotas_vencidas_total,
               round(deuda_familiar_total, 2) as deuda_familiar_total
        
        ORDER BY deuda_familiar_total DESC
        LIMIT 50
    """)
    
    return familias


async def detectar_grados_criticos(neo4j: Neo4jClient) -> list[dict]:
    """
    Identifica grados con mayor concentración de morosidad.
    
    Returns:
        Lista de grados ordenados por criticidad
    """
    grados = await neo4j.execute("""
        MATCH (e:Estudiante)-[:CURSA]->(g:Grado)
        MATCH (e)-[:DEBE]->(c:Cuota)
        
        WITH g,
             count(DISTINCT e) as total_estudiantes,
             count(DISTINCT CASE WHEN c.estado = 'vencida' THEN e END) as estudiantes_morosos,
             count(c) as total_cuotas,
             count(CASE WHEN c.estado = 'vencida' THEN 1 END) as cuotas_vencidas,
             sum(c.monto) as monto_total,
             sum(CASE WHEN c.estado = 'vencida' THEN c.monto ELSE 0 END) as monto_vencido
        
        WITH g, total_estudiantes, estudiantes_morosos, total_cuotas,
             cuotas_vencidas, monto_total, monto_vencido,
             toFloat(estudiantes_morosos) / toFloat(total_estudiantes) * 100 as pct_morosos,
             toFloat(monto_vencido) / toFloat(monto_total) * 100 as pct_mora
        
        RETURN g.nombre as grado,
               total_estudiantes,
               estudiantes_morosos,
               round(pct_morosos, 1) as pct_estudiantes_morosos,
               cuotas_vencidas,
               round(monto_vencido, 2) as monto_vencido,
               round(pct_mora, 1) as pct_morosidad,
               CASE
                   WHEN pct_morosos > 50 THEN 'CRITICO'
                   WHEN pct_morosos > 30 THEN 'ALTO'
                   WHEN pct_morosos > 15 THEN 'MODERADO'
                   ELSE 'NORMAL'
               END as nivel_alerta
        
        ORDER BY pct_morosos DESC
    """)
    
    return grados


async def detectar_tendencias_temporales(neo4j: Neo4jClient) -> dict[str, Any]:
    """
    Analiza tendencias temporales de pagos y morosidad.
    
    Returns:
        Diccionario con análisis temporal
    """
    # Pagos por mes (últimos 6 meses)
    pagos_mensual = await neo4j.execute("""
        MATCH (r:Responsable)-[p:PAGO]->(c:Cuota)
        WHERE p.fecha >= datetime() - duration('P6M')
        
        WITH date.truncate('month', date(p.fecha)) as mes,
             count(p) as cantidad_pagos,
             sum(p.monto) as monto_cobrado,
             avg(p.dias_demora) as demora_promedio
        
        RETURN mes,
               cantidad_pagos,
               round(monto_cobrado, 2) as monto_cobrado,
               round(demora_promedio, 1) as demora_promedio
        
        ORDER BY mes ASC
    """)
    
    # Nuevas cuotas vencidas por mes
    vencimientos_mensual = await neo4j.execute("""
        MATCH (c:Cuota)
        WHERE c.estado = 'vencida'
          AND c.fecha_vencimiento >= date() - duration('P6M')
        
        WITH date.truncate('month', c.fecha_vencimiento) as mes,
             count(c) as nuevas_vencidas,
             sum(c.monto) as monto_vencido
        
        RETURN mes,
               nuevas_vencidas,
               round(monto_vencido, 2) as monto_vencido
        
        ORDER BY mes ASC
    """)
    
    return {
        "pagos_mensual": pagos_mensual,
        "vencimientos_mensual": vencimientos_mensual
    }


async def obtener_resumen_patrones(neo4j: Neo4jClient) -> dict[str, Any]:
    """
    Obtiene resumen de patrones detectados.
    
    Returns:
        Diccionario con estadísticas de patrones
    """
    resumen = await neo4j.execute("""
        MATCH (r:Responsable)
        
        WITH count(r) as total_responsables,
             count(CASE WHEN r.perfil_pagador = 'MOROSO' THEN 1 END) as morosos,
             count(CASE WHEN r.perfil_pagador = 'EVENTUAL' THEN 1 END) as eventuales,
             count(CASE WHEN r.perfil_pagador = 'PUNTUAL' THEN 1 END) as puntuales,
             count(CASE WHEN r.perfil_pagador = 'NUEVO' THEN 1 END) as nuevos,
             count(CASE WHEN r.nivel_riesgo = 'ALTO' THEN 1 END) as alto_riesgo,
             count(CASE WHEN r.nivel_riesgo = 'MEDIO' THEN 1 END) as medio_riesgo,
             count(CASE WHEN r.nivel_riesgo = 'BAJO' THEN 1 END) as bajo_riesgo
        
        RETURN total_responsables, morosos, eventuales, puntuales, nuevos,
               alto_riesgo, medio_riesgo, bajo_riesgo
    """)
    
    clusters = await neo4j.execute("""
        MATCH (c:ClusterComportamiento)
        RETURN c.tipo as tipo,
               c.cantidad_miembros as cantidad,
               c.descripcion as descripcion
        ORDER BY c.cantidad_miembros DESC
    """)
    
    return {
        "perfiles": resumen[0] if resumen else {},
        "clusters": clusters
    }

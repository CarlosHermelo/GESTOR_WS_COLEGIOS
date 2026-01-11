"""
Consultas para proyección de caja y análisis financiero.
"""
import logging
from datetime import date, timedelta
from typing import Any

from app.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


async def proyectar_caja(neo4j: Neo4jClient, dias: int = 90) -> dict[str, Any]:
    """
    Proyecta ingresos esperados para los próximos N días.
    Considera el perfil de pagador para ajustar probabilidades.
    
    Args:
        neo4j: Cliente Neo4j
        dias: Días de proyección
    
    Returns:
        Diccionario con proyección detallada
    """
    fecha_limite = (date.today() + timedelta(days=dias)).isoformat()
    fecha_hoy = date.today().isoformat()
    
    # Obtener cuotas pendientes con perfil del responsable
    cuotas = await neo4j.execute(f"""
        MATCH (e:Estudiante)-[:DEBE]->(c:Cuota)
        MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e)
        
        WHERE c.estado IN ['pendiente', 'vencida']
          AND c.fecha_vencimiento <= date('{fecha_limite}')
        
        RETURN c.erp_id as cuota_id,
               c.monto as monto,
               c.fecha_vencimiento as fecha_vencimiento,
               c.estado as estado,
               e.nombre + ' ' + e.apellido as estudiante,
               e.grado as grado,
               r.perfil_pagador as perfil,
               r.nivel_riesgo as riesgo
    """)
    
    # Calcular proyección ajustada por perfil
    proyeccion = {
        "fecha_inicio": fecha_hoy,
        "fecha_fin": fecha_limite,
        "dias": dias,
        "cuotas_analizadas": len(cuotas),
        "monto_total_pendiente": 0,
        "monto_esperado_optimista": 0,
        "monto_esperado_realista": 0,
        "monto_esperado_pesimista": 0,
        "por_semana": [],
        "por_perfil": {}
    }
    
    # Probabilidades de cobro por perfil
    prob_cobro = {
        "PUNTUAL": {"optimista": 0.95, "realista": 0.85, "pesimista": 0.75},
        "EVENTUAL": {"optimista": 0.75, "realista": 0.55, "pesimista": 0.35},
        "MOROSO": {"optimista": 0.45, "realista": 0.25, "pesimista": 0.10},
        "NUEVO": {"optimista": 0.70, "realista": 0.50, "pesimista": 0.30},
        None: {"optimista": 0.60, "realista": 0.40, "pesimista": 0.20}
    }
    
    for cuota in cuotas:
        monto = float(cuota["monto"] or 0)
        perfil = cuota.get("perfil")
        probs = prob_cobro.get(perfil, prob_cobro[None])
        
        proyeccion["monto_total_pendiente"] += monto
        proyeccion["monto_esperado_optimista"] += monto * probs["optimista"]
        proyeccion["monto_esperado_realista"] += monto * probs["realista"]
        proyeccion["monto_esperado_pesimista"] += monto * probs["pesimista"]
        
        # Agrupar por perfil
        if perfil not in proyeccion["por_perfil"]:
            proyeccion["por_perfil"][perfil] = {
                "cantidad": 0,
                "monto_total": 0,
                "monto_esperado": 0
            }
        proyeccion["por_perfil"][perfil]["cantidad"] += 1
        proyeccion["por_perfil"][perfil]["monto_total"] += monto
        proyeccion["por_perfil"][perfil]["monto_esperado"] += monto * probs["realista"]
    
    # Redondear valores
    for key in ["monto_total_pendiente", "monto_esperado_optimista", 
                "monto_esperado_realista", "monto_esperado_pesimista"]:
        proyeccion[key] = round(proyeccion[key], 2)
    
    for perfil_data in proyeccion["por_perfil"].values():
        perfil_data["monto_total"] = round(perfil_data["monto_total"], 2)
        perfil_data["monto_esperado"] = round(perfil_data["monto_esperado"], 2)
    
    return proyeccion


async def obtener_vencimientos_proximos(
    neo4j: Neo4jClient, 
    dias: int = 7
) -> list[dict]:
    """
    Obtiene cuotas que vencen en los próximos N días.
    
    Args:
        neo4j: Cliente Neo4j
        dias: Días hacia adelante
    
    Returns:
        Lista de cuotas próximas a vencer
    """
    fecha_limite = (date.today() + timedelta(days=dias)).isoformat()
    fecha_hoy = date.today().isoformat()
    
    vencimientos = await neo4j.execute(f"""
        MATCH (e:Estudiante)-[:DEBE]->(c:Cuota)
        MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e)
        
        WHERE c.estado = 'pendiente'
          AND c.fecha_vencimiento >= date('{fecha_hoy}')
          AND c.fecha_vencimiento <= date('{fecha_limite}')
        
        RETURN c.erp_id as cuota_id,
               c.monto as monto,
               c.fecha_vencimiento as fecha_vencimiento,
               c.numero_cuota as numero_cuota,
               e.erp_id as estudiante_id,
               e.nombre + ' ' + e.apellido as estudiante,
               e.grado as grado,
               r.erp_id as responsable_id,
               r.nombre + ' ' + r.apellido as responsable,
               r.whatsapp as whatsapp,
               r.perfil_pagador as perfil,
               r.nivel_riesgo as riesgo
        
        ORDER BY c.fecha_vencimiento ASC
    """)
    
    return vencimientos


async def obtener_deuda_por_grado(neo4j: Neo4jClient) -> list[dict]:
    """
    Agrupa la deuda pendiente por grado escolar.
    
    Returns:
        Lista con deuda agrupada por grado
    """
    deuda = await neo4j.execute("""
        MATCH (e:Estudiante)-[:DEBE]->(c:Cuota)
        WHERE c.estado IN ['pendiente', 'vencida']
        
        WITH e.grado as grado,
             count(DISTINCT e) as estudiantes,
             count(c) as cuotas_pendientes,
             sum(c.monto) as deuda_total,
             count(CASE WHEN c.estado = 'vencida' THEN 1 END) as cuotas_vencidas,
             sum(CASE WHEN c.estado = 'vencida' THEN c.monto ELSE 0 END) as deuda_vencida
        
        RETURN grado,
               estudiantes,
               cuotas_pendientes,
               round(deuda_total, 2) as deuda_total,
               cuotas_vencidas,
               round(deuda_vencida, 2) as deuda_vencida
        
        ORDER BY deuda_total DESC
    """)
    
    return deuda


async def obtener_resumen_financiero(neo4j: Neo4jClient) -> dict[str, Any]:
    """
    Obtiene resumen financiero general.
    
    Returns:
        Diccionario con métricas financieras
    """
    resumen = await neo4j.execute("""
        MATCH (c:Cuota)
        
        WITH count(c) as total_cuotas,
             sum(c.monto) as monto_total,
             count(CASE WHEN c.estado = 'pagada' THEN 1 END) as cuotas_pagadas,
             sum(CASE WHEN c.estado = 'pagada' THEN c.monto ELSE 0 END) as monto_cobrado,
             count(CASE WHEN c.estado = 'pendiente' THEN 1 END) as cuotas_pendientes,
             sum(CASE WHEN c.estado = 'pendiente' THEN c.monto ELSE 0 END) as monto_pendiente,
             count(CASE WHEN c.estado = 'vencida' THEN 1 END) as cuotas_vencidas,
             sum(CASE WHEN c.estado = 'vencida' THEN c.monto ELSE 0 END) as monto_vencido
        
        RETURN total_cuotas,
               round(monto_total, 2) as monto_total,
               cuotas_pagadas,
               round(monto_cobrado, 2) as monto_cobrado,
               cuotas_pendientes,
               round(monto_pendiente, 2) as monto_pendiente,
               cuotas_vencidas,
               round(monto_vencido, 2) as monto_vencido
    """)
    
    if resumen:
        r = resumen[0]
        r["tasa_cobranza"] = round(
            (r["monto_cobrado"] / r["monto_total"] * 100) if r["monto_total"] > 0 else 0,
            2
        )
        r["tasa_morosidad"] = round(
            (r["monto_vencido"] / r["monto_total"] * 100) if r["monto_total"] > 0 else 0,
            2
        )
        return r
    
    return {}

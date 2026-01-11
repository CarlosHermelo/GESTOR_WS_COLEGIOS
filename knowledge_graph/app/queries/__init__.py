"""
Queries analíticas Cypher para el Knowledge Graph.
"""
from app.queries.riesgo_desercion import calcular_score_riesgo_desercion
from app.queries.proyeccion_caja import proyectar_caja
from app.queries.patrones import detectar_patrones
from app.queries.insights_llm import generar_resumen_ejecutivo

__all__ = [
    "calcular_score_riesgo_desercion",
    "proyectar_caja",
    "detectar_patrones",
    "generar_resumen_ejecutivo"
]


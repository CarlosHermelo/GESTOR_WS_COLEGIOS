"""
Enriquecimiento del Knowledge Graph con LLM.
Clasifica perfiles, genera clusters e insights predictivos.
"""
import json
import logging
from datetime import datetime
from typing import Any

from app.neo4j_client import Neo4jClient
from app.llm.factory import get_llm
from app.config import settings

logger = logging.getLogger(__name__)


class LLMEnrichment:
    """Enriquece el grafo con análisis de LLM."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j = neo4j_client
        self._llm = None
    
    @property
    def llm(self):
        """Lazy loading del LLM."""
        if self._llm is None:
            self._llm = get_llm()
        return self._llm
    
    async def enrich_all(self) -> dict[str, Any]:
        """
        Ejecuta todo el proceso de enriquecimiento.
        
        Returns:
            Diccionario con resultados
        """
        logger.info("🧠 Iniciando enriquecimiento con LLM...")
        logger.info(f"   Provider: {settings.LLM_PROVIDER}")
        logger.info(f"   Model: {settings.LLM_MODEL}")
        
        results = {
            "perfiles_clasificados": 0,
            "clusters_generados": 0,
            "insights_generados": False
        }
        
        # 1. Clasificar perfiles de pagadores
        results["perfiles_clasificados"] = await self.clasificar_perfiles_pagadores()
        
        # 2. Generar clusters de comportamiento
        results["clusters_generados"] = await self.generar_clusters_comportamiento()
        
        # 3. Generar insights predictivos
        results["insights_generados"] = await self.generar_insights_predictivos()
        
        logger.info(f"✅ Enriquecimiento completado: {results}")
        return results
    
    async def clasificar_perfiles_pagadores(self) -> int:
        """
        Usa LLM para clasificar perfiles de pagadores.
        
        Returns:
            Número de responsables clasificados
        """
        logger.info("   🔍 Clasificando perfiles de pagadores...")
        
        # Obtener responsables con métricas
        responsables = await self.neo4j.execute("""
            MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e:Estudiante)
            OPTIONAL MATCH (r)-[p:PAGO]->(c:Cuota)
            OPTIONAL MATCH (r)-[i:IGNORO_NOTIFICACION]->(c2:Cuota)
            OPTIONAL MATCH (r)-[:CREO_TICKET]->(t:Ticket)
            
            WITH r,
                 count(DISTINCT p) as pagos_totales,
                 avg(p.dias_demora) as demora_promedio,
                 max(p.dias_demora) as demora_maxima,
                 count(DISTINCT i) as notif_ignoradas,
                 count(DISTINCT t) as tickets_creados
            
            WHERE pagos_totales > 0 OR notif_ignoradas > 0
            
            RETURN r.erp_id as erp_id,
                   r.nombre as nombre,
                   r.apellido as apellido,
                   pagos_totales,
                   coalesce(demora_promedio, 0) as demora_promedio,
                   coalesce(demora_maxima, 0) as demora_maxima,
                   notif_ignoradas,
                   tickets_creados
            LIMIT 100
        """)
        
        count = 0
        for resp in responsables:
            try:
                # Construir prompt para LLM
                prompt = f"""
Clasifica el perfil de este responsable de alumno según su comportamiento de pago:

Datos:
- Nombre: {resp['nombre']} {resp['apellido']}
- Pagos totales realizados: {resp['pagos_totales']}
- Demora promedio en días: {resp['demora_promedio']:.1f}
- Demora máxima en días: {resp['demora_maxima']}
- Notificaciones ignoradas: {resp['notif_ignoradas']}
- Tickets de soporte creados: {resp['tickets_creados']}

Clasifica en UNA de estas categorías:
- PUNTUAL: Paga siempre a tiempo o con mínima demora (0-5 días)
- EVENTUAL: Paga pero con demoras moderadas (6-30 días)
- MOROSO: Demoras frecuentes o mayores a 30 días
- NUEVO: Sin historial suficiente (menos de 2 pagos)

Responde ÚNICAMENTE con este JSON válido (sin texto adicional):
{{"perfil": "PUNTUAL|EVENTUAL|MOROSO|NUEVO", "nivel_riesgo": "BAJO|MEDIO|ALTO", "razon": "explicación breve", "patrones": ["patrón1", "patrón2"]}}
"""
                
                response = await self.llm.ainvoke(prompt)
                content = response.content.strip()
                
                # Limpiar respuesta si tiene markdown
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()
                
                clasificacion = json.loads(content)
                
                # Actualizar nodo en Neo4j
                await self.neo4j.execute_write("""
                    MATCH (r:Responsable {erp_id: $erp_id})
                    SET r.perfil_pagador = $perfil,
                        r.nivel_riesgo = $nivel_riesgo,
                        r.patrones_detectados = $patrones,
                        r.razon_clasificacion = $razon,
                        r.clasificado_por_llm = $llm_info,
                        r.ultima_clasificacion = datetime()
                """, {
                    "erp_id": resp["erp_id"],
                    "perfil": clasificacion.get("perfil", "NUEVO"),
                    "nivel_riesgo": clasificacion.get("nivel_riesgo", "MEDIO"),
                    "patrones": clasificacion.get("patrones", []),
                    "razon": clasificacion.get("razon", ""),
                    "llm_info": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}"
                })
                count += 1
                
            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando JSON para {resp['erp_id']}: {e}")
            except Exception as e:
                logger.error(f"Error clasificando responsable {resp['erp_id']}: {e}")
        
        logger.info(f"   ✅ {count} perfiles clasificados")
        return count
    
    async def generar_clusters_comportamiento(self) -> int:
        """
        Genera clusters de comportamiento con descripciones LLM.
        
        Returns:
            Número de clusters generados
        """
        logger.info("   👥 Generando clusters de comportamiento...")
        
        # Agrupar responsables por perfil y riesgo
        grupos = await self.neo4j.execute("""
            MATCH (r:Responsable)
            WHERE r.perfil_pagador IS NOT NULL
            
            WITH r.perfil_pagador as perfil,
                 r.nivel_riesgo as riesgo,
                 collect({
                     nombre: r.nombre + ' ' + r.apellido,
                     patrones: r.patrones_detectados
                 })[0..5] as muestra_responsables,
                 count(r) as cantidad
            
            WHERE cantidad >= 1
            
            RETURN perfil, riesgo, muestra_responsables, cantidad
            ORDER BY cantidad DESC
        """)
        
        count = 0
        for grupo in grupos:
            try:
                # Generar descripción con LLM
                prompt = f"""
Analiza este grupo de {grupo['cantidad']} responsables de alumnos:

Perfil de pago: {grupo['perfil']}
Nivel de riesgo: {grupo['riesgo']}
Muestra de patrones: {json.dumps(grupo['muestra_responsables'], ensure_ascii=False)}

Genera:
1. Una descripción clara del comportamiento típico de este grupo
2. Recomendaciones específicas para mejorar la cobranza
3. Estrategia de comunicación óptima

Responde ÚNICAMENTE con este JSON válido:
{{"descripcion": "descripción del cluster", "caracteristicas": ["característica1", "característica2"], "recomendaciones": ["recomendación1", "recomendación2"], "estrategia_comunicacion": "mejor horario y canal"}}
"""
                
                response = await self.llm.ainvoke(prompt)
                content = response.content.strip()
                
                # Limpiar respuesta
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()
                
                cluster_info = json.loads(content)
                
                # Crear nodo de cluster
                cluster_id = f"{grupo['perfil']}_{grupo['riesgo']}"
                
                await self.neo4j.execute_write("""
                    MERGE (c:ClusterComportamiento {tipo: $tipo})
                    SET c.perfil = $perfil,
                        c.riesgo = $riesgo,
                        c.descripcion = $descripcion,
                        c.caracteristicas = $caracteristicas,
                        c.recomendaciones = $recomendaciones,
                        c.estrategia = $estrategia,
                        c.cantidad_miembros = $cantidad,
                        c.generado_por_llm = $llm_info,
                        c.ultima_actualizacion = datetime()
                """, {
                    "tipo": cluster_id,
                    "perfil": grupo["perfil"],
                    "riesgo": grupo["riesgo"],
                    "descripcion": cluster_info.get("descripcion", ""),
                    "caracteristicas": cluster_info.get("caracteristicas", []),
                    "recomendaciones": cluster_info.get("recomendaciones", []),
                    "estrategia": cluster_info.get("estrategia_comunicacion", ""),
                    "cantidad": grupo["cantidad"],
                    "llm_info": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}"
                })
                
                # Conectar responsables al cluster
                await self.neo4j.execute_write("""
                    MATCH (r:Responsable)
                    WHERE r.perfil_pagador = $perfil 
                      AND r.nivel_riesgo = $riesgo
                    
                    MATCH (c:ClusterComportamiento {tipo: $tipo})
                    MERGE (r)-[:PERTENECE_A]->(c)
                """, {
                    "perfil": grupo["perfil"],
                    "riesgo": grupo["riesgo"],
                    "tipo": cluster_id
                })
                
                count += 1
                
            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando JSON para cluster {grupo['perfil']}_{grupo['riesgo']}: {e}")
            except Exception as e:
                logger.error(f"Error generando cluster: {e}")
        
        logger.info(f"   ✅ {count} clusters generados")
        return count
    
    async def generar_insights_predictivos(self) -> dict[str, Any]:
        """
        Genera insights predictivos basados en patrones del grafo.
        
        Returns:
            Diccionario con insights generados
        """
        logger.info("   📊 Generando insights predictivos...")
        
        try:
            # Obtener métricas agregadas
            metricas = await self.neo4j.execute("""
                MATCH (r:Responsable)
                WITH count(r) as total_responsables,
                     count(CASE WHEN r.nivel_riesgo = 'ALTO' THEN 1 END) as alto_riesgo,
                     count(CASE WHEN r.nivel_riesgo = 'MEDIO' THEN 1 END) as medio_riesgo,
                     count(CASE WHEN r.perfil_pagador = 'MOROSO' THEN 1 END) as morosos,
                     count(CASE WHEN r.perfil_pagador = 'PUNTUAL' THEN 1 END) as puntuales
                
                MATCH (c:Cuota)
                WHERE c.estado = 'vencida'
                
                WITH total_responsables, alto_riesgo, medio_riesgo, morosos, puntuales,
                     count(c) as cuotas_vencidas,
                     sum(c.monto) as monto_vencido
                
                RETURN total_responsables, alto_riesgo, medio_riesgo, morosos, puntuales,
                       cuotas_vencidas, coalesce(monto_vencido, 0) as monto_vencido
            """)
            
            if not metricas:
                logger.warning("No hay métricas disponibles para generar insights")
                return {"error": "No hay datos suficientes"}
            
            m = metricas[0]
            
            # Generar insights con LLM
            prompt = f"""
Analiza estas métricas del sistema de cobranza escolar y genera insights predictivos:

MÉTRICAS ACTUALES:
- Total de responsables: {m['total_responsables']}
- En riesgo ALTO: {m['alto_riesgo']} ({(m['alto_riesgo']/max(m['total_responsables'],1))*100:.1f}%)
- En riesgo MEDIO: {m['medio_riesgo']}
- Perfil MOROSO: {m['morosos']}
- Perfil PUNTUAL: {m['puntuales']}
- Cuotas vencidas: {m['cuotas_vencidas']}
- Monto total vencido: ${m['monto_vencido']:,.0f}

Genera un análisis con:
1. tendencias: 3-4 tendencias principales detectadas
2. riesgos: 3-4 riesgos potenciales para los próximos 30 días
3. oportunidades: 2-3 oportunidades de mejora en cobranza
4. acciones: 3-4 acciones prioritarias ordenadas por impacto

Responde ÚNICAMENTE con este JSON válido:
{{"tendencias": ["tendencia1", "tendencia2"], "riesgos": ["riesgo1", "riesgo2"], "oportunidades": ["oportunidad1"], "acciones": ["acción1", "acción2"]}}
"""
            
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()
            
            # Limpiar respuesta
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            insights = json.loads(content)
            
            # Guardar en Neo4j como nodo de Insights
            await self.neo4j.execute_write("""
                MERGE (i:InsightsPredictivos {id: 'latest'})
                SET i.tendencias = $tendencias,
                    i.riesgos = $riesgos,
                    i.oportunidades = $oportunidades,
                    i.acciones = $acciones,
                    i.metricas = $metricas,
                    i.generado_por_llm = $llm_info,
                    i.timestamp = datetime()
            """, {
                "tendencias": insights.get("tendencias", []),
                "riesgos": insights.get("riesgos", []),
                "oportunidades": insights.get("oportunidades", []),
                "acciones": insights.get("acciones", []),
                "metricas": json.dumps(m),
                "llm_info": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}"
            })
            
            logger.info("   ✅ Insights predictivos generados")
            
            return {
                "insights": insights,
                "metricas": m,
                "generado_por": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando insights: {e}")
            return {"error": str(e)}


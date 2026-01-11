# Knowledge Graph - Sistema de Analytics

Sistema de Knowledge Graph con Neo4j para análisis predictivo de mora y deserción escolar.

## Stack Técnico

- **Graph DB:** Neo4j 5
- **ETL:** Python async + Celery
- **LLM:** LangChain + OpenAI GPT / Google Gemini (configurable)
- **Backend:** FastAPI
- **Scheduler:** Celery Beat

## Estructura del Proyecto

```
knowledge_graph/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuración
│   ├── neo4j_client.py     # Cliente Neo4j
│   ├── main.py             # FastAPI app
│   │
│   ├── llm/                # LLM Factory
│   │   ├── factory.py      # OpenAI/Gemini
│   │   └── base.py
│   │
│   ├── etl/                # Procesos ETL
│   │   ├── sync_from_erp.py
│   │   ├── sync_from_gestor.py
│   │   ├── llm_enrichment.py
│   │   └── scheduler.py    # Celery tasks
│   │
│   ├── queries/            # Consultas Cypher
│   │   ├── riesgo_desercion.py
│   │   ├── proyeccion_caja.py
│   │   ├── patrones.py
│   │   └── insights_llm.py
│   │
│   └── api/
│       └── reportes.py     # Endpoints
│
├── scripts/
│   ├── init_graph.py       # Crear constraints/índices
│   └── run_etl.py          # ETL manual
│
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Modelo del Grafo

```cypher
// NODOS
(:Responsable)              // Padres/tutores
(:Estudiante)               // Alumnos
(:Cuota)                    // Cuotas a pagar
(:Grado)                    // Niveles educativos
(:ClusterComportamiento)    // Clusters generados por LLM
(:Ticket)                   // Tickets de soporte
(:InsightsPredictivos)      // Insights generados

// RELACIONES
(:Responsable)-[:RESPONSABLE_DE]->(:Estudiante)
(:Estudiante)-[:CURSA]->(:Grado)
(:Estudiante)-[:DEBE]->(:Cuota)
(:Responsable)-[:PAGO {fecha, dias_demora, monto}]->(:Cuota)
(:Responsable)-[:INTERACTUO {timestamp, tipo}]->(:Cuota)
(:Responsable)-[:IGNORO_NOTIFICACION {fecha, tipo_notif}]->(:Cuota)
(:Responsable)-[:PERTENECE_A]->(:ClusterComportamiento)
(:Responsable)-[:CREO_TICKET]->(:Ticket)
```

## Requisitos Previos

1. **ERP Mock** corriendo en `localhost:8001`
2. **Gestor WS** corriendo en `localhost:8000`
3. Docker y Docker Compose instalados
4. API Keys configuradas (OpenAI o Google)

## Instalación

```bash
# 1. Copiar configuración
cp .env.example .env

# 2. Configurar API Keys en .env
# LLM_PROVIDER=google
# GOOGLE_API_KEY=AIzaSy...

# 3. Levantar servicios
docker-compose up -d

# 4. Inicializar grafo (constraints/índices)
docker-compose exec api python scripts/init_graph.py

# 5. Ejecutar ETL inicial
docker-compose exec api python scripts/run_etl.py
```

## URLs

| Servicio | URL |
|----------|-----|
| API Analytics | http://localhost:8002 |
| API Docs | http://localhost:8002/docs |
| Neo4j Browser | http://localhost:7474 |
| Redis | localhost:6379 |

## Endpoints API

### Riesgo de Deserción

```bash
# Lista alumnos en riesgo
GET /api/v1/reportes/riesgo-desercion?umbral=40

# Solo riesgo alto
GET /api/v1/reportes/riesgo-desercion/alto

# Estadísticas
GET /api/v1/reportes/riesgo-desercion/estadisticas
```

### Proyección de Caja

```bash
# Proyección a 90 días
GET /api/v1/reportes/proyeccion-caja?dias=90

# Vencimientos próximos
GET /api/v1/reportes/vencimientos-proximos?dias=7

# Deuda por grado
GET /api/v1/reportes/deuda-por-grado
```

### Analytics con LLM

```bash
# Clusters de comportamiento
GET /api/v1/reportes/clusters

# Insights predictivos
GET /api/v1/reportes/insights-predictivos

# Resumen ejecutivo (genera con LLM)
GET /api/v1/reportes/resumen-ejecutivo

# Recomendaciones personalizadas
GET /api/v1/reportes/recomendaciones/{responsable_id}
```

### ETL Manual

```bash
# Sincronizar desde ERP
POST /api/v1/reportes/etl/sync-erp

# Sincronizar desde Gestor WS
POST /api/v1/reportes/etl/sync-gestor

# Enriquecer con LLM
POST /api/v1/reportes/etl/enrich-llm

# ETL completo
POST /api/v1/reportes/etl/full
```

## ETL Programado (Celery)

| Tarea | Frecuencia |
|-------|------------|
| ETL Nocturno (completo) | 2:00 AM diario |
| Sync incremental ERP | Cada 6 horas |
| Cálculo scores riesgo | Cada 6 horas |
| Resumen semanal | Lunes 8:00 AM |
| Actualizar clusters | Domingo 3:00 AM |

## Comandos

```bash
# Ver logs
docker-compose logs -f api

# Ejecutar ETL manual
docker-compose exec api python scripts/run_etl.py

# Solo sincronizar ERP
docker-compose exec api python scripts/run_etl.py --only-erp

# Solo enriquecer con LLM
docker-compose exec api python scripts/run_etl.py --only-llm

# Abrir Neo4j Browser
open http://localhost:7474

# Ver estado del grafo
curl http://localhost:8002/api/v1/reportes/status/grafo
```

## Configuración LLM

El sistema soporta **OpenAI** y **Google Gemini**. Configurar en `.env`:

```bash
# Para OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-proj-xxx...

# Para Google Gemini
LLM_PROVIDER=google
LLM_MODEL=gemini-2.0-flash-exp
GOOGLE_API_KEY=AIzaSy...
```

## Propiedades Enriquecidas por LLM

Los responsables son clasificados automáticamente:

```json
{
  "perfil_pagador": "PUNTUAL | EVENTUAL | MOROSO | NUEVO",
  "nivel_riesgo": "BAJO | MEDIO | ALTO",
  "patrones_detectados": ["patrón 1", "patrón 2"],
  "razon_clasificacion": "Explicación del LLM"
}
```

Los clusters incluyen:

```json
{
  "tipo": "MOROSO_ALTO",
  "descripcion": "Descripción generada por LLM",
  "caracteristicas": ["característica 1", "característica 2"],
  "recomendaciones": ["recomendación 1", "recomendación 2"],
  "estrategia_comunicacion": "Mejor momento y canal"
}
```


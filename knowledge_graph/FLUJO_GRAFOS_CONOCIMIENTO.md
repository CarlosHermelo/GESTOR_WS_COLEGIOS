# 🔄 Flujo Completo de Grafos de Conocimiento

Este documento describe el flujo completo del sistema de Knowledge Graph, desde la ingesta de datos hasta la generación de reportes.

---

## 📊 Diagrama de Flujo General

```
┌─────────────────────────────────────────────────────────────────┐
│                    FUENTES DE DATOS                              │
├─────────────────────────────────────────────────────────────────┤
│  • ERP Mock (Cache de Gestor WS)                                │
│    - Responsables, Estudiantes, Cuotas, Pagos                  │
│  • Gestor WS                                                    │
│    - Interacciones WhatsApp, Notificaciones, Tickets           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 1: ETL - INGESTA DE DATOS               │
├─────────────────────────────────────────────────────────────────┤
│  📥 sync_from_erp.py                                            │
│     • sync_responsables()      → Nodos :Responsable             │
│     • sync_estudiantes()       → Nodos :Estudiante + :Grado    │
│     • sync_cuotas()            → Nodos :Cuota                   │
│     • sync_pagos()             → Relaciones :PAGO                │
│                                                                  │
│  📥 sync_from_gestor.py                                         │
│     • sync_interacciones()     → Relaciones :INTERACTUO         │
│     • detectar_notif_ignoradas() → Relaciones :IGNORO_NOTIFICACION │
│     • sync_tickets()           → Nodos :Ticket                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NEO4J - KNOWLEDGE GRAPH                      │
├─────────────────────────────────────────────────────────────────┤
│  Estructura del Grafo:                                          │
│                                                                  │
│  (:Responsable)                                                 │
│    ├─[:RESPONSABLE_DE]→(:Estudiante)                           │
│    ├─[:PAGO]→(:Cuota)                                          │
│    ├─[:INTERACTUO]→(:Cuota)                                    │
│    ├─[:IGNORO_NOTIFICACION]→(:Cuota)                            │
│    ├─[:CREO_TICKET]→(:Ticket)                                   │
│    └─[:PERTENECE_A]→(:ClusterComportamiento)                   │
│                                                                  │
│  (:Estudiante)                                                  │
│    ├─[:CURSA]→(:Grado)                                         │
│    └─[:DEBE]→(:Cuota)                                          │
│                                                                  │
│  (:ClusterComportamiento) ← Generado por LLM                    │
│  (:InsightsPredictivos) ← Generado por LLM                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 2: ENRIQUECIMIENTO CON LLM               │
├─────────────────────────────────────────────────────────────────┤
│  🧠 llm_enrichment.py                                           │
│                                                                  │
│  1. clasificar_perfiles_pagadores()                             │
│     • Analiza comportamiento de cada Responsable                 │
│     • Clasifica: PUNTUAL, EVENTUAL, MOROSO, NUEVO              │
│     • Asigna nivel_riesgo: BAJO, MEDIO, ALTO                    │
│     • Detecta patrones de comportamiento                        │
│     • Actualiza nodos :Responsable con:                         │
│       - perfil_pagador                                          │
│       - nivel_riesgo                                             │
│       - patrones_detectados                                      │
│       - razon_clasificacion                                      │
│                                                                  │
│  2. generar_clusters_comportamiento()                            │
│     • Agrupa responsables por perfil y riesgo                   │
│     • Genera descripciones con LLM                               │
│     • Crea nodos :ClusterComportamiento con:                     │
│       - descripcion                                              │
│       - caracteristicas                                          │
│       - recomendaciones                                          │
│       - estrategia_comunicacion                                  │
│     • Conecta responsables con [:PERTENECE_A]                    │
│                                                                  │
│  3. generar_insights_predictivos()                               │
│     • Analiza métricas agregadas del grafo                       │
│     • Genera insights con LLM:                                   │
│       - tendencias                                               │
│       - riesgos                                                  │
│       - oportunidades                                            │
│       - acciones                                                 │
│     • Almacena en nodo :InsightsPredictivos                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 3: GENERACIÓN DE REPORTES                │
├─────────────────────────────────────────────────────────────────┤
│  📈 Queries Cypher + API Endpoints                              │
│                                                                  │
│  A. RIESGO DE DESERCIÓN                                         │
│     queries/riesgo_desercion.py                                 │
│     • calcular_score_riesgo_desercion()                          │
│       - Factores: cuotas vencidas, notif ignoradas,            │
│         hermanos en mora, nivel_riesgo responsable, tickets    │
│       - Score 0-100 → nivel: ALTO/MEDIO/BAJO                   │
│     • obtener_alumnos_alto_riesgo()                             │
│     • obtener_estadisticas_riesgo()                              │
│                                                                  │
│     Endpoints:                                                   │
│     GET /api/v1/reportes/riesgo-desercion                       │
│     GET /api/v1/reportes/riesgo-desercion/alto                  │
│     GET /api/v1/reportes/riesgo-desercion/estadisticas          │
│                                                                  │
│  B. PROYECCIÓN DE CAJA                                          │
│     queries/proyeccion_caja.py                                  │
│     • proyectar_caja(dias=90)                                   │
│       - Considera perfil_pagador para probabilidades            │
│       - Escenarios: optimista, realista, pesimista              │
│     • obtener_vencimientos_proximos()                           │
│     • obtener_deuda_por_grado()                                  │
│     • obtener_resumen_financiero()                              │
│                                                                  │
│     Endpoints:                                                   │
│     GET /api/v1/reportes/proyeccion-caja                        │
│     GET /api/v1/reportes/vencimientos-proximos                  │
│     GET /api/v1/reportes/deuda-por-grado                        │
│                                                                  │
│  C. DETECCIÓN DE PATRONES                                       │
│     queries/patrones.py                                         │
│     • detectar_patrones()                                        │
│       - Patrones de morosidad                                   │
│       - Familias con múltiples hijos en mora                    │
│       - Grados críticos                                         │
│     • obtener_clusters()                                        │
│     • detectar_riesgo_abandono()                                 │
│     • detectar_familias_problema()                               │
│     • detectar_grados_criticos()                                 │
│                                                                  │
│     Endpoints:                                                   │
│     GET /api/v1/reportes/patrones                               │
│     GET /api/v1/reportes/clusters                               │
│                                                                  │
│  D. INSIGHTS CON LLM                                            │
│     queries/insights_llm.py                                     │
│     • generar_resumen_ejecutivo()                                │
│       - Genera resumen en tiempo real con LLM                   │
│     • obtener_insights_almacenados()                             │
│       - Lee nodo :InsightsPredictivos                           │
│     • generar_recomendaciones_personalizadas()                  │
│       - Recomendaciones por responsable                         │
│                                                                  │
│     Endpoints:                                                   │
│     GET /api/v1/reportes/resumen-ejecutivo                      │
│     GET /api/v1/reportes/insights-predictivos                   │
│     GET /api/v1/reportes/recomendaciones/{responsable_id}      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SALIDA: REPORTES Y ANALYTICS                  │
├─────────────────────────────────────────────────────────────────┤
│  • JSON via API REST (FastAPI)                                  │
│  • Consumido por Frontend Admin                                 │
│  • Visualizaciones en dashboards                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo Detallado por Fase

### **FASE 1: INGESTA DE DATOS (ETL)**

#### 1.1 Sincronización desde ERP (`sync_from_erp.py`)

**Origen:** Base de datos de cache de Gestor WS (tablas: `cache_responsables`, `cache_alumnos`, `cache_cuotas`)

**Proceso:**

```python
# 1. Responsables
sync_responsables()
  → Lee: cache_responsables
  → Crea: Nodos (:Responsable {erp_id, nombre, apellido, whatsapp, email})
  
# 2. Estudiantes
sync_estudiantes()
  → Lee: cache_alumnos
  → Crea: 
     - Nodos (:Estudiante {erp_id, nombre, apellido, grado})
     - Nodos (:Grado {nombre})
     - Relaciones (:Responsable)-[:RESPONSABLE_DE]->(:Estudiante)
     - Relaciones (:Estudiante)-[:CURSA]->(:Grado)
  
# 3. Cuotas
sync_cuotas()
  → Lee: cache_cuotas
  → Crea:
     - Nodos (:Cuota {erp_id, monto, fecha_vencimiento, estado, link_pago})
     - Relaciones (:Estudiante)-[:DEBE]->(:Cuota)
  
# 4. Pagos
sync_pagos()
  → Lee: cache_cuotas (donde estado='pagada')
  → Crea:
     - Relaciones (:Responsable)-[:PAGO {fecha, monto, dias_demora}]->(:Cuota)
```

**Archivos:**
- `knowledge_graph/app/etl/sync_from_erp.py`

---

#### 1.2 Sincronización desde Gestor WS (`sync_from_gestor.py`)

**Origen:** Base de datos de Gestor WS (tablas: `interacciones`, `notificaciones_enviadas`, `tickets`)

**Proceso:**

```python
# 1. Interacciones WhatsApp
sync_interacciones(dias=30)
  → Lee: interacciones (últimos 30 días)
  → Crea:
     - Relaciones (:Responsable)-[:INTERACTUO {id, timestamp, tipo, agente, contenido_preview}]->(:Cuota)
  
# 2. Notificaciones Ignoradas
detectar_notificaciones_ignoradas(horas=48)
  → Lee: notificaciones_enviadas (no leídas, >48 horas)
  → Crea:
     - Relaciones (:Responsable)-[:IGNORO_NOTIFICACION {id, fecha, tipo_notif}]->(:Cuota)
  
# 3. Tickets
sync_tickets()
  → Lee: tickets
  → Crea:
     - Nodos (:Ticket {id, categoria, prioridad, estado, created_at, resolved_at})
     - Relaciones (:Responsable)-[:CREO_TICKET]->(:Ticket)
```

**Archivos:**
- `knowledge_graph/app/etl/sync_from_gestor.py`

---

### **FASE 2: ENRIQUECIMIENTO CON LLM**

#### 2.1 Clasificación de Perfiles (`clasificar_perfiles_pagadores()`)

**Proceso:**

1. **Consulta Cypher** obtiene responsables con métricas:
   - Total de pagos
   - Demora promedio y máxima
   - Notificaciones ignoradas
   - Tickets creados

2. **Para cada responsable:**
   - Construye prompt con métricas
   - Llama a LLM (OpenAI/Gemini)
   - LLM clasifica en: `PUNTUAL`, `EVENTUAL`, `MOROSO`, `NUEVO`
   - LLM asigna: `nivel_riesgo` (BAJO/MEDIO/ALTO)
   - LLM detecta: `patrones` de comportamiento
   - LLM explica: `razon` de la clasificación

3. **Actualiza nodo** `:Responsable` con:
   ```cypher
   SET r.perfil_pagador = $perfil,
       r.nivel_riesgo = $nivel_riesgo,
       r.patrones_detectados = $patrones,
       r.razon_clasificacion = $razon,
       r.clasificado_por_llm = $llm_info,
       r.ultima_clasificacion = datetime()
   ```

**Archivos:**
- `knowledge_graph/app/etl/llm_enrichment.py` (líneas 60-158)

---

#### 2.2 Generación de Clusters (`generar_clusters_comportamiento()`)

**Proceso:**

1. **Agrupa responsables** por `perfil_pagador` + `nivel_riesgo`

2. **Para cada grupo:**
   - Construye prompt con muestra de responsables y patrones
   - Llama a LLM para generar:
     - `descripcion`: Comportamiento típico del grupo
     - `caracteristicas`: Lista de características
     - `recomendaciones`: Recomendaciones de cobranza
     - `estrategia_comunicacion`: Mejor horario y canal

3. **Crea nodo** `:ClusterComportamiento`:
   ```cypher
   MERGE (c:ClusterComportamiento {tipo: $tipo})
   SET c.perfil = $perfil,
       c.riesgo = $riesgo,
       c.descripcion = $descripcion,
       c.caracteristicas = $caracteristicas,
       c.recomendaciones = $recomendaciones,
       c.estrategia = $estrategia,
       c.cantidad_miembros = $cantidad
   ```

4. **Conecta responsables:**
   ```cypher
   MATCH (r:Responsable)
   WHERE r.perfil_pagador = $perfil AND r.nivel_riesgo = $riesgo
   MATCH (c:ClusterComportamiento {tipo: $tipo})
   MERGE (r)-[:PERTENECE_A]->(c)
   ```

**Archivos:**
- `knowledge_graph/app/etl/llm_enrichment.py` (líneas 160-268)

---

#### 2.3 Generación de Insights Predictivos (`generar_insights_predictivos()`)

**Proceso:**

1. **Obtiene métricas agregadas** del grafo:
   - Total de responsables
   - Responsables en riesgo ALTO/MEDIO
   - Perfiles MOROSO/PUNTUAL
   - Cuotas vencidas y monto vencido

2. **Genera insights con LLM:**
   - `tendencias`: 3-4 tendencias principales
   - `riesgos`: 3-4 riesgos potenciales (próximos 30 días)
   - `oportunidades`: 2-3 oportunidades de mejora
   - `acciones`: 3-4 acciones prioritarias

3. **Almacena en nodo** `:InsightsPredictivos`:
   ```cypher
   MERGE (i:InsightsPredictivos {id: 'latest'})
   SET i.tendencias = $tendencias,
       i.riesgos = $riesgos,
       i.oportunidades = $oportunidades,
       i.acciones = $acciones,
       i.metricas = $metricas,
       i.timestamp = datetime()
   ```

**Archivos:**
- `knowledge_graph/app/etl/llm_enrichment.py` (líneas 270-371)

---

### **FASE 3: GENERACIÓN DE REPORTES**

#### 3.1 Reportes de Riesgo de Deserción

**Query Principal:** `calcular_score_riesgo_desercion()`

**Factores de Score (0-100):**
- Cuotas vencidas: 20 pts c/u
- Notificaciones ignoradas: 15 pts c/u
- Cuotas vencidas de hermanos: 10 pts c/u
- Nivel de riesgo del responsable: 0-30 pts (ALTO=30, MEDIO=15, BAJO=0)
- Tickets de soporte: 5 pts c/u

**Niveles:**
- ALTO: score >= 70
- MEDIO: score >= 40
- BAJO: score < 40

**Endpoints:**
- `GET /api/v1/reportes/riesgo-desercion?umbral=40`
- `GET /api/v1/reportes/riesgo-desercion/alto`
- `GET /api/v1/reportes/riesgo-desercion/estadisticas`

**Archivos:**
- `knowledge_graph/app/queries/riesgo_desercion.py`
- `knowledge_graph/app/api/reportes.py` (líneas 63-99)

---

#### 3.2 Reportes de Proyección de Caja

**Query Principal:** `proyectar_caja(dias=90)`

**Proceso:**
1. Obtiene cuotas pendientes con `perfil_pagador` del responsable
2. Aplica probabilidades de cobro según perfil:
   - PUNTUAL: optimista 95%, realista 85%, pesimista 75%
   - EVENTUAL: optimista 75%, realista 55%, pesimista 35%
   - MOROSO: optimista 45%, realista 25%, pesimista 10%
   - NUEVO: optimista 70%, realista 50%, pesimista 30%

3. Calcula 3 escenarios de proyección

**Endpoints:**
- `GET /api/v1/reportes/proyeccion-caja?dias=90`
- `GET /api/v1/reportes/vencimientos-proximos?dias=7`
- `GET /api/v1/reportes/deuda-por-grado`

**Archivos:**
- `knowledge_graph/app/queries/proyeccion_caja.py`
- `knowledge_graph/app/api/reportes.py` (líneas 104-139)

---

#### 3.3 Reportes de Patrones

**Queries:**
- `detectar_patrones()`: Detecta todos los patrones
- `detectar_patrones_morosidad()`: Patrones de morosidad recurrente
- `detectar_familias_problema()`: Familias con múltiples hijos en mora
- `detectar_grados_criticos()`: Grados con mayor morosidad
- `obtener_clusters()`: Clusters de comportamiento con descripciones LLM

**Endpoints:**
- `GET /api/v1/reportes/patrones`
- `GET /api/v1/reportes/clusters`

**Archivos:**
- `knowledge_graph/app/queries/patrones.py`
- `knowledge_graph/app/api/reportes.py` (líneas 144-162)

---

#### 3.4 Reportes con LLM

**Queries:**
- `generar_resumen_ejecutivo()`: Genera resumen en tiempo real
- `obtener_insights_almacenados()`: Lee insights pre-generados
- `generar_recomendaciones_personalizadas()`: Recomendaciones por responsable

**Endpoints:**
- `GET /api/v1/reportes/resumen-ejecutivo`
- `GET /api/v1/reportes/insights-predictivos`
- `GET /api/v1/reportes/recomendaciones/{responsable_id}`

**Archivos:**
- `knowledge_graph/app/queries/insights_llm.py`
- `knowledge_graph/app/api/reportes.py` (líneas 167-201)

---

## ⏰ Programación Automática (Celery)

El sistema incluye tareas programadas que se ejecutan automáticamente:

**Archivo:** `knowledge_graph/app/etl/scheduler.py`

| Tarea | Frecuencia | Descripción |
|-------|-----------|-------------|
| `etl_nocturno` | Diario 2:00 AM | ETL completo: ERP + Gestor + LLM |
| `sync_erp_incremental` | Cada 6 horas | Sincroniza solo cuotas y pagos |
| `calcular_scores_riesgo` | Cada 6 horas (offset 30min) | Recalcula scores de riesgo |
| `generar_resumen_semanal` | Lunes 8:00 AM | Genera resumen ejecutivo semanal |
| `actualizar_clusters` | Domingo 3:00 AM | Actualiza clusters de comportamiento |

---

## 🚀 Ejecución Manual

### Script de ETL Manual

```bash
# ETL completo
python knowledge_graph/scripts/run_etl.py

# Solo ERP
python knowledge_graph/scripts/run_etl.py --only-erp

# Solo LLM
python knowledge_graph/scripts/run_etl.py --only-llm

# Sin LLM
python knowledge_graph/scripts/run_etl.py --no-llm
```

**Archivo:** `knowledge_graph/scripts/run_etl.py`

---

## 📡 API Endpoints de ETL

También se pueden disparar ETLs vía API:

```bash
# ETL completo
POST /api/v1/reportes/etl/full

# Solo ERP
POST /api/v1/reportes/etl/sync-erp

# Solo Gestor
POST /api/v1/reportes/etl/sync-gestor

# Solo LLM
POST /api/v1/reportes/etl/enrich-llm
```

**Archivos:**
- `knowledge_graph/app/api/reportes.py` (líneas 204-294)

---

## 🔍 Estructura de Datos en Neo4j

### Nodos Principales

- `(:Responsable)` - Padres/tutores
- `(:Estudiante)` - Alumnos
- `(:Cuota)` - Cuotas a pagar
- `(:Grado)` - Niveles educativos
- `(:Ticket)` - Tickets de soporte
- `(:ClusterComportamiento)` - Clusters generados por LLM
- `(:InsightsPredictivos)` - Insights generados por LLM

### Relaciones Principales

- `(:Responsable)-[:RESPONSABLE_DE]->(:Estudiante)`
- `(:Estudiante)-[:CURSA]->(:Grado)`
- `(:Estudiante)-[:DEBE]->(:Cuota)`
- `(:Responsable)-[:PAGO]->(:Cuota)`
- `(:Responsable)-[:INTERACTUO]->(:Cuota)`
- `(:Responsable)-[:IGNORO_NOTIFICACION]->(:Cuota)`
- `(:Responsable)-[:CREO_TICKET]->(:Ticket)`
- `(:Responsable)-[:PERTENECE_A]->(:ClusterComportamiento)`

---

## 📝 Resumen del Flujo

1. **INGESTA** → Datos desde ERP y Gestor WS se sincronizan a Neo4j
2. **ENRIQUECIMIENTO** → LLM clasifica perfiles, genera clusters e insights
3. **CONSULTA** → Queries Cypher analizan el grafo enriquecido
4. **REPORTES** → API REST expone reportes y analytics
5. **AUTOMATIZACIÓN** → Celery ejecuta ETLs y cálculos periódicamente

---

## 🔗 Archivos Clave

| Archivo | Descripción |
|---------|-------------|
| `app/etl/sync_from_erp.py` | ETL desde cache de ERP |
| `app/etl/sync_from_gestor.py` | ETL desde Gestor WS |
| `app/etl/llm_enrichment.py` | Enriquecimiento con LLM |
| `app/etl/scheduler.py` | Tareas programadas Celery |
| `app/queries/riesgo_desercion.py` | Queries de riesgo |
| `app/queries/proyeccion_caja.py` | Queries financieras |
| `app/queries/patrones.py` | Queries de patrones |
| `app/queries/insights_llm.py` | Queries con LLM |
| `app/api/reportes.py` | Endpoints de reportes |
| `scripts/run_etl.py` | Script ETL manual |

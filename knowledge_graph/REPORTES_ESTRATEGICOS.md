# 📊 Reportes Estratégicos con Neo4j - Knowledge Graph

Este documento contiene reportes de alto valor que aprovechan las capacidades únicas de los grafos de conocimiento para generar insights estratégicos en la gestión educativa.

---

## 🎯 PARTE 1: Reportes de Alto Valor (Solo posibles con Grafos)

Estos reportes explotan relaciones complejas y múltiples saltos que serían extremadamente difíciles o imposibles de realizar con bases de datos relacionales tradicionales.

---

### 1. **"Efecto Dominó" - Predicción de Deserción en Cadena**

> **Pregunta de negocio:** *"Si pierdo a esta familia, ¿a cuántas más podría perder?"*

**Contexto:** Los padres hablan entre sí. Si un padre influyente retira a sus hijos, otros podrían seguirlo.

**Query Cypher:**
```cypher
// Detectar "nodos influyentes" - familias cuya salida impactaría a otras
MATCH (r1:Responsable)-[:RESPONSABLE_DE]->(e1:Estudiante)-[:CURSA]->(g:Grado)
MATCH (r2:Responsable)-[:RESPONSABLE_DE]->(e2:Estudiante)-[:CURSA]->(g)
WHERE r1 <> r2 AND r1.nivel_riesgo = 'ALTO'

// Contar cuántas familias comparten grado con familias en riesgo alto
WITH r1, g, count(DISTINCT r2) as familias_expuestas,
     collect(DISTINCT r2.erp_id) as ids_expuestos

RETURN r1.nombre + ' ' + r1.apellido as familia_riesgo,
       g.nombre as grado,
       familias_expuestas as familias_que_podrian_seguir,
       r1.deuda_total as deuda_actual
ORDER BY familias_expuestas DESC
```

**Impacto:** Priorizar intervención en familias que, si se van, podrían llevarse a otras.

**¿Por qué necesita grafo?** Analiza "vecindad social" (familias en mismo grado) que sería muy complejo en SQL.

---

### 2. **"Patrón de Contagio" - Morosidad que se Propaga por Grado**

> **Pregunta de negocio:** *"¿La morosidad de un grado está 'contagiando' a familias que antes pagaban bien?"*

**Query Cypher:**
```cypher
// Detectar familias puntuales que empezaron a atrasarse después de que
// su grado alcanzó cierto umbral de morosidad
MATCH (r:Responsable {perfil_pagador: 'PUNTUAL'})-[:RESPONSABLE_DE]->(e:Estudiante)-[:CURSA]->(g:Grado)
MATCH (r)-[p:PAGO]->(c:Cuota)
WHERE p.dias_demora > 15  // Empezó a atrasarse

// Ver si el grado ya tenía alta morosidad cuando empezó el atraso
WITH r, e, g, p.fecha as fecha_primer_atraso

MATCH (otro:Responsable)-[:RESPONSABLE_DE]->(otro_e:Estudiante)-[:CURSA]->(g)
MATCH (otro_e)-[:DEBE]->(c2:Cuota {estado: 'vencida'})
WHERE c2.fecha_vencimiento < fecha_primer_atraso

WITH r, g, count(DISTINCT otro) as morosos_previos_en_grado

WHERE morosos_previos_en_grado > 5  // El grado ya estaba "enfermo"

RETURN r.nombre as familia_contagiada,
       g.nombre as grado,
       morosos_previos_en_grado as contexto_morosidad,
       "INTERVENIR: Familia puntual cayendo en mora por contexto" as accion
```

**Impacto:** Intervenir en familias puntuales que están en grados "tóxicos" antes de que caigan.

**¿Por qué necesita grafo?** Correlaciona comportamiento temporal entre nodos conectados.

---

### 3. **"Hermanos en Riesgo" - Predicción de Retiro Parcial**

> **Pregunta de negocio:** *"¿Qué familias están por retirar UN hijo pero mantener otro?"*

**Query Cypher:**
```cypher
// Familias con 2+ hijos donde UNO tiene deuda muy alta y OTRO no
MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e1:Estudiante)
MATCH (r)-[:RESPONSABLE_DE]->(e2:Estudiante)
WHERE e1 <> e2

// Deuda de cada hermano
OPTIONAL MATCH (e1)-[:DEBE]->(c1:Cuota {estado: 'vencida'})
OPTIONAL MATCH (e2)-[:DEBE]->(c2:Cuota {estado: 'vencida'})

WITH r, e1, e2,
     sum(c1.monto) as deuda_hijo1,
     sum(c2.monto) as deuda_hijo2

// El patrón: uno con mucha deuda, otro con poca o ninguna
WHERE (deuda_hijo1 > 5000 AND coalesce(deuda_hijo2, 0) < 1000)
   OR (deuda_hijo2 > 5000 AND coalesce(deuda_hijo1, 0) < 1000)

RETURN r.nombre + ' ' + r.apellido as familia,
       e1.nombre as hijo_1, e1.grado as grado_1, coalesce(deuda_hijo1, 0) as deuda_1,
       e2.nombre as hijo_2, e2.grado as grado_2, coalesce(deuda_hijo2, 0) as deuda_2,
       "ALERTA: Posible retiro selectivo de un hijo" as prediccion
```

**Impacto:** Detectar y negociar antes de que retiren a un hijo (ingresos parciales perdidos).

**¿Por qué necesita grafo?** Compara estados de múltiples hijos del mismo padre - muy complejo en SQL.

---

### 4. **"Ciclo de Vida del Moroso" - Camino Completo hacia la Deserción**

> **Pregunta de negocio:** *"¿Cuáles son los pasos típicos que sigue una familia antes de desertar?"*

**Query Cypher:**
```cypher
// Analizar la secuencia temporal de señales para familias que ya desertaron
MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e:Estudiante)
WHERE e.estado = 'retirado'  // Estudiantes que ya se fueron

// Reconstruir la línea temporal de eventos
OPTIONAL MATCH (r)-[p:PAGO]->(c:Cuota)
OPTIONAL MATCH (r)-[ig:IGNORO_NOTIFICACION]->(c2:Cuota)
OPTIONAL MATCH (r)-[:CREO_TICKET]->(t:Ticket)

WITH r, e,
     min(p.fecha) as primer_pago,
     max(p.fecha) as ultimo_pago,
     avg(p.dias_demora) as demora_promedio,
     count(ig) as notificaciones_ignoradas,
     count(t) as tickets_creados,
     // Tiempo desde último pago hasta retiro
     duration.between(max(p.fecha), e.fecha_retiro).months as meses_sin_pagar

RETURN 
  CASE 
    WHEN demora_promedio < 10 AND notificaciones_ignoradas = 0 THEN 'SORPRESA - Pagaba bien'
    WHEN demora_promedio > 30 AND notificaciones_ignoradas > 5 THEN 'ESPERADO - Patrón clásico'
    WHEN tickets_creados > 2 THEN 'CONFLICTO - Reclamos previos'
    ELSE 'OTRO'
  END as tipo_desercion,
  count(*) as cantidad,
  avg(meses_sin_pagar) as meses_promedio_sin_pagar,
  avg(demora_promedio) as demora_tipica
ORDER BY cantidad DESC
```

**Impacto:** Entender los "arquetipos de deserción" para intervenir en el momento correcto.

**¿Por qué necesita grafo?** Reconstruye secuencia de eventos a través de múltiples relaciones.

---

### 5. **"Red de Comunicación Fallida" - Canales Muertos**

> **Pregunta de negocio:** *"¿A quién le mandamos mensajes que NUNCA responde pero tampoco paga?"*

**Query Cypher:**
```cypher
// Responsables con muchas interacciones pero cero acción posterior
MATCH (r:Responsable)-[i:INTERACTUO]->(c:Cuota)
MATCH (r)-[:DEBE]->(c)
WHERE c.estado = 'vencida'

// Contar interacciones (mensajes) vs pagos
WITH r,
     count(DISTINCT i) as mensajes_enviados,
     sum(CASE WHEN i.tipo = 'recordatorio' THEN 1 ELSE 0 END) as recordatorios,
     sum(CASE WHEN i.tipo = 'link_pago' THEN 1 ELSE 0 END) as links_enviados

MATCH (r)-[:DEBE]->(c_actual:Cuota {estado: 'vencida'})
WITH r, mensajes_enviados, recordatorios, links_enviados, count(c_actual) as cuotas_sin_pagar

WHERE mensajes_enviados > 10 AND cuotas_sin_pagar > 3

RETURN r.nombre + ' ' + r.apellido as responsable,
       r.whatsapp as telefono,
       mensajes_enviados,
       cuotas_sin_pagar,
       round(toFloat(mensajes_enviados) / cuotas_sin_pagar, 1) as mensajes_por_cuota,
       "CAMBIAR ESTRATEGIA: WhatsApp no funciona" as recomendacion
ORDER BY mensajes_enviados DESC
```

**Impacto:** Dejar de gastar recursos en un canal que no funciona para ciertas personas.

**¿Por qué necesita grafo?** Combina interacciones + pagos + deuda en una sola consulta.

---

### 6. **"Proyección de Flujo de Caja con Contexto Comportamental"** ⭐

> **Pregunta de negocio:** *"¿Cuánto vamos a cobrar REALMENTE el próximo mes?"*

**Query Cypher:**
```cypher
// Cuotas que vencen próximo mes con probabilidad de pago
MATCH (e:Estudiante)-[:DEBE]->(c:Cuota)
WHERE c.estado = 'pendiente'
  AND c.fecha_vencimiento >= date() 
  AND c.fecha_vencimiento < date() + duration('P30D')

MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e)
OPTIONAL MATCH (r)-[:PERTENECE_A]->(cluster:ClusterComportamiento)
OPTIONAL MATCH (r)-[p:PAGO]->(:Cuota)

WITH c, r, e, cluster,
     avg(p.dias_demora) as demora_historica,
     count(p) as pagos_anteriores

// Calcular probabilidad basada en múltiples factores
WITH c, r,
     c.monto as monto,
     CASE cluster.tipo
       WHEN 'PUNTUAL' THEN 0.95
       WHEN 'EVENTUAL' THEN 0.60
       WHEN 'MOROSO' THEN 0.20
       ELSE 0.50
     END as prob_base,
     CASE 
       WHEN demora_historica < 5 THEN 0.10
       WHEN demora_historica > 30 THEN -0.20
       ELSE 0
     END as ajuste_historial,
     CASE r.nivel_riesgo
       WHEN 'ALTO' THEN -0.15
       WHEN 'MEDIO' THEN -0.05
       ELSE 0
     END as ajuste_riesgo

WITH c.fecha_vencimiento as fecha,
     sum(monto) as monto_total,
     sum(monto * (prob_base + ajuste_historial + ajuste_riesgo)) as monto_esperado

RETURN fecha,
       round(monto_total, 2) as facturado,
       round(monto_esperado, 2) as cobranza_esperada,
       round(monto_esperado / monto_total * 100, 1) as pct_recupero_estimado
ORDER BY fecha
```

**Impacto:** Planificación financiera realista, no basada en cuotas emitidas sino en probabilidad real de cobro.

**¿Por qué necesita grafo?** Pondera probabilidad usando cluster + historial + contexto familiar.

---

## 🚀 PARTE 2: Reportes Estratégicos con Datos Adicionales

Estos reportes requieren enriquecer el modelo con datos que un colegio privado típicamente ya tiene pero no está conectando.

---

### Datos Adicionales Necesarios

#### 1. **Datos Académicos**
- Notas/Calificaciones → `(Estudiante)-[:OBTUVO]->(Calificacion)`
- Asistencia → `(Estudiante)-[:ASISTIO]->(DiaClase)`
- Conducta/Sanciones → `(Estudiante)-[:TIENE]->(Sancion)`
- Materias reprobadas → `(Estudiante)-[:REPROBO]->(Materia)`

#### 2. **Datos de Engagement Familiar**
- Asistencia a reuniones → `(Responsable)-[:ASISTIO_A]->(Reunion)`
- Participación en eventos → `(Responsable)-[:PARTICIPO]->(Evento)`
- Comunicación con docentes → `(Responsable)-[:CONTACTO]->(Docente)`
- Quejas/Reclamos académicos → `(Responsable)-[:RECLAMO]->(Incidente)`

#### 3. **Datos Socioeconómicos**
- Tipo de beca/descuento → `(Estudiante)-[:TIENE_BECA]->(Beca)`
- Ocupación de padres → Propiedad en `Responsable`
- Zona/Barrio → `(Responsable)-[:VIVE_EN]->(Zona)`
- Medio de transporte → Propiedad en `Estudiante`

#### 4. **Datos de Servicios Adicionales**
- Transporte escolar → `(Estudiante)-[:USA]->(Transporte)`
- Comedor → `(Estudiante)-[:CONTRATO]->(Comedor)`
- Actividades extra → `(Estudiante)-[:INSCRITO]->(Actividad)`
- Seguro escolar → Propiedad en `Estudiante`

#### 5. **Datos Históricos**
- Año de ingreso → Propiedad en `Estudiante`
- Colegio anterior → `(Estudiante)-[:VINO_DE]->(ColegioAnterior)`
- Hermanos egresados → `(Responsable)-[:TUVO]->(Egresado)`
- Reinscripciones → Propiedad en `Estudiante`

---

### 7. **"Deserción Silenciosa" - Correlación Académica + Financiera**

> **Pregunta de negocio:** *"¿Los alumnos que bajan notas también empiezan a atrasarse en pagos?"*

**Query Cypher:**
```cypher
// Detectar correlación entre caída académica y morosidad
MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e:Estudiante)
MATCH (e)-[:OBTUVO]->(cal:Calificacion)
MATCH (e)-[:DEBE]->(c:Cuota)

WITH e, r,
     avg(cal.nota) as promedio_actual,
     avg(CASE WHEN cal.periodo = 'anterior' THEN cal.nota END) as promedio_anterior,
     count(CASE WHEN c.estado = 'vencida' THEN 1 END) as cuotas_vencidas

WHERE promedio_actual < promedio_anterior - 1.5  // Bajó más de 1.5 puntos
  AND cuotas_vencidas > 0

RETURN e.nombre as alumno,
       e.grado as grado,
       round(promedio_anterior, 1) as promedio_antes,
       round(promedio_actual, 1) as promedio_ahora,
       cuotas_vencidas,
       "⚠️ ALERTA: Caída académica + mora = alto riesgo de retiro" as insight
ORDER BY (promedio_anterior - promedio_actual) DESC
```

**Impacto:** Intervención temprana antes de que la familia decida retirar.

**Datos necesarios:** Calificaciones por período, relación con cuotas.

---

### 8. **"Padres Fantasma" - Engagement vs Morosidad**

> **Pregunta de negocio:** *"¿Los padres que nunca vienen a reuniones son los mismos que no pagan?"*

**Query Cypher:**
```cypher
MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e:Estudiante)

// Engagement: reuniones + eventos
OPTIONAL MATCH (r)-[:ASISTIO_A]->(reunion:Reunion)
WHERE reunion.fecha > date() - duration('P1Y')
OPTIONAL MATCH (r)-[:PARTICIPO]->(evento:Evento)

// Morosidad
OPTIONAL MATCH (r)-[:RESPONSABLE_DE]->(:Estudiante)-[:DEBE]->(c:Cuota {estado: 'vencida'})

WITH r,
     count(DISTINCT reunion) as reuniones_asistidas,
     count(DISTINCT evento) as eventos_participados,
     count(c) as cuotas_vencidas,
     sum(c.monto) as deuda_total

// Padres con CERO engagement y mora
WHERE reuniones_asistidas = 0 AND eventos_participados = 0 AND cuotas_vencidas > 0

RETURN r.nombre + ' ' + r.apellido as responsable,
       r.whatsapp as contacto,
       cuotas_vencidas,
       deuda_total,
       "DESCONECTADO: Sin vínculo con el colegio" as perfil,
       "Llamar personalmente - WhatsApp no alcanza" as accion
ORDER BY deuda_total DESC
```

**Impacto:** Identificar familias "desconectadas" que necesitan otro tipo de acercamiento.

**Datos necesarios:** Registro de asistencia a reuniones y eventos.

---

### 9. **"Efecto Beca" - ROI de Descuentos**

> **Pregunta de negocio:** *"¿Las becas están reteniendo alumnos o estamos subsidiando a quienes igual pagarían?"*

**Query Cypher:**
```cypher
MATCH (e:Estudiante)-[:TIENE_BECA]->(b:Beca)
MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e)

// Comportamiento de pago
OPTIONAL MATCH (r)-[p:PAGO]->(c:Cuota)
OPTIONAL MATCH (e)-[:DEBE]->(cv:Cuota {estado: 'vencida'})

WITH b.tipo as tipo_beca,
     count(DISTINCT e) as alumnos,
     avg(p.dias_demora) as demora_promedio,
     count(cv) as cuotas_vencidas_total,
     sum(b.descuento_mensual) * 10 as costo_anual_becas  // 10 meses

RETURN tipo_beca,
       alumnos,
       round(demora_promedio, 1) as dias_demora_promedio,
       cuotas_vencidas_total,
       costo_anual_becas,
       CASE 
         WHEN demora_promedio < 5 THEN '✅ BECA EFECTIVA'
         WHEN demora_promedio > 20 THEN '❌ REVISAR: Becados que igual no pagan'
         ELSE '⚠️ MONITOREAR'
       END as evaluacion
ORDER BY costo_anual_becas DESC
```

**Impacto:** Optimizar política de becas - dar a quien realmente lo necesita y retiene.

**Datos necesarios:** Tipo y monto de beca por estudiante.

---

### 10. **"Canasta de Servicios" - Predictor de Permanencia**

> **Pregunta de negocio:** *"¿Las familias que contratan más servicios (transporte, comedor, talleres) desertan menos?"*

**Query Cypher:**
```cypher
MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e:Estudiante)

// Servicios contratados
OPTIONAL MATCH (e)-[:USA]->(t:Transporte)
OPTIONAL MATCH (e)-[:CONTRATO]->(com:Comedor)
OPTIONAL MATCH (e)-[:INSCRITO]->(act:Actividad)

WITH r, e,
     CASE WHEN t IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN com IS NOT NULL THEN 1 ELSE 0 END +
     count(DISTINCT act) as servicios_contratados

// Antigüedad y estado
WITH servicios_contratados,
     count(e) as total_alumnos,
     count(CASE WHEN e.estado = 'activo' THEN 1 END) as activos,
     count(CASE WHEN e.estado = 'retirado' THEN 1 END) as retirados

RETURN servicios_contratados as cantidad_servicios,
       total_alumnos,
       activos,
       retirados,
       round(toFloat(retirados) / total_alumnos * 100, 1) as tasa_desercion,
       CASE 
         WHEN servicios_contratados >= 3 THEN '🔒 ALTA RETENCIÓN'
         WHEN servicios_contratados = 0 THEN '⚠️ BAJO ENGAGEMENT'
         ELSE 'NORMAL'
       END as perfil
ORDER BY servicios_contratados
```

**Impacto:** Promover servicios adicionales como estrategia de retención (no solo de ingresos).

**Datos necesarios:** Contratos de transporte, comedor, inscripciones a actividades.

---

### 11. **"Mapa de Riesgo Geográfico" - Zonas Problemáticas**

> **Pregunta de negocio:** *"¿Hay barrios donde la morosidad es sistemáticamente mayor?"*

**Query Cypher:**
```cypher
MATCH (r:Responsable)-[:VIVE_EN]->(z:Zona)
MATCH (r)-[:RESPONSABLE_DE]->(e:Estudiante)-[:DEBE]->(c:Cuota)

WITH z,
     count(DISTINCT r) as familias,
     count(DISTINCT CASE WHEN c.estado = 'vencida' THEN r END) as familias_morosas,
     sum(CASE WHEN c.estado = 'vencida' THEN c.monto ELSE 0 END) as deuda_zona

WITH z, familias, familias_morosas, deuda_zona,
     toFloat(familias_morosas) / familias * 100 as pct_morosidad

RETURN z.nombre as zona,
       z.distancia_km as distancia_colegio,
       familias,
       familias_morosas,
       round(pct_morosidad, 1) as pct_morosidad,
       round(deuda_zona, 0) as deuda_total,
       CASE 
         WHEN pct_morosidad > 40 THEN '🔴 ZONA CRÍTICA'
         WHEN pct_morosidad > 25 THEN '🟡 ZONA RIESGO'
         ELSE '🟢 ZONA ESTABLE'
       END as clasificacion
ORDER BY pct_morosidad DESC
```

**Impacto:** Decisiones sobre transporte escolar, sedes, o incluso marketing geolocalizado.

**Datos necesarios:** Domicilio/barrio de cada responsable, distancia al colegio.

---

### 12. **"Predictor de Reinscripción" - Score Integral**

> **Pregunta de negocio:** *"¿Qué familias NO van a reinscribir el próximo año?"*

**Query Cypher:**
```cypher
MATCH (r:Responsable)-[:RESPONSABLE_DE]->(e:Estudiante)

// Factor 1: Financiero
OPTIONAL MATCH (r)-[p:PAGO]->(c:Cuota)
WITH r, e, avg(p.dias_demora) as demora_pago

// Factor 2: Académico
OPTIONAL MATCH (e)-[:OBTUVO]->(cal:Calificacion)
WITH r, e, demora_pago, avg(cal.nota) as promedio

// Factor 3: Engagement
OPTIONAL MATCH (r)-[:ASISTIO_A]->(reunion:Reunion)
WITH r, e, demora_pago, promedio, count(reunion) as reuniones

// Factor 4: Servicios
OPTIONAL MATCH (e)-[:INSCRITO]->(act:Actividad)
WITH r, e, demora_pago, promedio, reuniones, count(act) as actividades

// Factor 5: Antigüedad
WITH r, e, demora_pago, promedio, reuniones, actividades,
     duration.between(e.fecha_ingreso, date()).years as años_en_colegio

// SCORE DE REINSCRIPCIÓN (0-100)
WITH r, e,
     // Penalizaciones
     CASE WHEN demora_pago > 30 THEN -30 WHEN demora_pago > 15 THEN -15 ELSE 0 END +
     CASE WHEN promedio < 6 THEN -20 WHEN promedio < 7 THEN -10 ELSE 0 END +
     // Bonificaciones
     CASE WHEN reuniones >= 3 THEN 20 WHEN reuniones >= 1 THEN 10 ELSE 0 END +
     CASE WHEN actividades >= 2 THEN 15 ELSE 0 END +
     CASE WHEN años_en_colegio >= 3 THEN 25 WHEN años_en_colegio >= 1 THEN 10 ELSE 0 END +
     50 as score_reinscripcion  // Base

WHERE score_reinscripcion < 50  // Riesgo de NO reinscribir

RETURN e.nombre as alumno,
       e.grado as grado,
       r.nombre + ' ' + r.apellido as responsable,
       score_reinscripcion,
       CASE 
         WHEN score_reinscripcion < 30 THEN '🔴 MUY PROBABLE QUE NO REINSCRIBA'
         ELSE '🟡 RIESGO MODERADO'
       END as prediccion
ORDER BY score_reinscripcion ASC
```

**Impacto:** Lista priorizada para campaña de retención antes del período de reinscripción.

**Datos necesarios:** Historial de pagos, calificaciones, asistencia a reuniones, servicios contratados, fecha de ingreso.

---

## 📋 Resumen: Comparación SQL vs Grafos

| Reporte | ¿Por qué necesita grafo? |
|---------|--------------------------|
| **Efecto Dominó** | Analiza "vecindad social" (familias en mismo grado) |
| **Contagio de Morosidad** | Correlaciona comportamiento temporal entre nodos conectados |
| **Hermanos en Riesgo** | Compara estados de múltiples hijos del mismo padre |
| **Ciclo de Vida** | Reconstruye secuencia de eventos a través de múltiples relaciones |
| **Canales Muertos** | Combina interacciones + pagos + deuda en una sola consulta |
| **Proyección de Caja** | Pondera probabilidad usando cluster + historial + contexto familiar |
| **Deserción Silenciosa** | Correlaciona datos académicos con financieros |
| **Padres Fantasma** | Cruza engagement social con morosidad |
| **Efecto Beca** | Analiza ROI de políticas de descuento |
| **Canasta de Servicios** | Predice retención basado en múltiples servicios |
| **Mapa Geográfico** | Agrupa por ubicación y analiza patrones espaciales |
| **Predictor Reinscripción** | Score multi-dimensional con múltiples factores |

---

## 🔧 Implementación

### Estado Actual
- ✅ Modelo de datos básico implementado
- ✅ ETL desde ERP funcionando
- ✅ Queries básicas en `knowledge_graph/app/queries/`

### Próximos Pasos
1. **Agregar queries de alto valor** a `knowledge_graph/app/queries/reportes_estrategicos.py`
2. **Exponer endpoints** en `knowledge_graph/app/api/reportes.py`
3. **Enriquecer modelo** con datos adicionales (ETL extendido)
4. **Crear dashboard** en frontend para visualizar estos reportes

---

## 📝 Notas

- Todos los queries están listos para implementar
- Algunos requieren datos adicionales que deben agregarse al modelo
- Los umbrales (ej: `> 5000`, `> 30 días`) deben ajustarse según el contexto del colegio
- Se recomienda ejecutar estos reportes periódicamente (semanal/mensual) para detectar tendencias

---

**Última actualización:** Enero 2026

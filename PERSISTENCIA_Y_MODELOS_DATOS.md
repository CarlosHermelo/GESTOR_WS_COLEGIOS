# 💾 Persistencia y Modelos de Datos

Este documento describe cómo se persisten las interacciones de WhatsApp y tickets en el sistema, y los modelos de datos de cada componente.

---

## 🔄 Flujo de Persistencia de Interacciones WhatsApp

### **1. Mensaje del Padre → Gestor WS**

```
┌─────────────────────────────────────────────────────────────────┐
│  PADRE ENVÍA MENSAJE POR WHATSAPP                                │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  POST /webhook/whatsapp (Gestor WS)                              │
│  • Recibe: {from_number, text}                                  │
│  • Procesa con Router/Asistente/Agente                           │
│  • Genera respuesta                                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  REGISTRO INMEDIATO EN POSTGRESQL (Gestor WS)                    │
├─────────────────────────────────────────────────────────────────┤
│  Tabla: interacciones                                            │
│                                                                  │
│  INSERT 1: Mensaje Entrante                                      │
│  • whatsapp_from: "+5491112345001"                              │
│  • tipo: "mensaje_entrante"                                     │
│  • contenido: "Cuánto debo?"                                    │
│  • agente: "usuario"                                            │
│  • timestamp: NOW()                                              │
│                                                                  │
│  INSERT 2: Respuesta del Bot                                    │
│  • whatsapp_from: "+5491112345001"                              │
│  • tipo: "respuesta"                                            │
│  • contenido: "📋 Estado de cuenta:..."                         │
│  • agente: "asistente" | "coordinador" | "router"              │
│  • timestamp: NOW()                                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  SINCRONIZACIÓN A NEO4J (ETL Periódico)                          │
├─────────────────────────────────────────────────────────────────┤
│  ETL: sync_from_gestor.py → sync_interacciones()                │
│  • Lee: interacciones (últimos 30 días)                         │
│  • Filtra: erp_cuota_id IS NOT NULL                             │
│  • Crea en Neo4j:                                                │
│                                                                  │
│    (:Responsable)-[:INTERACTUO {                                 │
│      id: "uuid",                                                │
│      timestamp: datetime,                                        │
│      tipo: "mensaje_entrante" | "respuesta",                   │
│      agente: "asistente" | "coordinador",                      │
│      contenido_preview: "primeros 100 chars"                   │
│    }]->(:Cuota)                                                 │
│                                                                  │
│  ⚠️ NOTA: Solo se sincronizan interacciones que tienen          │
│     erp_cuota_id asociado (relacionadas con una cuota)          │
└─────────────────────────────────────────────────────────────────┘
```

**Archivos:**
- `gestor_ws/app/api/webhooks_whatsapp.py` (líneas 205-234) - Registro en PostgreSQL
- `knowledge_graph/app/etl/sync_from_gestor.py` (líneas 62-118) - Sincronización a Neo4j

---

### **2. Respuesta del Administrador → Padre**

```
┌─────────────────────────────────────────────────────────────────┐
│  ADMIN RESPONDE TICKET (Frontend Admin)                         │
│  PUT /api/admin/tickets/{id}/resolver                          │
│  • Admin escribe respuesta técnica                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  ACTUALIZACIÓN EN POSTGRESQL (Gestor WS)                        │
├─────────────────────────────────────────────────────────────────┤
│  Tabla: tickets                                                 │
│                                                                  │
│  UPDATE tickets                                                 │
│  SET estado = 'resuelto',                                       │
│      respuesta_admin = 'Respuesta técnica...',                  │
│      resolved_at = NOW()                                        │
│  WHERE id = {ticket_id}                                         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  REFORMULACIÓN CON LLM                                          │
├─────────────────────────────────────────────────────────────────┤
│  • procesar_respuesta_admin()                                   │
│  • LLM reformula respuesta técnica → lenguaje amigable          │
│  • Adapta para WhatsApp (corto, emojis, cercano)                │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  ENVÍO POR WHATSAPP                                              │
├─────────────────────────────────────────────────────────────────┤
│  • whatsapp_service.send_message(phone_number, respuesta)       │
│  • Envía mensaje reformulado al padre                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  ¿SE REGISTRA EN INTERACCIONES?                                  │
├─────────────────────────────────────────────────────────────────┤
│  ❌ NO - Las respuestas de admin NO se registran                │
│     automáticamente en la tabla interacciones                    │
│                                                                  │
│  ✅ SÍ - Se actualiza el ticket en PostgreSQL                   │
│     y luego se sincroniza a Neo4j en el próximo ETL            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  SINCRONIZACIÓN A NEO4J (ETL Periódico)                          │
├─────────────────────────────────────────────────────────────────┤
│  ETL: sync_from_gestor.py → sync_tickets()                      │
│  • Lee: tickets (todos, no solo resueltos)                      │
│  • Crea en Neo4j:                                               │
│                                                                  │
│    (:Ticket {                                                    │
│      id: "uuid",                                                │
│      categoria: "plan_pago" | "reclamo" | "baja" | ...         │
│      prioridad: "baja" | "media" | "alta",                      │
│      estado: "pendiente" | "en_proceso" | "resuelto",          │
│      created_at: datetime,                                      │
│      resolved_at: datetime | null                              │
│    })                                                            │
│                                                                  │
│    (:Responsable)-[:CREO_TICKET]->(:Ticket)                     │
│                                                                  │
│  ⚠️ NOTA: El ticket se sincroniza completo, incluyendo          │
│     estado y resolved_at, pero NO incluye respuesta_admin       │
│     (solo metadatos del ticket)                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Archivos:**
- `gestor_ws/app/api/admin.py` (líneas 119-172) - Resolver ticket
- `gestor_ws/app/api/admin.py` (líneas 268-292) - Enviar respuesta
- `knowledge_graph/app/etl/sync_from_gestor.py` (líneas 171-227) - Sincronizar tickets

---

## 📊 Modelos de Datos por Sistema

### **1. ERP MOCK (PostgreSQL)**

**Base de datos:** `erp_mock`  
**Puerto:** 5433

#### **Tablas:**

**`erp_responsables`**
```sql
CREATE TABLE erp_responsables (
    id VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    whatsapp VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(200),
    tipo VARCHAR(20)  -- padre, madre, tutor
);
```

**`erp_alumnos`**
```sql
CREATE TABLE erp_alumnos (
    id VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE,
    grado VARCHAR(50),
    activo BOOLEAN DEFAULT TRUE
);
```

**`erp_responsabilidad`** (Tabla intermedia)
```sql
CREATE TABLE erp_responsabilidad (
    responsable_id VARCHAR(50) REFERENCES erp_responsables(id),
    alumno_id VARCHAR(50) REFERENCES erp_alumnos(id),
    PRIMARY KEY (responsable_id, alumno_id)
);
```

**`erp_planes_pago`**
```sql
CREATE TABLE erp_planes_pago (
    id VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(100),
    cantidad_cuotas INTEGER,
    monto_cuota NUMERIC(10, 2),
    anio INTEGER
);
```

**`erp_cuotas`**
```sql
CREATE TABLE erp_cuotas (
    id VARCHAR(50) PRIMARY KEY,
    alumno_id VARCHAR(50) REFERENCES erp_alumnos(id) NOT NULL,
    plan_pago_id VARCHAR(50) REFERENCES erp_planes_pago(id),
    numero_cuota INTEGER,
    monto NUMERIC(10, 2) NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    estado VARCHAR(20),  -- pendiente, pagada, vencida
    link_pago TEXT,
    fecha_pago TIMESTAMP
);
```

**`erp_pagos`**
```sql
CREATE TABLE erp_pagos (
    id VARCHAR(50) PRIMARY KEY,
    cuota_id VARCHAR(50) REFERENCES erp_cuotas(id) NOT NULL,
    monto NUMERIC(10, 2) NOT NULL,
    fecha_pago TIMESTAMP NOT NULL,
    metodo_pago VARCHAR(50),
    referencia VARCHAR(100)
);
```

**Archivos:**
- `erp_mock/app/models.py`

---

### **2. GESTOR WS (PostgreSQL)**

**Base de datos:** `gestor_ws`  
**Puerto:** 5432

#### **Tablas de CACHE (Réplica del ERP):**

**`cache_responsables`**
```sql
CREATE TABLE cache_responsables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_responsable_id VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(200),
    apellido VARCHAR(200),
    whatsapp VARCHAR(20) UNIQUE,
    email VARCHAR(200),
    ultima_sync TIMESTAMP DEFAULT NOW()
);
```

**`cache_alumnos`**
```sql
CREATE TABLE cache_alumnos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_alumno_id VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(200),
    apellido VARCHAR(200),
    grado VARCHAR(100),
    erp_responsable_id VARCHAR(100),
    ultima_sync TIMESTAMP DEFAULT NOW()
);
```

**`cache_cuotas`**
```sql
CREATE TABLE cache_cuotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_cuota_id VARCHAR(100) UNIQUE NOT NULL,
    erp_alumno_id VARCHAR(100),
    monto DECIMAL(10,2),
    fecha_vencimiento DATE,
    estado VARCHAR(50),  -- pendiente, pagada, vencida
    link_pago TEXT,
    fecha_pago TIMESTAMP,
    ultima_sync TIMESTAMP DEFAULT NOW()
);
```

#### **Tablas PROPIAS del Gestor WS:**

**`interacciones`**
```sql
CREATE TABLE interacciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_from VARCHAR(20) NOT NULL,
    erp_alumno_id VARCHAR(100),
    erp_cuota_id VARCHAR(100),  -- ⚠️ Importante: para vincular con Neo4j
    tipo VARCHAR(50),  -- mensaje_entrante, respuesta, confirmacion_pago, etc.
    contenido TEXT,
    agente VARCHAR(20),  -- usuario, asistente, coordinador, router
    extra_data JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

**`tickets`**
```sql
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_alumno_id VARCHAR(100) NOT NULL,
    erp_responsable_id VARCHAR(100),
    categoria VARCHAR(50),  -- plan_pago, reclamo, baja, consulta_admin
    motivo TEXT,
    contexto JSONB,  -- {phone_number, mensajes, timestamp}
    estado VARCHAR(20) DEFAULT 'pendiente',  -- pendiente, en_proceso, resuelto
    prioridad VARCHAR(20) DEFAULT 'media',  -- baja, media, alta
    respuesta_admin TEXT,  -- Respuesta técnica del admin
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);
```

**`notificaciones_enviadas`**
```sql
CREATE TABLE notificaciones_enviadas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    erp_cuota_id VARCHAR(100) NOT NULL,
    whatsapp_to VARCHAR(20),
    tipo VARCHAR(50),  -- recordatorio_d7, recordatorio_d3, recordatorio_d1, confirmacion_pago
    fecha_envio TIMESTAMP DEFAULT NOW(),
    leido BOOLEAN DEFAULT FALSE
);
```

**`sincronizaciones_log`**
```sql
CREATE TABLE sincronizaciones_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo VARCHAR(50),  -- alumno, cuota, responsable, pago
    erp_id VARCHAR(100),
    accion VARCHAR(20),  -- create, update, delete
    timestamp TIMESTAMP DEFAULT NOW(),
    payload JSONB
);
```

**Archivos:**
- `gestor_ws/app/models/interacciones.py`
- `gestor_ws/app/models/tickets.py`
- `gestor_ws/app/models/cache.py`
- `gestor_ws/app/database.py` (CREATE_TABLES_SQL)

---

### **3. NEO4J KNOWLEDGE GRAPH**

**Base de datos:** Neo4j 5  
**Puerto:** 7687 (Bolt), 7474 (Browser)

#### **Nodos:**

**`(:Responsable)`**
```cypher
{
  erp_id: String (único),
  nombre: String,
  apellido: String,
  whatsapp: String,
  email: String,
  perfil_pagador: String,  // PUNTUAL, EVENTUAL, MOROSO, NUEVO (LLM)
  nivel_riesgo: String,    // BAJO, MEDIO, ALTO (LLM)
  patrones_detectados: List<String>,  // (LLM)
  razon_clasificacion: String,  // (LLM)
  clasificado_por_llm: String,  // "openai/gpt-4" | "gemini/gemini-pro"
  ultima_clasificacion: DateTime,
  ultima_sync: DateTime
}
```

**`(:Estudiante)`**
```cypher
{
  erp_id: String (único),
  nombre: String,
  apellido: String,
  grado: String,
  ultima_sync: DateTime
}
```

**`(:Cuota)`**
```cypher
{
  erp_id: String (único),
  monto: Float,
  fecha_vencimiento: Date,
  estado: String,  // pendiente, pagada, vencida
  link_pago: String,
  ultima_sync: DateTime
}
```

**`(:Grado)`**
```cypher
{
  nombre: String (único)
}
```

**`(:Ticket)`**
```cypher
{
  id: String (UUID, único),
  categoria: String,  // plan_pago, reclamo, baja, consulta_admin
  prioridad: String,  // baja, media, alta
  estado: String,    // pendiente, en_proceso, resuelto
  created_at: DateTime,
  resolved_at: DateTime | null
}
```

**`(:ClusterComportamiento)`**
```cypher
{
  tipo: String (único),  // "PUNTUAL_BAJO", "MOROSO_ALTO", etc.
  perfil: String,
  riesgo: String,
  descripcion: String,  // (LLM)
  caracteristicas: List<String>,  // (LLM)
  recomendaciones: List<String>,  // (LLM)
  estrategia: String,  // (LLM)
  cantidad_miembros: Integer,
  generado_por_llm: String,
  ultima_actualizacion: DateTime
}
```

**`(:InsightsPredictivos)`**
```cypher
{
  id: String (único, siempre "latest"),
  tendencias: List<String>,  // (LLM)
  riesgos: List<String>,     // (LLM)
  oportunidades: List<String>,  // (LLM)
  acciones: List<String>,    // (LLM)
  metricas: String (JSON),   // Métricas agregadas
  generado_por_llm: String,
  timestamp: DateTime
}
```

#### **Relaciones:**

```cypher
(:Responsable)-[:RESPONSABLE_DE]->(:Estudiante)
(:Estudiante)-[:CURSA]->(:Grado)
(:Estudiante)-[:DEBE]->(:Cuota)
(:Responsable)-[:PAGO {fecha: DateTime, monto: Float, dias_demora: Integer}]->(:Cuota)
(:Responsable)-[:INTERACTUO {id: String, timestamp: DateTime, tipo: String, agente: String, contenido_preview: String}]->(:Cuota)
(:Responsable)-[:IGNORO_NOTIFICACION {id: String, fecha: DateTime, tipo_notif: String}]->(:Cuota)
(:Responsable)-[:CREO_TICKET]->(:Ticket)
(:Responsable)-[:PERTENECE_A]->(:ClusterComportamiento)
```

**Archivos:**
- `knowledge_graph/app/etl/sync_from_erp.py` - Sincronización desde ERP
- `knowledge_graph/app/etl/sync_from_gestor.py` - Sincronización desde Gestor WS
- `knowledge_graph/app/etl/llm_enrichment.py` - Enriquecimiento con LLM

---

### **4. FRONTEND ADMIN (TypeScript Interfaces)**

**No tiene base de datos propia**, solo consume APIs del Gestor WS.

#### **Interfaces Principales:**

**`Ticket`**
```typescript
interface Ticket {
  id: string;
  erp_alumno_id: string;
  erp_responsable_id?: string;
  categoria: 'plan_pago' | 'reclamo' | 'baja' | 'consulta_admin';
  motivo: string;
  contexto: {
    phone_number: string;
    mensajes: string[];
    timestamp: string;
  };
  estado: 'pendiente' | 'en_proceso' | 'resuelto';
  prioridad: 'baja' | 'media' | 'alta';
  respuesta_admin?: string;
  created_at: string;
  resolved_at?: string;
}
```

**`Interaccion`**
```typescript
interface Interaccion {
  id: string;
  whatsapp_from: string;
  erp_alumno_id?: string;
  erp_cuota_id?: string;
  tipo: string;
  contenido: string;
  agente: string;
  timestamp: string;
}
```

**Archivos:**
- `frontend_admin/src/types/ticket.ts`
- `frontend_admin/src/api/tickets.ts`

---

## 🔄 Resumen de Persistencia

### **Interacciones WhatsApp (Padre → Bot)**

| Paso | Sistema | Tabla/Modelo | ¿Cuándo? |
|------|---------|--------------|----------|
| 1. Mensaje recibido | Gestor WS | `interacciones` (tipo: "mensaje_entrante") | Inmediato (background task) |
| 2. Respuesta generada | Gestor WS | `interacciones` (tipo: "respuesta") | Inmediato (background task) |
| 3. Sincronización a Neo4j | Knowledge Graph | Relación `[:INTERACTUO]` | ETL periódico (diario 2 AM o manual) |

**Condición para Neo4j:** Solo se sincronizan interacciones que tienen `erp_cuota_id` asociado.

---

### **Tickets (Admin → Padre)**

| Paso | Sistema | Tabla/Modelo | ¿Cuándo? |
|------|---------|--------------|----------|
| 1. Ticket creado | Gestor WS | `tickets` (estado: "pendiente") | Cuando Agente Coordinador no puede resolver |
| 2. Admin responde | Gestor WS | `tickets` (estado: "resuelto", respuesta_admin) | Cuando admin resuelve ticket |
| 3. Mensaje enviado | WhatsApp | Envío directo (no se persiste) | Inmediato después de resolver |
| 4. Sincronización a Neo4j | Knowledge Graph | Nodo `(:Ticket)` + Relación `[:CREO_TICKET]` | ETL periódico (diario 2 AM o manual) |

**Nota:** La respuesta del admin NO se persiste en `interacciones`, solo en `tickets.respuesta_admin`.

---

## ⚠️ Puntos Importantes

### **1. Interacciones sin `erp_cuota_id`**

Si un mensaje del padre NO está relacionado con una cuota específica (ej: "Hola", "¿Cómo estás?"), **NO se sincroniza a Neo4j** porque el ETL filtra por `erp_cuota_id IS NOT NULL`.

**Query del ETL:**
```sql
SELECT ... 
FROM interacciones i
WHERE i.timestamp > NOW() - INTERVAL '30 days'
  AND i.erp_cuota_id IS NOT NULL  -- ⚠️ Filtro importante
  AND cr.erp_responsable_id IS NOT NULL
```

---

### **2. Respuestas de Admin NO en Interacciones**

Cuando el admin responde un ticket:
- ✅ Se actualiza `tickets.respuesta_admin`
- ✅ Se envía mensaje por WhatsApp
- ❌ **NO se crea registro en `interacciones`**

Esto significa que las respuestas de admin **NO aparecen en el historial de interacciones** de PostgreSQL, pero **SÍ se sincronizan a Neo4j como parte del ticket**.

---

### **3. Sincronización Periódica**

La sincronización a Neo4j NO es en tiempo real:
- **ETL Nocturno:** Diario a las 2:00 AM (completo)
- **ETL Incremental:** Cada 6 horas (solo cuotas y pagos)
- **Manual:** Via API `POST /api/v1/reportes/etl/sync-gestor`

**Archivos:**
- `knowledge_graph/app/etl/scheduler.py` - Tareas programadas

---

## 📋 Diagrama de Flujo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                    PADRE ENVÍA MENSAJE                          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Gestor WS: POST /webhook/whatsapp                               │
│  • Procesa mensaje                                               │
│  • Genera respuesta                                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PostgreSQL (Gestor WS)                                          │
│  • INSERT interacciones (mensaje_entrante)                       │
│  • INSERT interacciones (respuesta)                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  ETL Periódico (Knowledge Graph)                                 │
│  • sync_interacciones()                                          │
│  • Filtra: erp_cuota_id IS NOT NULL                              │
│  • Crea: (:Responsable)-[:INTERACTUO]->(:Cuota)                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Si requiere escalamiento:                                       │
│  • Agente Coordinador crea ticket                                │
│  • INSERT tickets (estado: pendiente)                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Admin responde ticket (Frontend)                                 │
│  • UPDATE tickets (estado: resuelto, respuesta_admin)            │
│  • LLM reformula respuesta                                       │
│  • Envía por WhatsApp                                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  ETL Periódico (Knowledge Graph)                                 │
│  • sync_tickets()                                                │
│  • Crea: (:Ticket) + (:Responsable)-[:CREO_TICKET]->(:Ticket)    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔗 Archivos Clave

| Archivo | Descripción |
|---------|-------------|
| `gestor_ws/app/models/interacciones.py` | Modelo de interacciones (PostgreSQL) |
| `gestor_ws/app/models/tickets.py` | Modelo de tickets (PostgreSQL) |
| `gestor_ws/app/api/webhooks_whatsapp.py` | Registro de interacciones |
| `gestor_ws/app/api/admin.py` | Resolución de tickets |
| `knowledge_graph/app/etl/sync_from_gestor.py` | Sincronización a Neo4j |
| `erp_mock/app/models.py` | Modelos del ERP Mock |
| `gestor_ws/app/database.py` | Esquema SQL de Gestor WS |

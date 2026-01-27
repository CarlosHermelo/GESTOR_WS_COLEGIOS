# 🤖 Flujo Completo del Agente Automático

Este documento describe el flujo completo del sistema de agente automático, desde la recepción de mensajes de WhatsApp hasta la resolución de consultas y tickets.

---

## 📊 Diagrama de Flujo General

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENTRADA: MENSAJE WHATSAPP                    │
├─────────────────────────────────────────────────────────────────┤
│  • Webhook de WhatsApp (Meta/WhatsApp Business API)            │
│  • Mensaje entrante: {from_number, text}                       │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 1: ROUTING (CAPA 1)                     │
├─────────────────────────────────────────────────────────────────┤
│  📥 router.py - MessageRouter                                   │
│     • route(mensaje) → Analiza keywords                        │
│     • Clasifica en:                                             │
│       - SALUDO: Mensajes cortos con keywords de saludo         │
│       - ASISTENTE: Consultas simples (cuotas, deuda, links)    │
│       - AGENTE: Casos complejos (reclamos, bajas, planes)     │
│                                                                  │
│  Keywords detectados:                                          │
│  • SIMPLE: "cuanto debo", "saldo", "link", "pagar", etc.      │
│  • ESCALAMIENTO: "reclamo", "baja", "plan de pago", etc.       │
│  • SALUDO: "hola", "buenos días", etc.                        │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  ¿Qué ruta?   │
                    └───────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│    SALUDO     │  │   ASISTENTE   │  │    AGENTE     │
│   (Router)    │  │   (Capa 2)    │  │  (Capa 3)     │
└───────────────┘  └───────────────┘  └───────────────┘
        │                   │                   │
        │                   ▼                   ▼
        │      ┌──────────────────────────────┐
        │      │  ASISTENTE VIRTUAL           │
        │      │  (LLM + Tools)                │
        │      ├──────────────────────────────┤
        │      │  • consultar_estado_cuenta()  │
        │      │  • obtener_link_pago()        │
        │      │  • registrar_confirmacion()   │
        │      │  • escalar_a_agente()         │
        │      └──────────────────────────────┘
        │                   │
        │                   ▼
        │      ┌──────────────────────────────┐
        │      │  ¿Puede resolver?            │
        │      └──────────────────────────────┘
        │                   │
        │        ┌──────────┴──────────┐
        │        │                     │
        │        ▼                     ▼
        │   ┌─────────┐         ┌──────────────┐
        │   │  SÍ     │         │  NO/Escalar  │
        │   │ Responde│         │  → AGENTE    │
        │   └─────────┘         └──────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 2: AGENTE COORDINADOR (CAPA 3)          │
├─────────────────────────────────────────────────────────────────┤
│  🧠 coordinador.py - AgenteAutonomo (LangGraph)                │
│                                                                  │
│  Grafo de Estados (LangGraph):                                  │
│                                                                  │
│  START                                                           │
│    │                                                             │
│    ▼                                                             │
│  [clasificar] → Clasifica consulta con LLM                    │
│    │                                                             │
│    ├─→ categoría: plan_pago, reclamo, baja, consulta_admin     │
│    ├─→ prioridad: baja, media, alta                            │
│    │                                                             │
│    ▼                                                             │
│  [decidir_ruta] → ¿Resolver o Escalar?                        │
│    │                                                             │
│    ├─→ "resolver" ──────────────┐                              │
│    │                              │                              │
│    ├─→ "escalar" ────────────────┼──┐                           │
│    │                              │  │                           │
│    ▼                              ▼  │                           │
│  [intentar_resolver]         [crear_ticket]                     │
│    │                              │                              │
│    │  • Informa sobre proceso    │  • Crea ticket en BD        │
│    │  • Da respuesta inicial      │  • Guarda contexto          │
│    │                              │                              │
│    ▼                              ▼                              │
│  [validar_resolucion]      [generar_respuesta_espera]           │
│    │                              │                              │
│    ├─→ "exito" → END              │  • Genera mensaje           │
│    │                              │    de espera                 │
│    └─→ "fallo" ──────────────────┘                              │
│                                    │                              │
│                                    ▼                              │
│                                  END                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 3: ENVÍO DE RESPUESTA                    │
├─────────────────────────────────────────────────────────────────┤
│  📤 whatsapp_service.py                                         │
│     • send_message(whatsapp, respuesta)                          │
│     • Envía respuesta por WhatsApp Business API                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 4: REGISTRO DE INTERACCIÓN               │
├─────────────────────────────────────────────────────────────────┤
│  📝 registrar_interaccion() (Background Task)                   │
│     • Guarda mensaje entrante en BD                             │
│     • Guarda respuesta del bot en BD                            │
│     • Registra: whatsapp, contenido, agente, timestamp           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 5: RESOLUCIÓN DE TICKETS                 │
│                    (Si se creó ticket)                          │
├─────────────────────────────────────────────────────────────────┤
│  👤 Admin responde ticket (Frontend Admin)                       │
│     • PUT /api/admin/tickets/{id}/resolver                      │
│     • Admin escribe respuesta técnica                           │
│                                                                  │
│  🔄 Reformulación con LLM                                        │
│     • procesar_respuesta_admin()                                 │
│     • LLM reformula respuesta técnica → lenguaje amigable        │
│     • Adapta para WhatsApp (corto, emojis, cercano)              │
│                                                                  │
│  📤 Envío al padre                                               │
│     • whatsapp_service.send_message()                           │
│     • Ticket marcado como "resuelto"                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo Detallado por Fase

### **FASE 1: ROUTING (Capa 1 - Sin LLM)**

#### 1.1 Recepción del Mensaje (`webhooks_whatsapp.py`)

**Endpoint:** `POST /webhook/whatsapp`

**Proceso:**

```python
# 1. Recibe mensaje de WhatsApp
whatsapp_from = message.from_number
texto = message.text

# 2. Router clasifica el mensaje
router_service = get_router_service()
ruta = router_service.route(texto)  # → RouteType.SALUDO | ASISTENTE | AGENTE
```

**Archivos:**
- `gestor_ws/app/api/webhooks_whatsapp.py` (líneas 71-120)

---

#### 1.2 Clasificación por Keywords (`router.py`)

**Proceso:**

```python
def route(message: str) -> RouteType:
    msg_lower = message.lower().strip()
    
    # 1. Verificar escalamiento (prioridad)
    if contiene_keywords(msg_lower, KEYWORDS_ESCALAMIENTO):
        return RouteType.AGENTE  # → Agente Coordinador
    
    # 2. Verificar consultas simples
    if contiene_keywords(msg_lower, KEYWORDS_SIMPLE):
        return RouteType.ASISTENTE  # → Asistente Virtual
    
    # 3. Verificar saludos (solo si es corto)
    if len(msg_lower) < 30 and contiene_keywords(msg_lower, KEYWORDS_SALUDO):
        return RouteType.SALUDO  # → Respuesta predefinida
    
    # 4. Por defecto → Asistente
    return RouteType.ASISTENTE
```

**Keywords:**

- **SIMPLE** (→ Asistente):
  - "cuanto debo", "cuánto debo", "saldo", "link", "pagar", "vencimiento", "cuota", "pendiente", "deuda", "estado de cuenta", "mis hijos", "alumno"

- **ESCALAMIENTO** (→ Agente):
  - "reclamo", "queja", "baja", "urgente", "error", "problema", "hablar con alguien", "humano", "plan de pago", "plan de pagos", "descuento", "beca", "no puedo pagar", "dificultad", "injusto", "mal cobro"

- **SALUDO** (→ Respuesta predefinida):
  - "hola", "buenos días", "buenas tardes", "buenas noches", "buen día", "hey", "hi"

**Archivos:**
- `gestor_ws/app/agents/router.py`

---

### **FASE 2: ASISTENTE VIRTUAL (Capa 2 - LLM + Tools)**

#### 2.1 Procesamiento con LLM (`asistente.py`)

**Proceso:**

```python
async def responder(whatsapp: str, mensaje: str, historial: Optional[list] = None):
    # 1. Construir historial de chat (últimos 5 mensajes)
    chat_history = []
    if historial:
        for msg in historial[-5:]:
            if msg["from"] == "usuario":
                chat_history.append(HumanMessage(content=msg["text"]))
            else:
                chat_history.append(AIMessage(content=msg["text"]))
    
    # 2. Invocar agente con herramientas
    result = await self.agent_executor.ainvoke({
        "input": mensaje,
        "whatsapp": whatsapp,
        "chat_history": chat_history
    })
    
    # 3. Retornar respuesta
    return result.get("output", "")
```

**System Prompt:**
- Define rol: asistente de cobranza del Colegio
- Permite: informar cuotas, enviar links, registrar pagos
- No permite: modificar montos, ofrecer planes, dar de baja
- Reglas: conciso, amigable, emojis moderados, formatear montos

**Archivos:**
- `gestor_ws/app/agents/asistente.py`

---

#### 2.2 Herramientas Disponibles (`consultar_erp.py`)

El asistente tiene acceso a 4 herramientas:

**1. `consultar_estado_cuenta(whatsapp: str)`**
- Consulta cuotas pendientes del responsable
- Retorna estado de cuenta con montos y fechas
- Usa: `erp_client.get_responsable_by_whatsapp()` y `erp_client.get_alumno_cuotas()`

**2. `obtener_link_pago(cuota_id: str)`**
- Obtiene link de pago de una cuota específica
- Retorna link, monto y fecha de vencimiento
- Usa: `erp_client.get_cuota()`

**3. `registrar_confirmacion_pago(cuota_id: str, whatsapp: str)`**
- Registra confirmación de pago del padre
- Crea interacción tipo "confirmacion_pago"
- Estado: "pendiente_validacion"

**4. `escalar_a_agente(motivo: str, categoria: str)`**
- Escala consulta al Agente Coordinador
- Retorna: `"__ESCALAR__|{categoria}|{motivo}"`
- Categorías: plan_pago, reclamo, baja, consulta_admin

**Archivos:**
- `gestor_ws/app/tools/consultar_erp.py`

---

#### 2.3 Escalamiento desde Asistente

Si el asistente decide escalar (usa herramienta `escalar_a_agente`):

```python
# Respuesta del asistente contiene: "__ESCALAR__|categoria|motivo"
if respuesta.startswith("__ESCALAR__"):
    parts = respuesta.split("|")
    categoria = parts[1]  # plan_pago, reclamo, etc.
    motivo = parts[2]
    
    # Pasar al Agente Coordinador
    agente_coord = get_agente()
    respuesta = await agente_coord.procesar(whatsapp_from, texto)
```

**Archivos:**
- `gestor_ws/app/api/webhooks_whatsapp.py` (líneas 108-115)

---

### **FASE 3: AGENTE COORDINADOR (Capa 3 - LangGraph)**

#### 3.1 Construcción del Grafo (`coordinador.py`)

**Grafo de Estados (LangGraph):**

```python
workflow = StateGraph(ConversationState)

# Nodos
workflow.add_node("clasificar", self.clasificar_consulta)
workflow.add_node("intentar_resolver", self.intentar_resolucion)
workflow.add_node("crear_ticket", self.crear_ticket)
workflow.add_node("generar_respuesta_espera", self.generar_respuesta_espera)

# Punto de entrada
workflow.set_entry_point("clasificar")

# Edges condicionales
workflow.add_conditional_edges(
    "clasificar",
    self.decidir_ruta,
    {
        "resolver": "intentar_resolver",
        "escalar": "crear_ticket",
        "error": END
    }
)

workflow.add_conditional_edges(
    "intentar_resolver",
    self.validar_resolucion,
    {
        "exito": END,
        "fallo": "crear_ticket"
    }
)

workflow.add_edge("crear_ticket", "generar_respuesta_espera")
workflow.add_edge("generar_respuesta_espera", END)
```

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 65-103)

---

#### 3.2 Nodo: Clasificar Consulta (`clasificar_consulta()`)

**Proceso:**

1. **Construye prompt para LLM:**
   ```
   Clasifica esta consulta de un padre/responsable de alumnos:
   
   Mensaje: {ultimo_mensaje}
   
   Categorías posibles:
   - plan_pago: Solicita plan de pagos, financiación
   - reclamo: Queja sobre cobros, errores, mal servicio
   - baja: Solicita dar de baja al alumno
   - consulta_admin: Otra consulta que requiere administración
   
   Prioridades:
   - baja: Consultas generales
   - media: Solicitudes normales
   - alta: Urgencias, reclamos graves
   ```

2. **LLM clasifica** y retorna JSON:
   ```json
   {
     "categoria": "plan_pago|reclamo|baja|consulta_admin",
     "prioridad": "baja|media|alta",
     "requiere_humano": true|false,
     "razon": "breve explicación"
   }
   ```

3. **Actualiza estado:**
   ```python
   state["categoria"] = clasificacion.get("categoria")
   state["prioridad"] = clasificacion.get("prioridad")
   ```

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 105-167)

---

#### 3.3 Nodo: Decidir Ruta (`decidir_ruta()`)

**Lógica de decisión:**

```python
def decidir_ruta(state: ConversationState) -> str:
    if state.get("error"):
        return "error"
    
    # Categorías que siempre escalan
    categorias_escalar = ["baja", "reclamo"]
    
    if state.get("categoria") in categorias_escalar:
        return "escalar"  # → crear_ticket
    
    # Plan de pago intentamos resolver primero
    if state.get("categoria") == "plan_pago":
        return "resolver"  # → intentar_resolver
    
    # Por defecto, intentar resolver
    return "resolver"
```

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 169-185)

---

#### 3.4 Nodo: Intentar Resolución (`intentar_resolucion()`)

**Proceso:**

```python
async def intentar_resolucion(state: ConversationState):
    categoria = state.get("categoria", "")
    
    if categoria == "plan_pago":
        # Informar sobre proceso
        state["respuesta_final"] = (
            "Entiendo que necesitás un plan de pagos. 📝\n\n"
            "Para solicitar un plan de pagos, necesito derivar tu "
            "consulta al área administrativa.\n\n"
            "Ellos evaluarán tu situación y te contactarán con "
            "las opciones disponibles.\n\n"
            "¿Querés que proceda con la solicitud?"
        )
        return state
    
    elif categoria == "consulta_admin":
        state["respuesta_final"] = (
            "Tu consulta requiere atención del área administrativa. 📋\n\n"
            "Voy a crear un ticket para que te respondan a la brevedad.\n\n"
            "Normalmente responden en menos de 24 horas hábiles."
        )
        return state
    
    # Si no se puede resolver
    state["respuesta_final"] = None
    return state
```

**Nota:** Aunque se da respuesta inicial, siempre se valida y generalmente se escala.

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 187-226)

---

#### 3.5 Nodo: Validar Resolución (`validar_resolucion()`)

**Lógica:**

```python
def validar_resolucion(state: ConversationState) -> str:
    # Para plan_pago y consulta_admin, siempre escalamos
    # aunque hayamos dado una respuesta inicial
    if state.get("categoria") in ["plan_pago", "consulta_admin"]:
        return "fallo"  # → crear_ticket
    
    if state.get("respuesta_final"):
        return "exito"  # → END
    
    return "fallo"  # → crear_ticket
```

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 228-238)

---

#### 3.6 Nodo: Crear Ticket (`crear_ticket()`)

**Proceso:**

```python
async def crear_ticket(state: ConversationState):
    ticket = Ticket.crear(
        erp_alumno_id=state.get("erp_alumno_id"),
        erp_responsable_id=state.get("erp_responsable_id"),
        categoria=state.get("categoria", "consulta_admin"),
        motivo=state["messages"][-1],
        contexto={
            "phone_number": state["phone_number"],
            "mensajes": state["messages"],
            "timestamp": datetime.now().isoformat()
        },
        prioridad=state.get("prioridad", "media")
    )
    
    session.add(ticket)
    await session.commit()
    
    state["ticket_id"] = str(ticket.id)
    return state
```

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 240-273)

---

#### 3.7 Nodo: Generar Respuesta de Espera (`generar_respuesta_espera()`)

**Proceso:**

Genera mensaje según categoría del ticket:

```python
respuestas = {
    "plan_pago": (
        "✅ Registré tu solicitud de plan de pagos.\n\n"
        f"📝 Ticket: #{ticket_id[:8]}\n\n"
        "El área administrativa va a evaluar tu situación y te "
        "contactará por este medio con las opciones disponibles.\n\n"
        "⏰ Tiempo estimado de respuesta: 24-48 horas hábiles."
    ),
    "reclamo": (
        "📋 Tu reclamo fue registrado correctamente.\n\n"
        f"📝 Ticket: #{ticket_id[:8]}\n\n"
        "Un representante del colegio va a revisar tu caso y "
        "te contactará para darle solución.\n\n"
        "⏰ Tiempo estimado de respuesta: 24 horas hábiles."
    ),
    "baja": (
        "📝 Tu solicitud de baja fue registrada.\n\n"
        f"Ticket: #{ticket_id[:8]}\n\n"
        "El área administrativa se comunicará contigo para "
        "continuar con el proceso.\n\n"
        "⚠️ Recordá que pueden aplicarse políticas de baja anticipada."
    ),
    "consulta_admin": (
        "✅ Tu consulta fue derivada al área administrativa.\n\n"
        f"📝 Ticket: #{ticket_id[:8]}\n\n"
        "Te responderán a la brevedad por este medio.\n\n"
        "⏰ Tiempo estimado: 24-48 horas hábiles."
    )
}

state["respuesta_final"] = respuestas.get(categoria, respuestas["consulta_admin"])
```

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 275-316)

---

### **FASE 4: ENVÍO DE RESPUESTA**

#### 4.1 Envío por WhatsApp (`whatsapp_service.py`)

**Proceso:**

```python
whatsapp_service = get_whatsapp_service()
await whatsapp_service.send_message(whatsapp_from, respuesta)
```

**Archivos:**
- `gestor_ws/app/services/whatsapp_service.py`
- `gestor_ws/app/api/webhooks_whatsapp.py` (línea 124)

---

#### 4.2 Registro de Interacción (`registrar_interaccion()`)

**Proceso (Background Task):**

```python
async def registrar_interaccion(whatsapp, mensaje_entrada, respuesta, agente):
    # 1. Registrar mensaje entrante
    interaccion_entrada = Interaccion.crear_mensaje_entrante(
        whatsapp=whatsapp,
        contenido=mensaje_entrada
    )
    
    # 2. Registrar respuesta
    interaccion_respuesta = Interaccion.crear_respuesta_bot(
        whatsapp=whatsapp,
        contenido=respuesta,
        agente=agente  # "router", "asistente", "coordinador"
    )
    
    session.add(interaccion_entrada)
    session.add(interaccion_respuesta)
    await session.commit()
```

**Archivos:**
- `gestor_ws/app/api/webhooks_whatsapp.py` (líneas 205-234)

---

### **FASE 5: RESOLUCIÓN DE TICKETS**

#### 5.1 Admin Responde Ticket (`admin.py`)

**Endpoint:** `PUT /api/admin/tickets/{ticket_id}/resolver`

**Proceso:**

```python
@router.put("/tickets/{ticket_id}/resolver")
async def resolver_ticket(ticket_id, data: TicketResolve, background_tasks):
    # 1. Obtener ticket
    ticket = await session.get(Ticket, ticket_id)
    
    # 2. Resolver ticket
    ticket.resolver(data.respuesta)  # respuesta técnica del admin
    await session.commit()
    
    # 3. Obtener phone_number del contexto
    phone_number = ticket.contexto.get("phone_number")
    
    # 4. Enviar respuesta reformulada (background)
    if phone_number:
        background_tasks.add_task(
            enviar_respuesta_ticket,
            ticket_id,
            data.respuesta,
            phone_number
        )
```

**Archivos:**
- `gestor_ws/app/api/admin.py` (líneas 119-172)

---

#### 5.2 Reformulación con LLM (`procesar_respuesta_admin()`)

**Proceso:**

```python
async def procesar_respuesta_admin(ticket_id, respuesta_admin, phone_number):
    prompt = f"""
Eres asistente del colegio. Reformula esta respuesta técnica del administrador
en lenguaje amigable para WhatsApp (máximo 3 párrafos cortos).

Respuesta del administrador:
{respuesta_admin}

Reglas:
- Usa lenguaje simple y cercano
- Incluye emojis relevantes
- Sé conciso (es para WhatsApp)
- Termina con una nota positiva o próximo paso claro

Respuesta reformulada:
"""
    
    response = await self.llm.ainvoke([HumanMessage(content=prompt)])
    return response.content.strip()
```

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 373-412)
- `gestor_ws/app/api/admin.py` (líneas 268-292)

---

#### 5.3 Envío de Respuesta Reformulada

**Proceso:**

```python
async def enviar_respuesta_ticket(ticket_id, respuesta_admin, phone_number):
    # 1. Reformular con LLM
    agente = AgenteAutonomo()
    respuesta_reformulada = await agente.procesar_respuesta_admin(
        ticket_id,
        respuesta_admin,
        phone_number
    )
    
    # 2. Enviar por WhatsApp
    whatsapp_service = get_whatsapp_service()
    await whatsapp_service.send_message(phone_number, respuesta_reformulada)
```

**Archivos:**
- `gestor_ws/app/api/admin.py` (líneas 268-292)

---

## 🔄 Flujo Completo: Ejemplo de Caso

### **Caso 1: Consulta Simple (Asistente)**

```
1. Padre envía: "Cuánto debo?"
   ↓
2. Router detecta keyword "cuanto debo" → RouteType.ASISTENTE
   ↓
3. Asistente procesa:
   - LLM analiza mensaje
   - Decide usar herramienta: consultar_estado_cuenta()
   - Consulta ERP: get_responsable_by_whatsapp() + get_alumno_cuotas()
   - LLM genera respuesta con datos
   ↓
4. Respuesta: "📋 Estado de cuenta:\n\n👤 Juan Pérez (3ro):\n  • Cuota 1: $45,000 (vence 2024-03-15)\n\n💰 Total adeudado: $45,000\n\n¿Necesitás los links de pago?"
   ↓
5. Se envía por WhatsApp
   ↓
6. Se registra interacción (mensaje + respuesta)
```

---

### **Caso 2: Caso Complejo (Agente Coordinador)**

```
1. Padre envía: "Necesito un plan de pagos, no puedo pagar todo junto"
   ↓
2. Router detecta keyword "plan de pago" → RouteType.AGENTE
   ↓
3. Agente Coordinador procesa (LangGraph):
   
   a) [clasificar]
      - LLM clasifica: categoria="plan_pago", prioridad="media"
      ↓
   b) [decidir_ruta]
      - categoria="plan_pago" → "resolver"
      ↓
   c) [intentar_resolver]
      - Genera respuesta inicial informativa
      - respuesta_final = "Entiendo que necesitás un plan de pagos..."
      ↓
   d) [validar_resolucion]
      - categoria="plan_pago" → siempre escalar
      - return "fallo"
      ↓
   e) [crear_ticket]
      - Crea ticket en BD:
        * categoria: "plan_pago"
        * prioridad: "media"
        * contexto: {phone_number, mensajes, timestamp}
      - ticket_id = "abc123..."
      ↓
   f) [generar_respuesta_espera]
      - Genera mensaje según categoría
      - respuesta_final = "✅ Registré tu solicitud de plan de pagos.\n\n📝 Ticket: #abc123...\n\n..."
      ↓
   g) END
   ↓
4. Se envía respuesta por WhatsApp
   ↓
5. Se registra interacción
   ↓
6. Admin ve ticket en Frontend Admin
   ↓
7. Admin responde: "Aprobamos plan de 3 cuotas de $15,000 c/u. ¿Te sirve?"
   ↓
8. Sistema reformula con LLM:
   - Entrada: "Aprobamos plan de 3 cuotas de $15,000 c/u. ¿Te sirve?"
   - Salida: "¡Buenas noticias! 🎉\n\nAprobamos tu plan de pagos:\n• 3 cuotas de $15,000 cada una\n\n¿Te sirve esta opción? 😊"
   ↓
9. Se envía al padre por WhatsApp
   ↓
10. Ticket marcado como "resuelto"
```

---

## 📋 Estado de Conversación (ConversationState)

El estado que se pasa entre nodos del grafo:

```python
class ConversationState(TypedDict):
    phone_number: str                    # WhatsApp del padre
    messages: list[str]                  # Historial de mensajes
    categoria: Optional[str]              # plan_pago, reclamo, baja, consulta_admin
    prioridad: Optional[str]             # baja, media, alta
    ticket_id: Optional[str]              # ID del ticket creado
    respuesta_admin: Optional[str]        # Respuesta del admin (para reformular)
    intentos_resolucion: int              # Contador de intentos
    respuesta_final: Optional[str]        # Respuesta final a enviar
    erp_alumno_id: Optional[str]          # ID del alumno (opcional)
    erp_responsable_id: Optional[str]     # ID del responsable (opcional)
    error: Optional[str]                  # Error si ocurre
```

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 21-33)

---

## 🔧 Configuración y Herramientas

### **LLM Factory**

El sistema usa un factory para obtener el LLM configurado:

```python
from app.llm.factory import get_llm

llm = get_llm()  # OpenAI GPT o Google Gemini (configurable)
```

**Archivos:**
- `gestor_ws/app/llm/factory.py`

---

### **ERP Client**

Interfaz para consultar datos del ERP:

```python
from app.adapters.erp_interface import ERPClientInterface
from app.adapters.mock_erp_adapter import get_erp_client

erp = get_erp_client()

# Métodos disponibles:
# - get_responsable_by_whatsapp(whatsapp: str)
# - get_alumno_cuotas(alumno_id: str, estado: str)
# - get_cuota(cuota_id: str)
```

**Archivos:**
- `gestor_ws/app/adapters/erp_interface.py`
- `gestor_ws/app/adapters/mock_erp_adapter.py`

---

## 📡 Endpoints API

### **Webhooks WhatsApp**

- `GET /webhook/whatsapp` - Verificación de webhook (Meta)
- `POST /webhook/whatsapp` - Recibe mensajes de WhatsApp
- `POST /webhook/whatsapp/test` - Endpoint de prueba (no envía respuesta real)

**Archivos:**
- `gestor_ws/app/api/webhooks_whatsapp.py`

---

### **Admin API**

- `GET /api/admin/tickets` - Lista todos los tickets
- `GET /api/admin/tickets/{id}` - Obtiene un ticket
- `PUT /api/admin/tickets/{id}/resolver` - Resuelve ticket y envía respuesta
- `PUT /api/admin/tickets/{id}/estado` - Cambia estado del ticket
- `GET /api/admin/stats` - Estadísticas de tickets

**Archivos:**
- `gestor_ws/app/api/admin.py`

---

## 🔍 Resumen del Flujo

1. **RECEPCIÓN** → Webhook recibe mensaje de WhatsApp
2. **ROUTING** → Router clasifica por keywords (SALUDO/ASISTENTE/AGENTE)
3. **PROCESAMIENTO** → 
   - **Saludo**: Respuesta predefinida
   - **Asistente**: LLM + Tools (consulta ERP, genera respuesta)
   - **Agente**: LangGraph (clasifica → intenta resolver → crea ticket)
4. **ENVÍO** → WhatsApp Service envía respuesta
5. **REGISTRO** → Interacción guardada en BD
6. **RESOLUCIÓN** → Admin responde ticket → LLM reformula → Se envía al padre

---

## 🔗 Archivos Clave

| Archivo | Descripción |
|---------|-------------|
| `app/api/webhooks_whatsapp.py` | Endpoint de recepción de mensajes |
| `app/agents/router.py` | Router de mensajes (Capa 1) |
| `app/agents/asistente.py` | Asistente Virtual (Capa 2 - LLM + Tools) |
| `app/agents/coordinador.py` | Agente Coordinador (Capa 3 - LangGraph) |
| `app/tools/consultar_erp.py` | Herramientas para consultar ERP |
| `app/api/admin.py` | API para administradores (resolver tickets) |
| `app/services/whatsapp_service.py` | Servicio de envío de mensajes |
| `app/models/interacciones.py` | Modelo de interacciones |
| `app/models/tickets.py` | Modelo de tickets |

---

## 🎯 Diferencias entre Capas

| Capa | Tecnología | Uso | Complejidad |
|------|-----------|-----|-------------|
| **Router** | Keywords simples | Saludos y routing inicial | Baja |
| **Asistente** | LLM + Tool Calling | Consultas simples (cuotas, links) | Media |
| **Coordinador** | LangGraph (StateGraph) | Casos complejos (planes, reclamos) | Alta |

---

## 📝 Notas Importantes

1. **Escalamiento Automático**: El asistente puede escalar usando la herramienta `escalar_a_agente()`, que retorna un string especial `"__ESCALAR__|categoria|motivo"` que es detectado por el webhook.

2. **Reformulación de Respuestas**: Las respuestas técnicas de los administradores se reformulan automáticamente con LLM antes de enviarse al padre, adaptándolas al formato WhatsApp.

3. **Historial de Conversación**: El asistente mantiene historial de los últimos 5 mensajes para contexto.

4. **Background Tasks**: El registro de interacciones se hace en background para no bloquear la respuesta.

5. **Manejo de Errores**: Cada capa tiene manejo de errores con respuestas de fallback amigables.

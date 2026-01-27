# 🔧 Herramientas del Agente Coordinador

Este documento describe las capacidades y recursos disponibles para el Agente Coordinador (AgenteAutonomo).

---

## ⚠️ Diferencia Importante: NO usa Tools LangChain

A diferencia del **Asistente Virtual** que usa `create_tool_calling_agent` con herramientas LangChain, el **Agente Coordinador** usa un enfoque diferente:

- **Asistente Virtual**: Usa `AgentExecutor` con herramientas LangChain (`@tool`)
- **Agente Coordinador**: Usa `StateGraph` (LangGraph) con nodos que son funciones Python

---

## 🎯 Recursos Disponibles

El Agente Coordinador tiene acceso a los siguientes recursos:

### **1. LLM (Large Language Model)**

**Acceso:** `self.llm` (obtenido via `get_llm()`)

**Uso:**
- Clasificación de consultas
- Reformulación de respuestas del admin

**Ejemplo:**
```python
# En clasificar_consulta()
response = await self.llm.ainvoke([HumanMessage(content=prompt)])

# En procesar_respuesta_admin()
response = await self.llm.ainvoke([HumanMessage(content=prompt)])
```

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 133, 407)

---

### **2. Cliente ERP**

**Acceso:** `self.erp` (obtenido via `get_erp_client()`)

**Tipo:** `ERPClientInterface`

**Estado Actual:** ⚠️ **NO se usa directamente** en el código actual del coordinador

**Disponible pero no utilizado:**
```python
def __init__(self, erp_client: Optional[ERPClientInterface] = None):
    self.erp = erp_client or get_erp_client()  # Disponible pero no usado
```

**Métodos disponibles (si se necesitara):**
- `get_responsable_by_whatsapp(whatsapp: str)`
- `get_alumno_cuotas(alumno_id: str, estado: str)`
- `get_cuota(cuota_id: str)`

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (línea 59)
- `gestor_ws/app/adapters/erp_interface.py`

---

### **3. Base de Datos (PostgreSQL)**

**Acceso:** Via `async_session_maker()` (importado cuando se necesita)

**Uso:**
- Crear tickets en la tabla `tickets`

**Ejemplo:**
```python
# En crear_ticket()
from app.models.tickets import Ticket
from app.database import async_session_maker

async with async_session_maker() as session:
    ticket = Ticket.crear(...)
    session.add(ticket)
    await session.commit()
```

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 243-261)

---

## 🔄 Nodos del Grafo (Funciones Disponibles)

El Agente Coordinador tiene 4 nodos principales que actúan como "funciones" disponibles:

### **1. `clasificar_consulta()`**

**Función:** Clasifica la consulta usando LLM

**Input:** `ConversationState` con `messages`

**Output:** `ConversationState` con `categoria` y `prioridad` actualizados

**Proceso:**
1. Construye prompt para LLM
2. Llama a LLM con el mensaje
3. Parsea respuesta JSON
4. Actualiza estado con categoría y prioridad

**Categorías posibles:**
- `plan_pago`: Solicita plan de pagos, financiación
- `reclamo`: Queja sobre cobros, errores, mal servicio
- `baja`: Solicita dar de baja al alumno
- `consulta_admin`: Otra consulta que requiere administración

**Prioridades posibles:**
- `baja`: Consultas generales
- `media`: Solicitudes normales
- `alta`: Urgencias, reclamos graves

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 105-167)

---

### **2. `intentar_resolucion()`**

**Función:** Intenta resolver la consulta automáticamente

**Input:** `ConversationState` con `categoria`

**Output:** `ConversationState` con `respuesta_final` (opcional)

**Proceso:**
1. Verifica categoría
2. Genera respuesta informativa según categoría
3. Para `plan_pago` y `consulta_admin`: da respuesta pero igual escala

**Respuestas generadas:**
- `plan_pago`: Informa sobre proceso de plan de pagos
- `consulta_admin`: Informa que se derivará a administración

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 187-226)

---

### **3. `crear_ticket()`**

**Función:** Crea un ticket en la base de datos

**Input:** `ConversationState` con `categoria`, `prioridad`, `messages`, etc.

**Output:** `ConversationState` con `ticket_id` actualizado

**Proceso:**
1. Crea instancia de `Ticket` con datos del estado
2. Guarda en PostgreSQL
3. Actualiza estado con `ticket_id`

**Datos guardados:**
- `erp_alumno_id`
- `erp_responsable_id`
- `categoria`
- `motivo` (último mensaje)
- `contexto` (JSON con phone_number, mensajes, timestamp)
- `prioridad`

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 240-273)

---

### **4. `generar_respuesta_espera()`**

**Función:** Genera mensaje indicando que el ticket fue creado

**Input:** `ConversationState` con `categoria` y `ticket_id`

**Output:** `ConversationState` con `respuesta_final` actualizado

**Proceso:**
1. Selecciona plantilla de respuesta según categoría
2. Incluye número de ticket
3. Establece tiempo estimado de respuesta

**Respuestas por categoría:**
- `plan_pago`: "✅ Registré tu solicitud de plan de pagos..."
- `reclamo`: "📋 Tu reclamo fue registrado correctamente..."
- `baja`: "📝 Tu solicitud de baja fue registrada..."
- `consulta_admin`: "✅ Tu consulta fue derivada al área administrativa..."

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 275-316)

---

### **5. `procesar_respuesta_admin()`** (Método adicional)

**Función:** Reformula respuesta técnica del admin para WhatsApp

**Input:** 
- `ticket_id`: ID del ticket
- `respuesta_admin`: Respuesta técnica del administrador
- `phone_number`: Número de WhatsApp del padre

**Output:** `str` - Respuesta reformulada

**Proceso:**
1. Construye prompt para LLM
2. LLM reformula respuesta técnica → lenguaje amigable
3. Adapta para WhatsApp (corto, emojis, cercano)

**Uso:** Se llama desde `gestor_ws/app/api/admin.py` cuando el admin resuelve un ticket

**Archivos:**
- `gestor_ws/app/agents/coordinador.py` (líneas 373-412)

---

## 📊 Comparación: Asistente vs Coordinador

| Aspecto | Asistente Virtual | Agente Coordinador |
|---------|-------------------|-------------------|
| **Arquitectura** | `AgentExecutor` con tools | `StateGraph` con nodos |
| **Herramientas LangChain** | ✅ Sí (4 tools) | ❌ No |
| **LLM** | ✅ Sí (para razonamiento) | ✅ Sí (para clasificación y reformulación) |
| **Cliente ERP** | ✅ Sí (via tools) | ⚠️ Disponible pero no usado |
| **Base de Datos** | ❌ No (tools lo hacen) | ✅ Sí (crear tickets) |
| **Tool Calling** | ✅ Sí | ❌ No |
| **Flujo** | Reactivo (LLM decide qué tool usar) | Proactivo (grafo define flujo) |

---

## 🔍 Herramientas del Asistente (Para Comparar)

El Asistente Virtual tiene estas herramientas (que el Coordinador NO tiene):

1. **`consultar_estado_cuenta(whatsapp: str)`**
   - Consulta cuotas pendientes
   - Retorna estado de cuenta

2. **`obtener_link_pago(cuota_id: str)`**
   - Obtiene link de pago de una cuota
   - Retorna link, monto, fecha

3. **`registrar_confirmacion_pago(cuota_id: str, whatsapp: str)`**
   - Registra confirmación de pago
   - Crea interacción en BD

4. **`escalar_a_agente(motivo: str, categoria: str)`**
   - Escala al Agente Coordinador
   - Retorna string especial `"__ESCALAR__|..."`

**Archivos:**
- `gestor_ws/app/tools/consultar_erp.py`

---

## 💡 ¿Por qué el Coordinador NO usa Tools?

El Agente Coordinador está diseñado para:

1. **Casos complejos** que requieren múltiples pasos
2. **Escalamiento** a humanos (crear tickets)
3. **Flujo predefinido** (no reactivo)

Usa LangGraph porque:
- Permite definir un flujo de trabajo explícito
- Control total sobre cada paso
- Fácil agregar nuevos nodos o modificar flujo
- No depende de que el LLM "decida" qué hacer (ya está definido)

El Asistente Virtual usa tools porque:
- Necesita consultar datos dinámicamente
- El LLM decide qué información necesita
- Es más flexible para consultas simples

---

## 🚀 Posibles Extensiones Futuras

Si se quisiera agregar herramientas al Coordinador, se podría:

1. **Agregar nodo con tool calling:**
   ```python
   async def consultar_datos(self, state: ConversationState):
       # Usar self.erp para consultar datos
       # Actualizar state con información
       return state
   ```

2. **Usar herramientas en nodos específicos:**
   ```python
   from app.tools.consultar_erp import get_erp_tools
   
   async def intentar_resolucion(self, state: ConversationState):
       tools = get_erp_tools(self.erp)
       # Usar tools si es necesario
   ```

3. **Crear herramientas específicas para el coordinador:**
   ```python
   # app/tools/coordinador_tools.py
   @tool
   async def consultar_historial_tickets(whatsapp: str):
       # Consultar tickets anteriores del responsable
   ```

---

## 📋 Resumen

**El Agente Coordinador NO tiene herramientas LangChain**, pero tiene:

✅ **LLM** - Para clasificación y reformulación  
✅ **Base de Datos** - Para crear tickets  
⚠️ **Cliente ERP** - Disponible pero no usado actualmente  
✅ **Nodos del Grafo** - Funciones que ejecutan lógica específica  

**Diferencia clave:** El Coordinador usa un flujo predefinido (LangGraph), mientras que el Asistente usa un flujo reactivo con tools (AgentExecutor).

---

## 🔗 Archivos Clave

| Archivo | Descripción |
|---------|-------------|
| `gestor_ws/app/agents/coordinador.py` | Implementación del Agente Coordinador |
| `gestor_ws/app/agents/asistente.py` | Asistente Virtual (con tools, para comparar) |
| `gestor_ws/app/tools/consultar_erp.py` | Herramientas del Asistente |
| `gestor_ws/app/adapters/erp_interface.py` | Interface del cliente ERP |

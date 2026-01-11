# Tipos TypeScript para Gestor WS Frontend

Este documento describe los tipos TypeScript generados para el frontend del sistema Gestor WS.

## Archivos Generados

| Archivo | Descripción |
|---------|-------------|
| `types.ts` | Tipos e interfaces TypeScript + Cliente API |
| `types.example.ts` | Ejemplos de uso con React |

## Instalación en tu Proyecto React

```bash
# Copiar al proyecto frontend
cp types.ts ../frontend/src/api/gestor-ws/types.ts
```

## Uso Básico

### 1. Inicializar el Cliente

```typescript
import { GestorWSClient } from './types';

const client = new GestorWSClient('http://localhost:8000');
```

### 2. Health Checks

```typescript
// Verificar estado del sistema
const health = await client.getHealth();
console.log(health.status); // "healthy" | "degraded"
console.log(health.llm.provider); // "openai" | "google"

// Verificar LLM
const llmHealth = await client.getHealthLLM();

// Verificar ERP
const erpHealth = await client.getHealthERP();
```

### 3. Enviar Mensajes WhatsApp

```typescript
import { WhatsAppMessage } from './types';

const message: WhatsAppMessage = {
  from_number: '+5491112345005',
  text: 'Cuánto debo?'
};

// Endpoint de prueba (no envía respuesta real)
const testResponse = await client.testWhatsAppMessage(message);
console.log(testResponse.route_info?.route); // "asistente" | "agente" | "saludo"
console.log(testResponse.respuesta);

// Endpoint real
const response = await client.sendWhatsAppMessage(message);
```

### 4. Gestionar Tickets

```typescript
import { TicketListParams, TicketResolve } from './types';

// Listar tickets pendientes
const params: TicketListParams = {
  estado: 'pendiente',
  categoria: 'plan_pago',
  limit: 20
};
const ticketList = await client.listTickets(params);

// Obtener detalle
const ticket = await client.getTicket('uuid-del-ticket');

// Resolver ticket
const resolveData: TicketResolve = {
  respuesta: 'Se aprobó el plan de pagos en 3 cuotas.'
};
await client.resolveTicket('uuid-del-ticket', resolveData);

// Estadísticas
const stats = await client.getStats();
```

## Tipos Principales

### Entidades

```typescript
interface Alumno {
  id: string;
  nombre: string;
  apellido: string;
  grado?: string | null;
}

interface Responsable {
  id: string;
  nombre: string;
  apellido: string;
  whatsapp?: string | null;
  email?: string | null;
  alumnos: Alumno[];
}

interface Cuota {
  id: string;
  alumno_id: string;
  numero_cuota: number;
  monto: number;
  fecha_vencimiento: string; // YYYY-MM-DD
  estado: 'pendiente' | 'pagada' | 'vencida';
  link_pago?: string | null;
  fecha_pago?: string | null; // ISO 8601
}

interface Ticket {
  id: string; // UUID
  erp_alumno_id: string;
  erp_responsable_id?: string | null;
  categoria?: 'plan_pago' | 'reclamo' | 'baja' | 'consulta_admin' | null;
  motivo?: string | null;
  contexto?: Record<string, unknown> | null;
  estado: 'pendiente' | 'en_proceso' | 'resuelto';
  prioridad: 'baja' | 'media' | 'alta';
  respuesta_admin?: string | null;
  created_at: string; // ISO 8601
  resolved_at?: string | null; // ISO 8601
}
```

### Mensajes WhatsApp

```typescript
interface WhatsAppMessage {
  from_number: string;
  text: string;
  message_id?: string | null;
  timestamp?: string; // ISO 8601
}

interface WhatsAppResponse {
  to_number: string;
  text: string;
  reply_to?: string | null;
}
```

### Eventos Webhook

```typescript
interface PagoConfirmadoEvent {
  tipo: 'pago_confirmado';
  timestamp: string;
  datos: {
    cuota_id: string;
    alumno_id: string;
    monto: number;
    metodo_pago?: string;
    fecha_pago: string;
  };
}

interface CuotaGeneradaEvent {
  tipo: 'cuota_generada';
  timestamp: string;
  datos: {
    cuota_id: string;
    alumno_id: string;
    monto: number;
    fecha_vencimiento: string;
    link_pago?: string;
  };
}
```

## Endpoints API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Estado general del sistema |
| GET | `/health/llm` | Estado del LLM |
| GET | `/health/erp` | Estado del ERP |
| POST | `/webhook/whatsapp` | Recibir mensaje WhatsApp (envía respuesta) |
| POST | `/webhook/whatsapp/test` | Probar mensaje WhatsApp (solo procesa) |
| POST | `/webhook/erp/pago-confirmado` | Notificar pago confirmado |
| POST | `/webhook/erp/cuota-generada` | Notificar cuota generada |
| GET | `/api/admin/tickets` | Listar tickets |
| GET | `/api/admin/tickets/{id}` | Obtener ticket |
| PUT | `/api/admin/tickets/{id}/resolver` | Resolver ticket |
| PUT | `/api/admin/tickets/{id}/estado` | Cambiar estado |
| GET | `/api/admin/stats` | Estadísticas |

## Constantes Útiles

```typescript
import {
  TICKET_ESTADOS,      // ['pendiente', 'en_proceso', 'resuelto']
  TICKET_CATEGORIAS,   // ['plan_pago', 'reclamo', 'baja', 'consulta_admin']
  TICKET_PRIORIDADES,  // ['baja', 'media', 'alta']
  CUOTA_ESTADOS        // ['pendiente', 'pagada', 'vencida']
} from './types';
```

## Type Guards

```typescript
import { isTicketEstado, isTicketCategoria, isTicketPrioridad } from './types';

// Validar valores dinámicos
if (isTicketEstado(value)) {
  // value es TicketEstado
}
```

## Ejemplo React Completo

Ver archivo `types.example.ts` para ejemplos completos de:
- React hooks personalizados
- Componente de dashboard
- Manejo de errores
- Validación de tipos


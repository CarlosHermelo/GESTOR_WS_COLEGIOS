/**
 * Ejemplos de uso de los tipos TypeScript para Gestor WS API
 * 
 * Este archivo muestra cómo usar los tipos y el cliente API en tu frontend React/TypeScript
 */

import {
  GestorWSClient,
  WhatsAppMessage,
  TicketCreate,
  TicketResolve,
  TicketListParams,
  HealthResponse,
  Ticket,
} from './types';

// ============================================================================
// 1. INICIALIZAR CLIENTE
// ============================================================================

const client = new GestorWSClient("http://localhost:8000");

// O con variable de entorno:
const clientFromEnv = new GestorWSClient(process.env.REACT_APP_API_URL || "http://localhost:8000");

// ============================================================================
// 2. HEALTH CHECKS
// ============================================================================

async function checkSystemHealth() {
  try {
    const health = await client.getHealth();
    console.log("Sistema:", health.status);
    console.log("BD:", health.components.database);
    console.log("ERP:", health.components.erp);
    console.log("LLM:", health.llm.provider, health.llm.model);
  } catch (error) {
    console.error("Error verificando salud:", error);
  }
}

async function checkLLMHealth() {
  try {
    const llmHealth = await client.getHealthLLM();
    if (llmHealth.status === "ok") {
      console.log(`LLM configurado: ${llmHealth.provider} / ${llmHealth.model}`);
    } else {
      console.error("Error LLM:", llmHealth.error);
    }
  } catch (error) {
    console.error("Error:", error);
  }
}

// ============================================================================
// 3. ENVIAR MENSAJES WHATSAPP
// ============================================================================

async function sendWhatsAppMessage() {
  const message: WhatsAppMessage = {
    from_number: "+5491112345005",
    text: "Cuánto debo?",
    message_id: "msg_123",
    timestamp: new Date().toISOString(),
  };

  try {
    // Endpoint de prueba (solo procesa, no envía respuesta real)
    const testResponse = await client.testWhatsAppMessage(message);
    console.log("Ruta:", testResponse.route_info?.route);
    console.log("Respuesta:", testResponse.respuesta);

    // Endpoint real (envía respuesta simulada)
    const realResponse = await client.sendWhatsAppMessage(message);
    console.log("Estado:", realResponse.status);
    console.log("Agente:", realResponse.agente);
  } catch (error) {
    console.error("Error enviando mensaje:", error);
  }
}

// ============================================================================
// 4. GESTIONAR TICKETS
// ============================================================================

async function listTickets() {
  const params: TicketListParams = {
    estado: "pendiente",
    categoria: "plan_pago",
    limit: 20,
    offset: 0,
  };

  try {
    const response = await client.listTickets(params);
    console.log(`Total tickets: ${response.total}`);
    console.log(`Pendientes: ${response.pendientes}`);
    console.log(`En proceso: ${response.en_proceso}`);
    console.log(`Resueltos: ${response.resueltos}`);

    response.tickets.forEach((ticket) => {
      console.log(`- ${ticket.id}: ${ticket.categoria} (${ticket.estado})`);
    });
  } catch (error) {
    console.error("Error listando tickets:", error);
  }
}

async function createTicket() {
  const ticketData: TicketCreate = {
    erp_alumno_id: "ALU-001",
    erp_responsable_id: "RES-001",
    categoria: "plan_pago",
    motivo: "El padre solicita un plan de pagos en 3 cuotas",
    contexto: {
      mensajes: [
        { from: "usuario", text: "Necesito un plan de pago" },
        { from: "bot", text: "Entiendo, voy a derivar tu consulta" },
      ],
    },
    prioridad: "media",
  };

  // Nota: No hay endpoint público para crear tickets directamente,
  // se crean automáticamente cuando el bot escala una consulta
}

async function getTicketDetails(ticketId: string) {
  try {
    const ticket = await client.getTicket(ticketId);
    console.log("Ticket:", ticket.id);
    console.log("Categoría:", ticket.categoria);
    console.log("Estado:", ticket.estado);
    console.log("Motivo:", ticket.motivo);
  } catch (error) {
    console.error("Error obteniendo ticket:", error);
  }
}

async function resolveTicket(ticketId: string) {
  const resolveData: TicketResolve = {
    respuesta: "Se aprobó el plan de pagos en 3 cuotas sin interés. Las nuevas fechas de vencimiento son: 15/02, 15/03 y 15/04.",
  };

  try {
    const result = await client.resolveTicket(ticketId, resolveData);
    console.log("Ticket resuelto:", result.ticket_id);
    console.log("Notificación enviada:", result.notificacion_enviada);
  } catch (error) {
    console.error("Error resolviendo ticket:", error);
  }
}

async function getTicketStats() {
  try {
    const stats = await client.getStats();
    console.log("Estadísticas de tickets:", stats.tickets);
  } catch (error) {
    console.error("Error obteniendo stats:", error);
  }
}

// ============================================================================
// 5. WEBHOOKS ERP (para simular eventos del ERP)
// ============================================================================

async function simulatePagoConfirmado() {
  const event = {
    tipo: "pago_confirmado" as const,
    timestamp: new Date().toISOString(),
    datos: {
      cuota_id: "CUO-001",
      alumno_id: "ALU-001",
      monto: 45000.0,
      metodo_pago: "transferencia",
      fecha_pago: new Date().toISOString(),
    },
  };

  try {
    const response = await client.notifyPagoConfirmado(event);
    console.log("Webhook procesado:", response.status);
  } catch (error) {
    console.error("Error enviando webhook:", error);
  }
}

async function simulateCuotaGenerada() {
  const event = {
    tipo: "cuota_generada" as const,
    timestamp: new Date().toISOString(),
    datos: {
      cuota_id: "CUO-002",
      alumno_id: "ALU-001",
      monto: 45000.0,
      fecha_vencimiento: "2024-02-15",
      link_pago: "https://pago.colegio.com/CUO-002",
    },
  };

  try {
    const response = await client.notifyCuotaGenerada(event);
    console.log("Webhook procesado:", response.status);
  } catch (error) {
    console.error("Error enviando webhook:", error);
  }
}

// ============================================================================
// 6. USO CON REACT HOOKS
// ============================================================================

/*
import { useState, useEffect } from 'react';
import { GestorWSClient, Ticket, TicketListParams } from './types';

function useTickets(params?: TicketListParams) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const client = new GestorWSClient();
    client
      .listTickets(params)
      .then((response) => setTickets(response.tickets))
      .catch(setError)
      .finally(() => setLoading(false));
  }, [JSON.stringify(params)]);

  return { tickets, loading, error };
}

// Uso en componente:
function TicketsList() {
  const { tickets, loading, error } = useTickets({ estado: 'pendiente' });

  if (loading) return <div>Cargando...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <ul>
      {tickets.map((ticket) => (
        <li key={ticket.id}>
          {ticket.categoria} - {ticket.estado}
        </li>
      ))}
    </ul>
  );
}
*/

// ============================================================================
// 7. MANEJO DE ERRORES
// ============================================================================

async function handleErrorsExample() {
  try {
    const tickets = await client.listTickets();
    return tickets;
  } catch (error) {
    if (error instanceof Error) {
      console.error("Error de red:", error.message);
    } else {
      console.error("Error desconocido:", error);
    }
    throw error;
  }
}

// ============================================================================
// 8. VALIDACION DE TIPOS
// ============================================================================

import { isTicketEstado, isTicketCategoria, isTicketPrioridad } from './types';

function validateTicketFilters(params: unknown) {
  if (typeof params !== 'object' || params === null) {
    return false;
  }

  const p = params as Record<string, unknown>;

  if (p.estado && !isTicketEstado(p.estado as string)) {
    return false;
  }

  if (p.categoria && !isTicketCategoria(p.categoria as string)) {
    return false;
  }

  if (p.prioridad && !isTicketPrioridad(p.prioridad as string)) {
    return false;
  }

  return true;
}

// ============================================================================
// 9. EJEMPLO DE COMPONENTE REACT COMPLETO
// ============================================================================

/*
import React, { useState, useEffect } from 'react';
import { GestorWSClient, Ticket, TicketEstado } from './types';

const client = new GestorWSClient(process.env.REACT_APP_API_URL || 'http://localhost:8000');

function TicketsDashboard() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<TicketEstado>('pendiente');

  useEffect(() => {
    setLoading(true);
    client
      .listTickets({ estado: filter })
      .then((response) => {
        setTickets(response.tickets);
        setLoading(false);
      })
      .catch((error) => {
        console.error('Error:', error);
        setLoading(false);
      });
  }, [filter]);

  const handleResolve = async (ticketId: string) => {
    const respuesta = prompt('Ingrese la respuesta para el padre:');
    if (!respuesta || respuesta.length < 10) {
      alert('La respuesta debe tener al menos 10 caracteres');
      return;
    }

    try {
      await client.resolveTicket(ticketId, { respuesta });
      alert('Ticket resuelto correctamente');
      // Recargar tickets
      const response = await client.listTickets({ estado: filter });
      setTickets(response.tickets);
    } catch (error) {
      console.error('Error resolviendo ticket:', error);
      alert('Error al resolver el ticket');
    }
  };

  if (loading) {
    return <div>Cargando tickets...</div>;
  }

  return (
    <div>
      <h1>Dashboard de Tickets</h1>
      
      <div>
        <label>
          Filtrar por estado:
          <select value={filter} onChange={(e) => setFilter(e.target.value as TicketEstado)}>
            <option value="pendiente">Pendiente</option>
            <option value="en_proceso">En Proceso</option>
            <option value="resuelto">Resuelto</option>
          </select>
        </label>
      </div>

      <ul>
        {tickets.map((ticket) => (
          <li key={ticket.id}>
            <h3>{ticket.categoria} - {ticket.estado}</h3>
            <p>{ticket.motivo}</p>
            {ticket.estado !== 'resuelto' && (
              <button onClick={() => handleResolve(ticket.id)}>
                Resolver
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default TicketsDashboard;
*/


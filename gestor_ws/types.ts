/**
 * TypeScript Types for Gestor WS API
 * Generated from FastAPI schemas and endpoints
 * 
 * Base URL: http://localhost:8000
 */

// ============================================================================
// BASE TYPES
// ============================================================================

export type UUID = string;
export type Decimal = number;
export type DateTime = string; // ISO 8601 format
export type Date = string; // YYYY-MM-DD format

// ============================================================================
// ERP SCHEMAS
// ============================================================================

export interface Alumno {
  id: string;
  nombre: string;
  apellido: string;
  grado?: string | null;
}

export interface Responsable {
  id: string;
  nombre: string;
  apellido: string;
  whatsapp?: string | null;
  email?: string | null;
  alumnos: Alumno[];
}

export interface Cuota {
  id: string;
  alumno_id: string;
  numero_cuota: number;
  monto: Decimal;
  fecha_vencimiento: Date;
  estado: "pendiente" | "pagada" | "vencida";
  link_pago?: string | null;
  fecha_pago?: DateTime | null;
}

// ============================================================================
// WHATSAPP SCHEMAS
// ============================================================================

export interface WhatsAppMessage {
  from_number: string;
  text: string;
  message_id?: string | null;
  timestamp?: DateTime;
}

export interface WhatsAppResponse {
  to_number: string;
  text: string;
  reply_to?: string | null;
}

export interface WebhookPayload {
  object: string;
  entry: Array<Record<string, unknown>>;
}

export interface WebhookVerification {
  "hub.mode": string;
  "hub.verify_token": string;
  "hub.challenge": string;
}

// ============================================================================
// TICKETS SCHEMAS
// ============================================================================

export type TicketCategoria = "plan_pago" | "reclamo" | "baja" | "consulta_admin";
export type TicketEstado = "pendiente" | "en_proceso" | "resuelto";
export type TicketPrioridad = "baja" | "media" | "alta";

export interface TicketCreate {
  erp_alumno_id: string;
  erp_responsable_id?: string | null;
  categoria: TicketCategoria;
  motivo: string;
  contexto?: Record<string, unknown>;
  prioridad?: TicketPrioridad;
}

export interface Ticket {
  id: UUID;
  erp_alumno_id: string;
  erp_responsable_id?: string | null;
  categoria?: TicketCategoria | null;
  motivo?: string | null;
  contexto?: Record<string, unknown> | null;
  estado: TicketEstado;
  prioridad: TicketPrioridad;
  respuesta_admin?: string | null;
  created_at: DateTime;
  resolved_at?: DateTime | null;
}

export interface TicketResolve {
  respuesta: string;
}

export interface TicketListResponse {
  tickets: Ticket[];
  total: number;
  pendientes: number;
  en_proceso: number;
  resueltos: number;
}

// ============================================================================
// WEBHOOK EVENTS (ERP)
// ============================================================================

export interface PagoConfirmadoEvent {
  tipo: "pago_confirmado";
  timestamp: DateTime;
  datos: {
    cuota_id: string;
    alumno_id: string;
    monto: Decimal;
    metodo_pago?: string;
    fecha_pago: DateTime;
  };
}

export interface CuotaGeneradaEvent {
  tipo: "cuota_generada";
  timestamp: DateTime;
  datos: {
    cuota_id: string;
    alumno_id: string;
    monto: Decimal;
    fecha_vencimiento: Date;
    link_pago?: string;
  };
}

// ============================================================================
// HEALTH CHECK RESPONSES
// ============================================================================

export interface HealthResponse {
  status: "healthy" | "degraded";
  service: "gestor_ws";
  version: string;
  components: {
    database: "connected" | "disconnected";
    erp: "connected" | "disconnected";
  };
  llm: {
    provider: string;
    model: string;
  };
  config: {
    erp_url: string;
    whatsapp_simulation: boolean;
  };
}

export interface HealthLLMResponse {
  status: "ok" | "error";
  provider?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  available_providers?: string[];
  error?: string;
}

export interface HealthERPResponse {
  status: "ok" | "error";
  url: string;
  type: string;
  error?: string;
}

// ============================================================================
// API RESPONSES
// ============================================================================

export interface WebhookWhatsAppResponse {
  status: "ok" | "error";
  ruta?: string;
  agente?: string;
  respuesta_preview?: string;
  error?: string;
}

export interface WebhookWhatsAppTestResponse {
  status: "ok" | "error";
  from?: string;
  message?: string;
  route_info?: {
    route: "asistente" | "agente" | "saludo";
    message_preview: string;
    matched_keywords: {
      simple: string[];
      escalamiento: string[];
      saludo: string[];
    };
    reason: string;
  };
  agente?: string;
  respuesta?: string;
  error?: string;
}

export interface WebhookERPResponse {
  status: "ok";
  message: string;
  cuota_id?: string;
  alumno_id?: string;
}

export interface TicketStatsResponse {
  tickets: {
    por_estado: Record<TicketEstado, number>;
    por_categoria: Record<TicketCategoria, number>;
    pendientes_por_prioridad: Record<TicketPrioridad, number>;
    total: number;
  };
}

// ============================================================================
// API CLIENT TYPES
// ============================================================================

export interface TicketListParams {
  estado?: TicketEstado;
  categoria?: TicketCategoria;
  prioridad?: TicketPrioridad;
  limit?: number;
  offset?: number;
}

// ============================================================================
// API CLIENT CLASS
// ============================================================================

export class GestorWSClient {
  private baseURL: string;

  constructor(baseURL: string = "http://localhost:8000") {
    this.baseURL = baseURL.replace(/\/$/, ""); // Remove trailing slash
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // ========================================================================
  // HEALTH CHECKS
  // ========================================================================

  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  async getHealthLLM(): Promise<HealthLLMResponse> {
    return this.request<HealthLLMResponse>("/health/llm");
  }

  async getHealthERP(): Promise<HealthERPResponse> {
    return this.request<HealthERPResponse>("/health/erp");
  }

  // ========================================================================
  // WHATSAPP WEBHOOKS
  // ========================================================================

  async sendWhatsAppMessage(message: WhatsAppMessage): Promise<WebhookWhatsAppResponse> {
    return this.request<WebhookWhatsAppResponse>("/webhook/whatsapp", {
      method: "POST",
      body: JSON.stringify(message),
    });
  }

  async testWhatsAppMessage(message: WhatsAppMessage): Promise<WebhookWhatsAppTestResponse> {
    return this.request<WebhookWhatsAppTestResponse>("/webhook/whatsapp/test", {
      method: "POST",
      body: JSON.stringify(message),
    });
  }

  // ========================================================================
  // ERP WEBHOOKS
  // ========================================================================

  async notifyPagoConfirmado(event: PagoConfirmadoEvent): Promise<WebhookERPResponse> {
    return this.request<WebhookERPResponse>("/webhook/erp/pago-confirmado", {
      method: "POST",
      body: JSON.stringify(event),
    });
  }

  async notifyCuotaGenerada(event: CuotaGeneradaEvent): Promise<WebhookERPResponse> {
    return this.request<WebhookERPResponse>("/webhook/erp/cuota-generada", {
      method: "POST",
      body: JSON.stringify(event),
    });
  }

  // ========================================================================
  // ADMIN API - TICKETS
  // ========================================================================

  async listTickets(params?: TicketListParams): Promise<TicketListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.estado) searchParams.append("estado", params.estado);
    if (params?.categoria) searchParams.append("categoria", params.categoria);
    if (params?.prioridad) searchParams.append("prioridad", params.prioridad);
    if (params?.limit) searchParams.append("limit", params.limit.toString());
    if (params?.offset) searchParams.append("offset", params.offset.toString());

    const query = searchParams.toString();
    return this.request<TicketListResponse>(`/api/admin/tickets${query ? `?${query}` : ""}`);
  }

  async getTicket(ticketId: UUID): Promise<Ticket> {
    return this.request<Ticket>(`/api/admin/tickets/${ticketId}`);
  }

  async resolveTicket(ticketId: UUID, data: TicketResolve): Promise<{ status: "ok"; message: string; ticket_id: string; notificacion_enviada: boolean }> {
    return this.request(`/api/admin/tickets/${ticketId}/resolver`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async changeTicketStatus(
    ticketId: UUID,
    estado: TicketEstado
  ): Promise<{ status: "ok"; ticket_id: string; nuevo_estado: TicketEstado }> {
    return this.request(`/api/admin/tickets/${ticketId}/estado`, {
      method: "PUT",
      params: new URLSearchParams({ estado }),
    });
  }

  async getStats(): Promise<TicketStatsResponse> {
    return this.request<TicketStatsResponse>("/api/admin/stats");
  }
}

// ============================================================================
// REACT HOOKS (OPTIONAL)
// ============================================================================

/**
 * React hook example for using the API client
 * 
 * Usage:
 * ```tsx
 * const { tickets, loading, error } = useTickets({ estado: 'pendiente' });
 * ```
 */

export interface UseTicketsOptions {
  estado?: TicketEstado;
  categoria?: TicketCategoria;
  prioridad?: TicketPrioridad;
  limit?: number;
  offset?: number;
}

// Example hook implementation (requires React)
/*
import { useState, useEffect } from 'react';

export function useTickets(options?: UseTicketsOptions) {
  const [tickets, setTickets] = useState<TicketListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const client = new GestorWSClient();
    client
      .listTickets(options)
      .then(setTickets)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [JSON.stringify(options)]);

  return { tickets, loading, error };
}

export function useTicket(ticketId: UUID | null) {
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!ticketId) {
      setTicket(null);
      setLoading(false);
      return;
    }

    const client = new GestorWSClient();
    client
      .getTicket(ticketId)
      .then(setTicket)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [ticketId]);

  return { ticket, loading, error };
}

export function useHealth() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const client = new GestorWSClient();
    client
      .getHealth()
      .then(setHealth)
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  return { health, loading, error };
}
*/

// ============================================================================
// TYPE GUARDS
// ============================================================================

export function isTicketEstado(value: string): value is TicketEstado {
  return ["pendiente", "en_proceso", "resuelto"].includes(value);
}

export function isTicketCategoria(value: string): value is TicketCategoria {
  return ["plan_pago", "reclamo", "baja", "consulta_admin"].includes(value);
}

export function isTicketPrioridad(value: string): value is TicketPrioridad {
  return ["baja", "media", "alta"].includes(value);
}

// ============================================================================
// CONSTANTS
// ============================================================================

export const TICKET_ESTADOS: TicketEstado[] = ["pendiente", "en_proceso", "resuelto"];
export const TICKET_CATEGORIAS: TicketCategoria[] = ["plan_pago", "reclamo", "baja", "consulta_admin"];
export const TICKET_PRIORIDADES: TicketPrioridad[] = ["baja", "media", "alta"];

export const CUOTA_ESTADOS = ["pendiente", "pagada", "vencida"] as const;
export type CuotaEstado = typeof CUOTA_ESTADOS[number];


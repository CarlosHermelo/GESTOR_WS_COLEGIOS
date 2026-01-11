export interface Message {
  from: 'padre' | 'bot';
  content: string;
  timestamp?: string;
}

export interface TicketContexto {
  estudiante: string;
  deuda_total: number;
  historial_pago: string;
  conversacion: Message[];
  whatsapp?: string;
}

export interface Ticket {
  id: string;
  erp_alumno_id: string;
  erp_responsable_id?: string;
  categoria: 'plan_pago' | 'reclamo' | 'baja' | 'consulta_admin';
  prioridad: 'baja' | 'media' | 'alta';
  motivo: string;
  contexto: TicketContexto;
  estado: 'pendiente' | 'en_proceso' | 'resuelto';
  respuesta_admin?: string;
  created_at: string;
  resolved_at?: string;
}

export interface TicketListResponse {
  tickets: Ticket[];
  total: number;
  pendientes: number;
  en_proceso: number;
  resueltos: number;
}

export interface TicketFilters {
  estado?: string;
  categoria?: string;
  prioridad?: string;
  limit?: number;
  offset?: number;
}

export interface TicketResponder {
  respuesta: string;
}


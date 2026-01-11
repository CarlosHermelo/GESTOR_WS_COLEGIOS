import { apiClient } from './client';
import type { Ticket, TicketListResponse, TicketFilters, TicketResponder } from '@/types';

export const ticketsApi = {
  getAll: async (filters?: TicketFilters): Promise<TicketListResponse> => {
    const { data } = await apiClient.get('/api/admin/tickets', { params: filters });
    return data;
  },

  getById: async (id: string): Promise<Ticket> => {
    const { data } = await apiClient.get(`/api/admin/tickets/${id}`);
    return data;
  },

  responder: async (id: string, body: TicketResponder): Promise<{ status: string; message: string }> => {
    const { data } = await apiClient.put(`/api/admin/tickets/${id}/resolver`, body);
    return data;
  },

  cambiarEstado: async (id: string, estado: string): Promise<{ status: string }> => {
    const { data } = await apiClient.put(`/api/admin/tickets/${id}/estado`, null, {
      params: { estado },
    });
    return data;
  },
};


import { apiClient } from './client';
import type { DashboardStats, TicketListResponse } from '@/types';

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const { data } = await apiClient.get('/api/admin/stats');
    return data.tickets || data;
  },

  getRecentTickets: async (limit: number = 5): Promise<TicketListResponse> => {
    const { data } = await apiClient.get('/api/admin/tickets', {
      params: { limit, offset: 0 },
    });
    return data;
  },
};


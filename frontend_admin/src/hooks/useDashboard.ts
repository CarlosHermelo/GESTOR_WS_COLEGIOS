import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/api';

export const useDashboardStats = () => {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => dashboardApi.getStats(),
    refetchInterval: 30000, // Refrescar cada 30 segundos
  });
};

export const useRecentTickets = (limit: number = 5) => {
  return useQuery({
    queryKey: ['dashboard', 'recent-tickets', limit],
    queryFn: () => dashboardApi.getRecentTickets(limit),
    refetchInterval: 30000,
  });
};


import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ticketsApi } from '@/api';
import type { TicketFilters, TicketResponder } from '@/types';

export const useTickets = (filters?: TicketFilters) => {
  return useQuery({
    queryKey: ['tickets', filters],
    queryFn: () => ticketsApi.getAll(filters),
  });
};

export const useTicket = (id: string) => {
  return useQuery({
    queryKey: ['ticket', id],
    queryFn: () => ticketsApi.getById(id),
    enabled: !!id,
  });
};

export const useResponderTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, respuesta }: { ticketId: string; respuesta: string }) =>
      ticketsApi.responder(ticketId, { respuesta } as TicketResponder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
      queryClient.invalidateQueries({ queryKey: ['ticket'] });
    },
  });
};

export const useCambiarEstadoTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, estado }: { ticketId: string; estado: string }) =>
      ticketsApi.cambiarEstado(ticketId, estado),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
      queryClient.invalidateQueries({ queryKey: ['ticket'] });
    },
  });
};


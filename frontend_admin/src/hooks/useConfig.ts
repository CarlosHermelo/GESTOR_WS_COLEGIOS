import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { configApi } from '@/api';
import type { ConfigUpdate } from '@/types';

export const useConfig = () => {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => configApi.get(),
  });
};

export const useUpdateConfig = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (config: ConfigUpdate) => configApi.update(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
};

export const useLLMModels = () => {
  return useQuery({
    queryKey: ['llm-models'],
    queryFn: () => configApi.getModels(),
    staleTime: Infinity, // No cambian frecuentemente
  });
};

export const useTestLLM = () => {
  return useMutation({
    mutationFn: ({ provider }: { provider: 'openai' | 'google' }) =>
      configApi.testLLM(provider),
  });
};


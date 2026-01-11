import { apiClient } from './client';
import type { Config, ConfigUpdate, LLMModels, TestLLMResponse } from '@/types';

export const configApi = {
  get: async (): Promise<Config> => {
    const { data } = await apiClient.get('/api/admin/config');
    return data;
  },

  update: async (config: ConfigUpdate): Promise<{ status: string; message: string }> => {
    const { data } = await apiClient.put('/api/admin/config', config);
    return data;
  },

  getModels: async (): Promise<LLMModels> => {
    const { data } = await apiClient.get('/api/admin/config/llm-models');
    return data;
  },

  testLLM: async (provider: 'openai' | 'google'): Promise<TestLLMResponse> => {
    const { data } = await apiClient.post('/api/admin/config/test-llm', { provider });
    return data;
  },
};


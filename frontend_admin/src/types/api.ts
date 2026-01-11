export interface ApiResponse<T> {
  status: 'ok' | 'error';
  data?: T;
  message?: string;
  error?: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  service: string;
  version: string;
  components: {
    database: 'connected' | 'disconnected';
    erp: 'connected' | 'disconnected';
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


export interface Config {
  llm_provider: 'openai' | 'google';
  llm_model: string;
  llm_temperature: number;
  llm_max_tokens: number;
  openai_api_key_configured: boolean;
  google_api_key_configured: boolean;
  whatsapp_configured: boolean;
}

export interface ConfigUpdate {
  llm_provider?: 'openai' | 'google';
  llm_model?: string;
  llm_temperature?: number;
  llm_max_tokens?: number;
  openai_api_key?: string;
  google_api_key?: string;
}

export interface LLMModels {
  openai: string[];
  google: string[];
}

export interface TestLLMResponse {
  success: boolean;
  error?: string;
  response?: string;
}


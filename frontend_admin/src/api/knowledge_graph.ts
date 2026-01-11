/**
 * API client para Knowledge Graph Analytics
 */
import { apiClient } from './client';

// Base URL del Knowledge Graph API
const KG_API_URL = import.meta.env.VITE_KG_API_URL || 'http://localhost:8002';

// Cliente específico para Knowledge Graph
const kgClient = apiClient.create?.({
  baseURL: KG_API_URL,
}) || apiClient;

// Si no hay método create, usar el default con baseURL modificado
const getKgClient = () => {
  if (apiClient.defaults?.baseURL === 'http://localhost:8000') {
    return {
      get: (url: string) => fetch(`${KG_API_URL}${url}`).then(r => r.json()),
      post: (url: string, data?: any) => fetch(`${KG_API_URL}${url}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: data ? JSON.stringify(data) : undefined
      }).then(r => r.json())
    };
  }
  return kgClient;
};

// ============== TIPOS ==============

export interface RiesgoDesercion {
  alumno_id: number;
  alumno_nombre: string;
  grado: string;
  responsable_nombre: string;
  responsable_whatsapp: string;
  perfil_responsable: string;
  nivel_riesgo_responsable: string;
  cuotas_vencidas: number;
  deuda_vencida: number;
  notif_ignoradas: number;
  score_riesgo: number;
  nivel_riesgo: 'ALTO' | 'MEDIO' | 'BAJO';
}

export interface ProyeccionCaja {
  fecha_inicio: string;
  fecha_fin: string;
  dias: number;
  cuotas_analizadas: number;
  monto_total_pendiente: number;
  monto_esperado_optimista: number;
  monto_esperado_realista: number;
  monto_esperado_pesimista: number;
  por_perfil: Record<string, {
    cantidad: number;
    monto_total: number;
    monto_esperado: number;
  }>;
}

export interface Cluster {
  tipo: string;
  perfil: string;
  riesgo: string;
  descripcion: string;
  caracteristicas: string[];
  recomendaciones: string[];
  estrategia: string;
  cantidad: number;
  generado_por: string;
}

export interface InsightsPredictivos {
  tendencias: string[];
  riesgos: string[];
  oportunidades: string[];
  acciones: string[];
  generado_por: string;
  timestamp: string;
}

export interface ResumenEjecutivo {
  metricas: {
    total_responsables: number;
    alto_riesgo: number;
    medio_riesgo: number;
    morosos: number;
    puntuales: number;
    cuotas_vencidas: number;
    monto_vencido: number;
    pct_alto_riesgo: number;
  };
  resumen_ejecutivo: string;
  generado_por: string;
  timestamp: string;
}

export interface GrafoStatus {
  status: string;
  nodos: Record<string, number>;
  relaciones: Record<string, number>;
  total_nodos: number;
  total_relaciones: number;
}

// ============== API CALLS ==============

export const knowledgeGraphApi = {
  // Riesgo de deserción
  getRiesgoDesercion: async (umbral = 40) => {
    const client = getKgClient();
    const response = await client.get(`/api/v1/reportes/riesgo-desercion?umbral=${umbral}`);
    return response.data || response;
  },

  getRiesgoAlto: async () => {
    const client = getKgClient();
    const response = await client.get('/api/v1/reportes/riesgo-desercion/alto');
    return response.data || response;
  },

  getEstadisticasRiesgo: async () => {
    const client = getKgClient();
    const response = await client.get('/api/v1/reportes/riesgo-desercion/estadisticas');
    return response.data || response;
  },

  // Proyección de caja
  getProyeccionCaja: async (dias = 90) => {
    const client = getKgClient();
    const response = await client.get(`/api/v1/reportes/proyeccion-caja?dias=${dias}`);
    return response.data || response;
  },

  getVencimientosProximos: async (dias = 7) => {
    const client = getKgClient();
    const response = await client.get(`/api/v1/reportes/vencimientos-proximos?dias=${dias}`);
    return response.data || response;
  },

  getDeudaPorGrado: async () => {
    const client = getKgClient();
    const response = await client.get('/api/v1/reportes/deuda-por-grado');
    return response.data || response;
  },

  // Clusters e Insights
  getClusters: async () => {
    const client = getKgClient();
    const response = await client.get('/api/v1/reportes/clusters');
    return response.data || response;
  },

  getInsightsPredictivos: async () => {
    const client = getKgClient();
    const response = await client.get('/api/v1/reportes/insights-predictivos');
    return response.data || response;
  },

  getResumenEjecutivo: async () => {
    const client = getKgClient();
    const response = await client.get('/api/v1/reportes/resumen-ejecutivo');
    return response.data || response;
  },

  getPatrones: async () => {
    const client = getKgClient();
    const response = await client.get('/api/v1/reportes/patrones');
    return response.data || response;
  },

  // Status
  getGrafoStatus: async () => {
    const client = getKgClient();
    const response = await client.get('/api/v1/reportes/status/grafo');
    return response.data || response;
  },

  getLlmStatus: async () => {
    const client = getKgClient();
    const response = await client.get('/api/v1/reportes/status/llm');
    return response.data || response;
  },

  // ETL triggers
  triggerSyncERP: async () => {
    const client = getKgClient();
    const response = await client.post('/api/v1/reportes/etl/sync-erp');
    return response.data || response;
  },

  triggerSyncGestor: async () => {
    const client = getKgClient();
    const response = await client.post('/api/v1/reportes/etl/sync-gestor');
    return response.data || response;
  },

  triggerLLMEnrichment: async () => {
    const client = getKgClient();
    const response = await client.post('/api/v1/reportes/etl/enrich-llm');
    return response.data || response;
  },

  triggerFullETL: async () => {
    const client = getKgClient();
    const response = await client.post('/api/v1/reportes/etl/full');
    return response.data || response;
  },
};


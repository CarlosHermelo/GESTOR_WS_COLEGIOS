export interface DashboardStats {
  consultas_totales?: number;
  resueltas_automaticamente?: number;
  tickets_pendientes?: number;
  tickets_en_proceso?: number;
  tickets_resueltos?: number;
  tickets_resueltos_24hs?: number;
  cuotas_cobradas_mes?: number;
  monto_cobrado_mes?: number;
  // Stats del backend actual
  por_estado?: Record<string, number>;
  por_categoria?: Record<string, number>;
  pendientes_por_prioridad?: Record<string, number>;
  total?: number;
}

export interface ConsultaPorDia {
  fecha: string;
  consultas: number;
  resueltas: number;
}

export interface DashboardData {
  stats: DashboardStats;
  consultas_por_dia: ConsultaPorDia[];
}


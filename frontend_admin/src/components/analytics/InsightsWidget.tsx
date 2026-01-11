/**
 * Widget de Insights Predictivos generados por IA
 */
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertTriangle, TrendingUp, Lightbulb, CheckCircle2 } from 'lucide-react';
import { knowledgeGraphApi, InsightsPredictivos } from '@/api/knowledge_graph';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';

export const InsightsWidget = () => {
  const { data, isLoading, error } = useQuery<InsightsPredictivos>({
    queryKey: ['insights-predictivos'],
    queryFn: knowledgeGraphApi.getInsightsPredictivos,
    refetchInterval: 5 * 60 * 1000, // Refrescar cada 5 minutos
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data || 'error' in data) {
    return (
      <Card className="border-amber-200 bg-amber-50">
        <CardHeader>
          <CardTitle className="text-amber-700">🤖 Insights Predictivos</CardTitle>
          <CardDescription className="text-amber-600">
            No hay insights disponibles. Ejecuta el proceso de enriquecimiento LLM.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const timeAgo = data.timestamp 
    ? formatDistanceToNow(new Date(data.timestamp), { addSuffix: true, locale: es })
    : 'desconocido';

  return (
    <Card className="border-violet-200 bg-gradient-to-br from-violet-50 to-indigo-50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-violet-900 flex items-center gap-2">
            <span className="text-2xl">🤖</span> 
            Insights Predictivos
          </CardTitle>
          <Badge variant="outline" className="text-xs bg-white">
            {data.generado_por}
          </Badge>
        </div>
        <CardDescription className="text-violet-600">
          Generado {timeAgo}
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Tendencias */}
        {data.tendencias?.length > 0 && (
          <div className="p-3 bg-white/60 rounded-lg border border-violet-100">
            <h4 className="font-semibold mb-2 flex items-center gap-2 text-violet-800">
              <TrendingUp className="h-4 w-4" />
              Tendencias Detectadas
            </h4>
            <ul className="space-y-1.5">
              {data.tendencias.map((tendencia, i) => (
                <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                  <span className="text-violet-400 mt-1">•</span>
                  {tendencia}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Riesgos */}
        {data.riesgos?.length > 0 && (
          <div className="p-3 bg-red-50/50 rounded-lg border border-red-100">
            <h4 className="font-semibold mb-2 flex items-center gap-2 text-red-700">
              <AlertTriangle className="h-4 w-4" />
              Riesgos (30 días)
            </h4>
            <ul className="space-y-1.5">
              {data.riesgos.map((riesgo, i) => (
                <li key={i} className="text-sm text-red-800 flex items-start gap-2">
                  <span className="text-red-400 mt-1">⚠️</span>
                  {riesgo}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Oportunidades */}
        {data.oportunidades?.length > 0 && (
          <div className="p-3 bg-emerald-50/50 rounded-lg border border-emerald-100">
            <h4 className="font-semibold mb-2 flex items-center gap-2 text-emerald-700">
              <Lightbulb className="h-4 w-4" />
              Oportunidades
            </h4>
            <ul className="space-y-1.5">
              {data.oportunidades.map((oportunidad, i) => (
                <li key={i} className="text-sm text-emerald-800 flex items-start gap-2">
                  <span className="text-emerald-400 mt-1">💡</span>
                  {oportunidad}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Acciones Prioritarias */}
        {data.acciones?.length > 0 && (
          <div className="p-3 bg-blue-50/50 rounded-lg border border-blue-100">
            <h4 className="font-semibold mb-2 flex items-center gap-2 text-blue-700">
              <CheckCircle2 className="h-4 w-4" />
              Acciones Prioritarias
            </h4>
            <ol className="space-y-1.5">
              {data.acciones.map((accion, i) => (
                <li key={i} className="text-sm text-blue-800 flex items-start gap-2">
                  <span className="font-bold text-blue-500 min-w-[20px]">{i + 1}.</span>
                  {accion}
                </li>
              ))}
            </ol>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default InsightsWidget;


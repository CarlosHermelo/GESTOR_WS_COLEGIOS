/**
 * Widget de Clusters de Comportamiento
 */
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Users, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { knowledgeGraphApi, Cluster } from '@/api/knowledge_graph';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface ClusterCardProps {
  cluster: Cluster;
}

const ClusterCard = ({ cluster }: ClusterCardProps) => {
  const [expanded, setExpanded] = useState(false);

  const getBadgeColor = (riesgo: string) => {
    switch (riesgo) {
      case 'ALTO':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'MEDIO':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'BAJO':
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const getProfileBadge = (perfil: string) => {
    switch (perfil) {
      case 'PUNTUAL':
        return 'bg-emerald-500 text-white';
      case 'EVENTUAL':
        return 'bg-amber-500 text-white';
      case 'MOROSO':
        return 'bg-red-500 text-white';
      case 'NUEVO':
        return 'bg-blue-500 text-white';
      default:
        return 'bg-gray-500 text-white';
    }
  };

  return (
    <div className="p-4 border rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge className={getProfileBadge(cluster.perfil)}>
            {cluster.perfil}
          </Badge>
          <Badge variant="outline" className={getBadgeColor(cluster.riesgo)}>
            Riesgo {cluster.riesgo}
          </Badge>
        </div>
        <div className="flex items-center gap-1 text-gray-500">
          <Users className="h-4 w-4" />
          <span className="text-sm font-medium">{cluster.cantidad}</span>
        </div>
      </div>
      
      <p className="text-sm text-gray-600 mb-3 line-clamp-2">
        {cluster.descripcion}
      </p>
      
      {/* Características */}
      {cluster.caracteristicas?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {cluster.caracteristicas.slice(0, 3).map((caract, i) => (
            <span 
              key={i}
              className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full"
            >
              {caract}
            </span>
          ))}
          {cluster.caracteristicas.length > 3 && (
            <span className="text-xs text-gray-400">
              +{cluster.caracteristicas.length - 3} más
            </span>
          )}
        </div>
      )}
      
      {/* Expandir/Colapsar */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-center gap-1 text-sm text-violet-600 hover:text-violet-800 py-1"
      >
        {expanded ? (
          <>
            <ChevronUp className="h-4 w-4" />
            Ver menos
          </>
        ) : (
          <>
            <ChevronDown className="h-4 w-4" />
            Ver recomendaciones
          </>
        )}
      </button>
      
      {/* Contenido expandido */}
      {expanded && (
        <div className="mt-3 pt-3 border-t space-y-3">
          {/* Recomendaciones */}
          {cluster.recomendaciones?.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                Recomendaciones
              </h5>
              <ul className="space-y-1">
                {cluster.recomendaciones.map((rec, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                    <span className="text-violet-500">•</span>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Estrategia */}
          {cluster.estrategia && (
            <div>
              <h5 className="text-xs font-semibold text-gray-500 uppercase mb-1">
                Estrategia de comunicación
              </h5>
              <p className="text-sm text-gray-700 italic">
                "{cluster.estrategia}"
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const ClustersWidget = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['clusters'],
    queryFn: knowledgeGraphApi.getClusters,
    refetchInterval: 10 * 60 * 1000, // Refrescar cada 10 minutos
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  const clusters = data?.clusters || [];

  if (error || clusters.length === 0) {
    return (
      <Card className="border-amber-200 bg-amber-50">
        <CardHeader>
          <CardTitle className="text-amber-700 flex items-center gap-2">
            <Users className="h-5 w-5" />
            Clusters de Comportamiento
          </CardTitle>
          <CardDescription className="text-amber-600">
            No hay clusters generados. Ejecuta el enriquecimiento LLM para crear clusters.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const totalResponsables = clusters.reduce((sum: number, c: Cluster) => sum + (c.cantidad || 0), 0);

  return (
    <Card className="border-indigo-200">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-indigo-900 flex items-center gap-2">
            <Users className="h-5 w-5" />
            Clusters de Comportamiento
          </CardTitle>
          <Badge variant="outline" className="bg-white flex items-center gap-1">
            <Sparkles className="h-3 w-3" />
            IA
          </Badge>
        </div>
        <CardDescription>
          {clusters.length} clusters • {totalResponsables} responsables clasificados
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2">
          {clusters.map((cluster: Cluster) => (
            <ClusterCard key={cluster.tipo} cluster={cluster} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default ClustersWidget;


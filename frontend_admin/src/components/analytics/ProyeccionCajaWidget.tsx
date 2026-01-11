/**
 * Widget de Proyección de Caja
 */
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { DollarSign, TrendingUp, TrendingDown, Wallet } from 'lucide-react';
import { knowledgeGraphApi, ProyeccionCaja } from '@/api/knowledge_graph';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

interface MetricCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  description?: string;
}

const MetricCard = ({ label, value, icon, color, description }: MetricCardProps) => (
  <div className={`p-4 rounded-lg border ${color}`}>
    <div className="flex items-center gap-2 mb-1">
      {icon}
      <span className="text-sm font-medium text-gray-600">{label}</span>
    </div>
    <div className="text-xl font-bold">{formatCurrency(value)}</div>
    {description && (
      <p className="text-xs text-gray-500 mt-1">{description}</p>
    )}
  </div>
);

export const ProyeccionCajaWidget = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['proyeccion-caja'],
    queryFn: () => knowledgeGraphApi.getProyeccionCaja(90),
    refetchInterval: 15 * 60 * 1000, // Cada 15 minutos
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const proyeccion: ProyeccionCaja | null = data?.proyeccion || null;

  if (error || !proyeccion) {
    return (
      <Card className="border-amber-200 bg-amber-50">
        <CardHeader>
          <CardTitle className="text-amber-700 flex items-center gap-2">
            <Wallet className="h-5 w-5" />
            Proyección de Caja
          </CardTitle>
          <CardDescription className="text-amber-600">
            No hay datos de proyección disponibles
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const tasaCobro = proyeccion.monto_total_pendiente > 0
    ? (proyeccion.monto_esperado_realista / proyeccion.monto_total_pendiente * 100).toFixed(1)
    : 0;

  return (
    <Card className="border-emerald-200">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-emerald-900 flex items-center gap-2">
            <Wallet className="h-5 w-5" />
            Proyección de Caja
          </CardTitle>
          <span className="text-sm text-gray-500">
            Próximos {proyeccion.dias} días
          </span>
        </div>
        <CardDescription>
          {proyeccion.cuotas_analizadas} cuotas analizadas • {tasaCobro}% tasa de cobro esperada
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <MetricCard
            label="Total Pendiente"
            value={proyeccion.monto_total_pendiente}
            icon={<DollarSign className="h-4 w-4 text-gray-500" />}
            color="bg-gray-50 border-gray-200"
            description="Monto total de cuotas"
          />
          
          <MetricCard
            label="Esperado (Realista)"
            value={proyeccion.monto_esperado_realista}
            icon={<TrendingUp className="h-4 w-4 text-emerald-600" />}
            color="bg-emerald-50 border-emerald-200"
            description="Escenario más probable"
          />
          
          <MetricCard
            label="Escenario Optimista"
            value={proyeccion.monto_esperado_optimista}
            icon={<TrendingUp className="h-4 w-4 text-blue-600" />}
            color="bg-blue-50 border-blue-200"
            description="Mejor caso"
          />
          
          <MetricCard
            label="Escenario Pesimista"
            value={proyeccion.monto_esperado_pesimista}
            icon={<TrendingDown className="h-4 w-4 text-red-600" />}
            color="bg-red-50 border-red-200"
            description="Peor caso"
          />
        </div>
        
        {/* Distribución por perfil */}
        {proyeccion.por_perfil && Object.keys(proyeccion.por_perfil).length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <h4 className="text-sm font-medium text-gray-600 mb-2">
              Por perfil de pagador
            </h4>
            <div className="space-y-2">
              {Object.entries(proyeccion.por_perfil).map(([perfil, data]) => (
                <div key={perfil} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">{perfil || 'Sin clasificar'}</span>
                  <div className="text-right">
                    <span className="font-medium">
                      {formatCurrency(data.monto_esperado)}
                    </span>
                    <span className="text-gray-400 ml-2">
                      ({data.cantidad} cuotas)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ProyeccionCajaWidget;


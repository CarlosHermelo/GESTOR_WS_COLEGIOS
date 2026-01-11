/**
 * Widget de Riesgo de Deserción
 */
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertTriangle, User, Phone, GraduationCap } from 'lucide-react';
import { knowledgeGraphApi, RiesgoDesercion } from '@/api/knowledge_graph';

export const RiesgoDesercionWidget = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['riesgo-desercion-alto'],
    queryFn: knowledgeGraphApi.getRiesgoAlto,
    refetchInterval: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  const alumnos: RiesgoDesercion[] = data?.alumnos_alto_riesgo || [];

  if (error || alumnos.length === 0) {
    return (
      <Card className="border-emerald-200 bg-emerald-50">
        <CardHeader>
          <CardTitle className="text-emerald-700 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Riesgo de Deserción
          </CardTitle>
          <CardDescription className="text-emerald-600">
            ✅ No hay alumnos en riesgo alto de deserción
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const getRiskBadge = (nivel: string) => {
    switch (nivel) {
      case 'ALTO':
        return 'bg-red-500 text-white';
      case 'MEDIO':
        return 'bg-amber-500 text-white';
      case 'BAJO':
        return 'bg-emerald-500 text-white';
      default:
        return 'bg-gray-500 text-white';
    }
  };

  return (
    <Card className="border-red-200">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-red-900 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Riesgo de Deserción
          </CardTitle>
          <Badge variant="destructive">
            {alumnos.length} en riesgo
          </Badge>
        </div>
        <CardDescription className="text-red-600">
          Alumnos que requieren atención inmediata
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-3">
          {alumnos.slice(0, 5).map((alumno) => (
            <div 
              key={alumno.alumno_id}
              className="p-3 border rounded-lg bg-red-50/50 hover:bg-red-50 transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-gray-500" />
                  <span className="font-medium text-gray-900">
                    {alumno.alumno_nombre}
                  </span>
                </div>
                <Badge className={getRiskBadge(alumno.nivel_riesgo)}>
                  Score: {alumno.score_riesgo}
                </Badge>
              </div>
              
              <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                <div className="flex items-center gap-1">
                  <GraduationCap className="h-3.5 w-3.5" />
                  {alumno.grado}
                </div>
                <div className="flex items-center gap-1">
                  <Phone className="h-3.5 w-3.5" />
                  {alumno.responsable_whatsapp || 'Sin teléfono'}
                </div>
              </div>
              
              <div className="mt-2 flex flex-wrap gap-1">
                <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded">
                  {alumno.cuotas_vencidas} cuotas vencidas
                </span>
                {alumno.notif_ignoradas > 0 && (
                  <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded">
                    {alumno.notif_ignoradas} notif. ignoradas
                  </span>
                )}
                {alumno.perfil_responsable && (
                  <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-700 rounded">
                    {alumno.perfil_responsable}
                  </span>
                )}
              </div>
            </div>
          ))}
          
          {alumnos.length > 5 && (
            <p className="text-sm text-center text-gray-500">
              Y {alumnos.length - 5} alumnos más...
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default RiesgoDesercionWidget;


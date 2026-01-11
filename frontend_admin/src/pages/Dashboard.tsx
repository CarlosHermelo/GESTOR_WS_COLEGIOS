import { Header } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useDashboardStats, useRecentTickets } from '@/hooks';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  TrendingUp,
  Clock,
  AlertCircle,
  DollarSign,
  CheckCircle,
  Loader2,
} from 'lucide-react';
import { formatDate, formatCurrency, getPriorityVariant } from '@/lib/utils';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  variant?: 'default' | 'warning' | 'success';
  description?: string;
}

const MetricCard = ({ title, value, icon, variant = 'default', description }: MetricCardProps) => {
  const bgColors = {
    default: 'bg-blue-50 text-blue-600',
    warning: 'bg-orange-50 text-orange-600',
    success: 'bg-green-50 text-green-600',
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold mt-2">{value}</p>
            {description && (
              <p className="text-xs text-muted-foreground mt-1">{description}</p>
            )}
          </div>
          <div className={`p-3 rounded-lg ${bgColors[variant]}`}>{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
};

export const Dashboard = () => {
  const navigate = useNavigate();
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: ticketsData, isLoading: ticketsLoading } = useRecentTickets(5);

  // Datos mock para el gráfico (hasta que el backend los provea)
  const chartData = [
    { fecha: 'Lun', consultas: 45, resueltas: 35 },
    { fecha: 'Mar', consultas: 52, resueltas: 48 },
    { fecha: 'Mié', consultas: 38, resueltas: 30 },
    { fecha: 'Jue', consultas: 65, resueltas: 55 },
    { fecha: 'Vie', consultas: 48, resueltas: 42 },
    { fecha: 'Sáb', consultas: 22, resueltas: 20 },
    { fecha: 'Dom', consultas: 15, resueltas: 12 },
  ];

  const totalConsultas = stats?.por_estado
    ? Object.values(stats.por_estado).reduce((a, b) => a + b, 0)
    : stats?.total || 0;

  return (
    <div>
      <Header title="Dashboard" subtitle="Vista general del sistema de cobranza" />

      <div className="p-6 space-y-6">
        {/* Métricas principales */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Consultas Totales"
            value={statsLoading ? '...' : totalConsultas.toLocaleString()}
            icon={<BarChart3 className="w-6 h-6" />}
          />
          <MetricCard
            title="Tasa de Resolución"
            value={statsLoading ? '...' : '78.5%'}
            icon={<TrendingUp className="w-6 h-6" />}
            variant="success"
            description="Automáticamente"
          />
          <MetricCard
            title="Tiempo Promedio"
            value="8 min"
            icon={<Clock className="w-6 h-6" />}
          />
          <MetricCard
            title="Tickets Pendientes"
            value={statsLoading ? '...' : ticketsData?.pendientes || 0}
            icon={<AlertCircle className="w-6 h-6" />}
            variant={ticketsData?.pendientes ? 'warning' : 'default'}
          />
        </div>

        {/* Segunda fila de métricas */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            title="Cuotas Cobradas (Mes)"
            value={statsLoading ? '...' : '47'}
            icon={<CheckCircle className="w-6 h-6" />}
            variant="success"
          />
          <MetricCard
            title="Monto Cobrado (Mes)"
            value={statsLoading ? '...' : formatCurrency(2115000)}
            icon={<DollarSign className="w-6 h-6" />}
            variant="success"
          />
          <MetricCard
            title="En Proceso"
            value={statsLoading ? '...' : ticketsData?.en_proceso || 0}
            icon={<Loader2 className="w-6 h-6" />}
          />
        </div>

        {/* Gráfico de consultas */}
        <Card>
          <CardHeader>
            <CardTitle>Consultas por Día (Última Semana)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="fecha" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="consultas"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    name="Total Consultas"
                  />
                  <Line
                    type="monotone"
                    dataKey="resueltas"
                    stroke="#22c55e"
                    strokeWidth={2}
                    name="Resueltas Auto"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Tickets recientes */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Tickets Recientes</CardTitle>
            <Button variant="outline" onClick={() => navigate('/tickets')}>
              Ver todos
            </Button>
          </CardHeader>
          <CardContent>
            {ticketsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
              </div>
            ) : ticketsData?.tickets.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>¡No hay tickets pendientes!</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Alumno</TableHead>
                    <TableHead>Categoría</TableHead>
                    <TableHead>Prioridad</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ticketsData?.tickets.map((ticket) => (
                    <TableRow key={ticket.id}>
                      <TableCell className="font-mono text-sm">
                        #{ticket.id.slice(0, 8)}
                      </TableCell>
                      <TableCell>{ticket.contexto?.estudiante || 'N/A'}</TableCell>
                      <TableCell className="capitalize">
                        {ticket.categoria?.replace('_', ' ')}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getPriorityVariant(ticket.prioridad)}>
                          {ticket.prioridad}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={ticket.estado === 'pendiente' ? 'destructive' : 'secondary'}>
                          {ticket.estado}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(ticket.created_at)}
                      </TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => navigate(`/tickets/${ticket.id}`)}
                        >
                          Ver
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};


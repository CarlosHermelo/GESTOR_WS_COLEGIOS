import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useTickets } from '@/hooks';
import { formatDate, getPriorityVariant, getEstadoBadgeVariant } from '@/lib/utils';
import { Loader2, Search, Filter, Eye } from 'lucide-react';

export const Tickets = () => {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<{
    estado?: string;
    categoria?: string;
    prioridad?: string;
  }>({});
  const [search, setSearch] = useState('');

  const { data: ticketData, isLoading } = useTickets({
    ...filters,
    limit: 50,
  });

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === 'todos' ? undefined : value,
    }));
  };

  const filteredTickets = ticketData?.tickets.filter((ticket) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      ticket.id.toLowerCase().includes(searchLower) ||
      ticket.contexto?.estudiante?.toLowerCase().includes(searchLower) ||
      ticket.motivo?.toLowerCase().includes(searchLower)
    );
  });

  return (
    <div>
      <Header
        title="Tickets"
        subtitle={`${ticketData?.pendientes || 0} pendientes | ${ticketData?.en_proceso || 0} en proceso | ${ticketData?.resueltos || 0} resueltos`}
      />

      <div className="p-6 space-y-6">
        {/* Resumen */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-red-50 border-red-200">
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-red-600">
                {ticketData?.pendientes || 0}
              </div>
              <div className="text-sm text-red-600">Pendientes</div>
            </CardContent>
          </Card>
          <Card className="bg-yellow-50 border-yellow-200">
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-yellow-600">
                {ticketData?.en_proceso || 0}
              </div>
              <div className="text-sm text-yellow-600">En Proceso</div>
            </CardContent>
          </Card>
          <Card className="bg-green-50 border-green-200">
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-green-600">
                {ticketData?.resueltos || 0}
              </div>
              <div className="text-sm text-green-600">Resueltos</div>
            </CardContent>
          </Card>
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-blue-600">
                {ticketData?.total || 0}
              </div>
              <div className="text-sm text-blue-600">Total</div>
            </CardContent>
          </Card>
        </div>

        {/* Filtros */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="w-5 h-5" />
              Filtros
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              <div className="w-[200px]">
                <Select
                  value={filters.estado || 'todos'}
                  onValueChange={(value) => handleFilterChange('estado', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Estado" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todos los estados</SelectItem>
                    <SelectItem value="pendiente">Pendiente</SelectItem>
                    <SelectItem value="en_proceso">En Proceso</SelectItem>
                    <SelectItem value="resuelto">Resuelto</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="w-[200px]">
                <Select
                  value={filters.categoria || 'todos'}
                  onValueChange={(value) => handleFilterChange('categoria', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Categoría" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todas las categorías</SelectItem>
                    <SelectItem value="plan_pago">Plan de Pago</SelectItem>
                    <SelectItem value="reclamo">Reclamo</SelectItem>
                    <SelectItem value="baja">Baja</SelectItem>
                    <SelectItem value="consulta_admin">Consulta Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="w-[200px]">
                <Select
                  value={filters.prioridad || 'todos'}
                  onValueChange={(value) => handleFilterChange('prioridad', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Prioridad" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todas las prioridades</SelectItem>
                    <SelectItem value="alta">Alta</SelectItem>
                    <SelectItem value="media">Media</SelectItem>
                    <SelectItem value="baja">Baja</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex-1 min-w-[250px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar por alumno, ID o motivo..."
                    className="pl-10"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tabla */}
        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
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
                    <TableHead>Motivo</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTickets?.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                        No se encontraron tickets
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredTickets?.map((ticket) => (
                      <TableRow
                        key={ticket.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => navigate(`/tickets/${ticket.id}`)}
                      >
                        <TableCell className="font-mono text-sm">
                          #{ticket.id.slice(0, 8)}
                        </TableCell>
                        <TableCell className="font-medium">
                          {ticket.contexto?.estudiante || 'N/A'}
                        </TableCell>
                        <TableCell>
                          <span className="capitalize">
                            {ticket.categoria?.replace('_', ' ')}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getPriorityVariant(ticket.prioridad)}>
                            {ticket.prioridad}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getEstadoBadgeVariant(ticket.estado)}>
                            {ticket.estado.replace('_', ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate">
                          {ticket.motivo}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(ticket.created_at)}
                        </TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/tickets/${ticket.id}`);
                            }}
                          >
                            <Eye className="w-4 h-4 mr-1" />
                            Ver
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};


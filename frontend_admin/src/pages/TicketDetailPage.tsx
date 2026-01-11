import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useTicket, useResponderTicket } from '@/hooks';
import { formatDate, formatCurrency, getPriorityVariant } from '@/lib/utils';
import { toast } from 'sonner';
import {
  ArrowLeft,
  User,
  DollarSign,
  History,
  MessageSquare,
  Send,
  Loader2,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';

export const TicketDetailPage = () => {
  const { ticketId } = useParams<{ ticketId: string }>();
  const navigate = useNavigate();
  const { data: ticket, isLoading } = useTicket(ticketId || '');
  const { mutate: responder, isPending } = useResponderTicket();
  const [respuesta, setRespuesta] = useState('');

  const handleSubmit = () => {
    if (!respuesta.trim() || respuesta.length < 10) {
      toast.error('La respuesta debe tener al menos 10 caracteres');
      return;
    }

    responder(
      { ticketId: ticketId!, respuesta },
      {
        onSuccess: () => {
          toast.success('Respuesta enviada correctamente');
          setRespuesta('');
        },
        onError: (error) => {
          toast.error(`Error al enviar: ${error.message}`);
        },
      }
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <AlertCircle className="w-12 h-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Ticket no encontrado</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/tickets')}>
          Volver a Tickets
        </Button>
      </div>
    );
  }

  return (
    <div>
      <Header
        title={`Ticket #${ticket.id.slice(0, 8)}`}
        subtitle={`${ticket.categoria?.replace('_', ' ')} - ${ticket.estado}`}
      />

      <div className="p-6 max-w-4xl mx-auto space-y-6">
        {/* Botón Volver */}
        <Button variant="outline" onClick={() => navigate('/tickets')}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Volver a Tickets
        </Button>

        {/* Header del Ticket */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-xl">
                  Ticket #{ticket.id.slice(0, 8)}
                </CardTitle>
                <CardDescription className="mt-1">
                  Creado el {formatDate(ticket.created_at)}
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Badge variant={getPriorityVariant(ticket.prioridad)}>
                  {ticket.prioridad.toUpperCase()}
                </Badge>
                <Badge
                  variant={
                    ticket.estado === 'resuelto'
                      ? 'secondary'
                      : ticket.estado === 'pendiente'
                      ? 'destructive'
                      : 'default'
                  }
                >
                  {ticket.estado.replace('_', ' ').toUpperCase()}
                </Badge>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Información del contexto */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <User className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Alumno</p>
                  <p className="font-semibold">
                    {ticket.contexto?.estudiante || 'No especificado'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <DollarSign className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Deuda Total</p>
                  <p className="font-semibold text-lg">
                    {ticket.contexto?.deuda_total
                      ? formatCurrency(ticket.contexto.deuda_total)
                      : 'N/A'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <History className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Historial de Pago</p>
                  <p className="font-semibold capitalize">
                    {ticket.contexto?.historial_pago || 'Sin datos'}
                  </p>
                </div>
              </div>
            </div>

            {/* Motivo */}
            <div className="p-4 border-l-4 border-yellow-400 bg-yellow-50 rounded-r-lg">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-yellow-600" />
                Motivo del Escalamiento
              </h3>
              <p className="text-slate-700">{ticket.motivo}</p>
            </div>

            {/* Conversación */}
            {ticket.contexto?.conversacion && ticket.contexto.conversacion.length > 0 && (
              <div>
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <MessageSquare className="w-5 h-5" />
                  Historial de Conversación
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto border rounded-lg p-3 bg-slate-50">
                  {ticket.contexto.conversacion.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg ${
                        msg.from === 'padre'
                          ? 'bg-white border'
                          : 'bg-blue-50 border border-blue-100'
                      }`}
                    >
                      <span className="font-semibold text-sm">
                        {msg.from === 'padre' ? '👤 Padre:' : '🤖 Bot:'}
                      </span>{' '}
                      <span className="text-slate-700">{msg.content}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Respuesta del Admin (si ya está resuelto) */}
            {ticket.estado === 'resuelto' && ticket.respuesta_admin && (
              <Alert variant="success" className="border-green-500 bg-green-50">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <AlertDescription>
                  <h4 className="font-semibold text-green-800 mb-1">Ticket Resuelto</h4>
                  <p className="text-green-700">{ticket.respuesta_admin}</p>
                  {ticket.resolved_at && (
                    <p className="text-xs text-green-600 mt-2">
                      Resuelto el {formatDate(ticket.resolved_at)}
                    </p>
                  )}
                </AlertDescription>
              </Alert>
            )}

            {/* Formulario de Respuesta (si no está resuelto) */}
            {ticket.estado !== 'resuelto' && (
              <div className="space-y-4 pt-4 border-t">
                <div>
                  <Label htmlFor="respuesta" className="text-base font-semibold">
                    Tu Respuesta
                  </Label>
                  <p className="text-sm text-muted-foreground mb-3">
                    Esta respuesta será reformulada automáticamente por el agente antes de
                    enviarla al padre.
                  </p>
                  <Textarea
                    id="respuesta"
                    value={respuesta}
                    onChange={(e) => setRespuesta(e.target.value)}
                    rows={4}
                    placeholder="Ej: Aprobar plan de 3 cuotas mensuales sin recargo. Montos: $50.000 c/u. Vencimientos: 15/02, 15/03, 15/04"
                    className="resize-none"
                  />
                </div>

                <div className="flex gap-2">
                  <Button onClick={handleSubmit} disabled={!respuesta.trim() || isPending}>
                    {isPending ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Enviando...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4 mr-2" />
                        Enviar Respuesta
                      </>
                    )}
                  </Button>
                  <Button variant="outline" disabled={isPending}>
                    Guardar Borrador
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};


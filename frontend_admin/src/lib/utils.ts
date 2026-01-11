import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount)
}

export function getPriorityVariant(priority: string): "default" | "secondary" | "destructive" | "outline" {
  switch (priority.toLowerCase()) {
    case 'alta':
      return 'destructive'
    case 'media':
      return 'default'
    case 'baja':
      return 'secondary'
    default:
      return 'outline'
  }
}

export function getEstadoBadgeVariant(estado: string): "default" | "secondary" | "destructive" | "outline" {
  switch (estado.toLowerCase()) {
    case 'pendiente':
      return 'destructive'
    case 'en_proceso':
      return 'default'
    case 'resuelto':
      return 'secondary'
    default:
      return 'outline'
  }
}


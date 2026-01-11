# Frontend Admin - Gestor WS

Panel administrativo para el sistema de Gestión de Cobranza por WhatsApp.

## Stack Técnico

- **Frontend:** React 18 + TypeScript
- **Routing:** React Router v6
- **UI:** TailwindCSS + shadcn/ui
- **State:** TanStack Query (React Query)
- **HTTP:** Axios
- **Charts:** Recharts
- **Build:** Vite

## Requisitos Previos

- Node.js 18+
- Backend Gestor WS corriendo en `http://localhost:8000`

## Instalación

```bash
# Instalar dependencias
npm install

# Iniciar en desarrollo
npm run dev

# Build para producción
npm run build

# Preview del build
npm run preview
```

## Estructura del Proyecto

```
frontend_admin/
├── src/
│   ├── main.tsx              # Entry point
│   ├── App.tsx               # Router y providers
│   │
│   ├── components/
│   │   ├── ui/               # Componentes shadcn/ui
│   │   └── layout/           # Layout (Sidebar, Header)
│   │
│   ├── pages/
│   │   ├── Dashboard.tsx     # Página principal con métricas
│   │   ├── Tickets.tsx       # Lista de tickets
│   │   ├── TicketDetailPage.tsx # Detalle de ticket
│   │   └── Configuracion.tsx # Configuración LLM
│   │
│   ├── api/                  # Clientes API
│   ├── hooks/                # React Query hooks
│   ├── types/                # TypeScript types
│   └── lib/                  # Utilidades
│
├── tailwind.config.js
├── vite.config.ts
└── package.json
```

## Páginas Principales

### Dashboard
- Métricas en tiempo real
- Gráfico de consultas por día
- Tickets recientes

### Tickets
- Lista con filtros (estado, categoría, prioridad)
- Búsqueda por alumno o motivo
- Vista detallada con historial de conversación
- Formulario para responder tickets

### Configuración
- Selector de proveedor LLM (OpenAI / Google Gemini)
- Selector de modelo
- Configuración de temperature y max tokens
- Gestión de API keys
- Test de conexión con LLM

## Variables de Entorno

```bash
# URL del backend (por defecto http://localhost:8000)
VITE_API_URL=http://localhost:8000
```

## Desarrollo

```bash
# Desarrollo con hot reload
npm run dev

# El frontend estará disponible en http://localhost:5173
```

## Docker

```dockerfile
# Dockerfile incluido para containerización
docker build -t gestor-ws-frontend .
docker run -p 5173:5173 gestor-ws-frontend
```

## Conexión con Backend

El frontend se conecta al backend en `http://localhost:8000` (configurable via `VITE_API_URL`).

### Endpoints consumidos:

- `GET /api/admin/tickets` - Lista tickets
- `GET /api/admin/tickets/:id` - Detalle ticket
- `PUT /api/admin/tickets/:id/resolver` - Resolver ticket
- `GET /api/admin/stats` - Estadísticas dashboard
- `GET /api/admin/config` - Configuración actual
- `PUT /api/admin/config` - Actualizar configuración
- `POST /api/admin/config/test-llm` - Test conexión LLM
- `GET /api/admin/config/llm-models` - Modelos disponibles

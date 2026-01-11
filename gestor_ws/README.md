# Gestor WS - Sistema de Cobranza por WhatsApp

Backend del sistema de gestión de cobranza escolar que se integra con el ERP Mock y utiliza WhatsApp como canal de comunicación.

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        GESTOR WS                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐    │
│  │   Router    │→ │  Asistente   │→ │    Coordinador      │    │
│  │ (Keywords)  │  │  (LLM+Tools) │  │    (LangGraph)      │    │
│  └─────────────┘  └──────────────┘  └─────────────────────┘    │
│         │                │                    │                 │
│         ▼                ▼                    ▼                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   LLM Factory                            │   │
│  │           (OpenAI GPT / Google Gemini)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │  ERP Mock   │  │  PostgreSQL  │  │  WhatsApp Service   │   │
│  │  Adapter    │  │   (Cache)    │  │  (Meta Cloud API)   │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Stack Técnico

- **Backend:** FastAPI (Python 3.11+)
- **Base de datos:** PostgreSQL 15
- **LLM:** LangChain + OpenAI GPT / Google Gemini (configurable)
- **Orquestación de Agentes:** LangGraph
- **WhatsApp:** Meta Cloud API (simulado inicialmente)
- **Cliente ERP:** httpx (async)
- **Containerización:** Docker + Docker Compose

## 📁 Estructura del Proyecto

```
gestor_ws/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI principal
│   ├── config.py            # Settings
│   ├── database.py          # Conexión PostgreSQL
│   │
│   ├── llm/                 # LLM Factory
│   │   ├── __init__.py
│   │   ├── factory.py       # Factory para OpenAI/Gemini
│   │   └── base.py          # Interface común
│   │
│   ├── adapters/            # Integración ERP
│   │   ├── __init__.py
│   │   ├── erp_interface.py # Interface abstracta
│   │   └── mock_erp_adapter.py
│   │
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── interacciones.py
│   │   └── tickets.py
│   │
│   ├── agents/              # LLM Agents
│   │   ├── __init__.py
│   │   ├── router.py        # Clasificación simple
│   │   ├── asistente.py     # Asistente Virtual
│   │   └── coordinador.py   # Agente Autónomo (LangGraph)
│   │
│   ├── tools/               # Herramientas LLM
│   │   ├── __init__.py
│   │   ├── consultar_erp.py
│   │   ├── tickets.py
│   │   └── notificaciones.py
│   │
│   ├── api/                 # Endpoints
│   │   ├── __init__.py
│   │   ├── webhooks_erp.py
│   │   ├── webhooks_whatsapp.py
│   │   └── admin.py
│   │
│   ├── services/            # Lógica de negocio
│   │   ├── __init__.py
│   │   ├── sync_service.py
│   │   ├── whatsapp_service.py
│   │   └── notification_service.py
│   │
│   └── schemas/             # Pydantic schemas
│       ├── __init__.py
│       ├── erp.py
│       ├── whatsapp.py
│       └── tickets.py
│
├── scripts/
│   └── test_whatsapp.py
│
├── tests/
│   ├── test_router.py
│   ├── test_asistente.py
│   ├── test_llm_factory.py
│   └── test_webhooks.py
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── env.example
└── README.md
```

## ⚙️ Configuración

### 1. Variables de Entorno

Copiar `env.example` a `.env` y configurar:

```bash
cp env.example .env
```

### 2. Configuración LLM

El sistema soporta **OpenAI** y **Google Gemini**. Configurar en `.env`:

```env
# Para OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-proj-xxx...

# Para Google Gemini
LLM_PROVIDER=google
LLM_MODEL=gemini-2.0-flash-exp
GOOGLE_API_KEY=AIzaSyxxx...
```

### 3. Modelos Disponibles

| Provider | Modelos |
|----------|---------|
| OpenAI | gpt-4o, gpt-4-turbo, gpt-4, gpt-3.5-turbo |
| Google | gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash |

## 🐳 Ejecución con Docker

### Prerequisitos

- Docker y Docker Compose instalados
- ERP Mock corriendo en `localhost:8001`

### Levantar el sistema

```bash
# Asegurarse que ERP Mock está corriendo
cd ../erp_mock
docker-compose up -d

# Volver a gestor_ws y levantar
cd ../gestor_ws
docker-compose up -d
```

### Ver logs

```bash
# Ver todos los logs
docker-compose logs -f

# Ver solo logs de la API
docker-compose logs -f api
```

### Validar configuración LLM

En los logs deberías ver:

```
🤖 Configurando LLM...
   Provider: openai
   Model: gpt-4o
   ✅ LLM configurado correctamente
```

## 🧪 Testing

### Ejecutar tests

```bash
# Desde Docker
docker-compose exec api pytest

# Con cobertura
docker-compose exec api pytest --cov=app
```

### Probar mensaje de WhatsApp (simulado)

```bash
python scripts/test_whatsapp.py "+5491112345005" "Cuánto debo?"
```

## 📡 Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/webhook/whatsapp` | Recibe mensajes WhatsApp |
| POST | `/webhook/erp/pago-confirmado` | Webhook de pago confirmado |
| POST | `/webhook/erp/cuota-generada` | Webhook de nueva cuota |
| GET | `/api/admin/tickets` | Lista tickets pendientes |
| PUT | `/api/admin/tickets/{id}/resolver` | Resuelve un ticket |

## 🔄 Flujo de Mensajes

1. **Mensaje entra** por webhook WhatsApp
2. **Router** clasifica por keywords (simple → asistente, complejo → agente)
3. **Asistente** procesa consultas simples con LLM + herramientas
4. **Coordinador** maneja casos complejos con LangGraph
5. **Respuesta** se envía por WhatsApp

## 🔧 Cambiar Provider LLM

Para cambiar de OpenAI a Gemini (o viceversa):

1. Editar `.env`:
```env
LLM_PROVIDER=google
LLM_MODEL=gemini-2.0-flash-exp
```

2. Reiniciar:
```bash
docker-compose restart api
```

## 📝 Licencia

MIT


# MCP Tools Server

Servidor de herramientas centralizado para agentes LLM, implementado con el protocolo MCP (Model Context Protocol).

## 🎯 Propósito

Este servidor expone todas las herramientas (tools) que pueden usar los agentes LLM de forma centralizada:

- **Desacoplamiento**: Las tools están separadas del agente
- **Discovery**: El agente puede consultar qué tools están disponibles
- **Testing**: Fácil de testear con modo mock
- **Escalabilidad**: Agregar tools sin modificar el agente

## 📁 Estructura

```
mcp_tools/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI Application
│   ├── config.py            # Configuración
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py        # MCP Protocol handler
│   │   └── registry.py      # Tool registry
│   └── tools/
│       ├── __init__.py
│       ├── base.py          # Utilidades base
│       ├── erp_tools.py     # Tools de ERP
│       ├── admin_tools.py   # Tools administrativas
│       ├── kg_tools.py      # Tools de Knowledge Graph
│       └── notif_tools.py   # Tools de notificaciones
├── tests/
│   ├── conftest.py
│   └── test_tools.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🔧 Tools Disponibles

### ERP (erp)
| Tool | Descripción |
|------|-------------|
| `consultar_estado_cuenta` | Consulta estado de cuenta por WhatsApp |
| `obtener_link_pago` | Obtiene link de pago para una cuota |
| `registrar_confirmacion_pago` | Registra confirmación de pago |
| `buscar_alumno` | Busca información de un alumno |

### Admin (admin)
| Tool | Descripción |
|------|-------------|
| `crear_ticket` | Crea ticket de escalamiento |
| `buscar_ticket` | Busca información de un ticket |
| `clasificar_prioridad` | Clasifica prioridad de un caso |
| `listar_tickets_pendientes` | Lista tickets pendientes |

### Knowledge Graph (kg)
| Tool | Descripción |
|------|-------------|
| `buscar_horarios` | Busca horarios de clases |
| `buscar_calendario` | Busca calendario escolar |
| `buscar_autoridades` | Busca info de autoridades |
| `buscar_contacto` | Busca info de contacto |
| `buscar_info_general` | Búsqueda semántica general |
| `analizar_patrones_pago` | Analiza patrones de pago |
| `calcular_riesgo_desercion` | Calcula riesgo de deserción |

### Notificaciones (notif)
| Tool | Descripción |
|------|-------------|
| `enviar_whatsapp` | Envía mensaje WhatsApp |
| `registrar_notificacion` | Registra notificación enviada |
| `obtener_cuotas_por_vencer` | Obtiene cuotas próximas a vencer |
| `enviar_recordatorios_masivos` | Envía recordatorios masivos |

## 🚀 Ejecución

### Local (desarrollo)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar entorno
cp .env.example .env
# Editar .env con tus valores

# Ejecutar servidor
python -m app.main
```

### Docker

```bash
# Build y run
docker-compose up --build

# Solo build
docker build -t mcp_tools .

# Run
docker run -p 8003:8003 mcp_tools
```

### Con gestor_ws (integrado)

```bash
cd gestor_ws
docker-compose up --build
```

## 📡 API Endpoints

### REST API

```bash
# Health check
GET /health

# Listar tools
GET /tools
GET /tools?category=erp

# Schema de una tool
GET /tools/{tool_name}

# Ejecutar tool
POST /tools/{tool_name}/call
{
  "name": "consultar_estado_cuenta",
  "arguments": {"whatsapp": "+5491112345001"}
}
```

### MCP Protocol (JSON-RPC)

```bash
# Listar tools
POST /mcp
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "id": "1"
}

# Ejecutar tool
POST /mcp
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "consultar_estado_cuenta",
    "arguments": {"whatsapp": "+5491112345001"}
  },
  "id": "2"
}
```

## 🧪 Testing

```bash
# Ejecutar tests
pytest tests/ -v

# Con coverage
pytest tests/ --cov=app --cov-report=html
```

## 📝 Agregar una nueva Tool

1. Elegir o crear módulo en `app/tools/`
2. Usar el decorador `@tool`:

```python
from app.mcp.registry import tool

@tool(
    category="erp",  # erp, admin, kg, notif
    mock_response={"found": True, "data": "mock"}  # Opcional
)
async def mi_nueva_tool(param1: str, param2: int = 10) -> dict:
    """
    Descripción de lo que hace la tool.
    
    Args:
        param1: Descripción del parámetro
        param2: Otro parámetro con default
    
    Returns:
        dict con el resultado
    """
    if settings.MOCK_MODE:
        return {"found": True, "data": "mock"}
    
    # Lógica real
    return {"found": True, "data": "real"}
```

3. Importar en `app/tools/__init__.py`
4. La tool se registra automáticamente

## 🔗 Uso desde el Agente

```python
from app.mcp_client import MCPClient, call_mcp_tool

# Opción 1: Usar cliente
client = MCPClient()
tools = await client.list_tools()
result = await client.call_tool("consultar_estado_cuenta", {"whatsapp": "+54..."})

# Opción 2: Función directa
result = await call_mcp_tool("consultar_estado_cuenta", {"whatsapp": "+54..."})
```

## ⚙️ Configuración

| Variable | Descripción | Default |
|----------|-------------|---------|
| `MOCK_MODE` | Usa datos mock | `true` |
| `ERP_URL` | URL del ERP | `http://localhost:8001` |
| `KNOWLEDGE_GRAPH_URL` | URL del KG | `http://localhost:8002` |
| `GESTOR_WS_URL` | URL del Gestor | `http://localhost:8000` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

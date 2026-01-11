# ERP Mock API 🏫

API REST que simula un sistema de gestión escolar (ERP) para desarrollo y testing.

## 📋 Características

- ✅ **API REST completa** con FastAPI
- ✅ **Base de datos PostgreSQL** para persistencia
- ✅ **Webhooks** para notificar pagos confirmados
- ✅ **Datos de prueba** pre-cargados con escenarios realistas
- ✅ **Documentación OpenAPI** automática
- ✅ **Docker Compose** para fácil despliegue
- ✅ **Tests automatizados** con pytest

## 🏗️ Estructura del Proyecto

```
erp_mock/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI (endpoints)
│   ├── database.py          # Conexión PostgreSQL async
│   ├── models.py            # Modelos SQLAlchemy
│   ├── schemas.py           # Schemas Pydantic v2
│   ├── crud.py              # Operaciones de BD
│   ├── webhooks.py          # Cliente para webhooks
│   └── config.py            # Configuración (Settings)
├── scripts/
│   ├── seed.py              # Poblar datos de prueba
│   └── reset.py             # Limpiar BD
├── tests/
│   ├── conftest.py          # Configuración pytest
│   └── test_api.py          # Tests de la API
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pytest.ini
└── README.md
```

## 🚀 Inicio Rápido

### 1. Levantar los servicios

```bash
cd erp_mock
docker-compose up -d
```

### 2. Verificar que está corriendo

```bash
# Health check
curl http://localhost:8001/health

# Ver logs
docker-compose logs -f api
```

### 3. Cargar datos de prueba

```bash
docker-compose exec api python scripts/seed.py
```

### 4. Explorar la API

Abrir en el navegador:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## 📡 Endpoints API

### Health Check

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Estado del servicio |

### Alumnos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/alumnos/{alumno_id}` | Datos del alumno |
| GET | `/api/v1/alumnos/{alumno_id}/cuotas` | Cuotas del alumno (filtrable por estado) |

### Responsables

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/responsables/by-whatsapp/{whatsapp}` | Buscar por WhatsApp |

### Cuotas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/cuotas/{cuota_id}` | Detalle de cuota |
| GET | `/api/v1/cuotas` | Listar con filtros |

### Pagos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/pagos/confirmar` | Confirmar pago |

## 📊 Datos de Prueba

El script `seed.py` genera:

### Responsables (5)
| ID | Nombre | WhatsApp | Hijos |
|----|--------|----------|-------|
| R001 | María González | +5491112345001 | Martín (4to A) |
| R002 | Juan Pérez | +5491112345002 | Sofía (3ro B) |
| R003 | Ana Rodríguez | +5491112345003 | Lucas (5to A) |
| R004 | Carlos López | +5491112345004 | Valentina (2do C), Tomás (4to B) |
| R005 | Laura Martínez | +5491112345005 | Emma (3ro A) |

### Alumnos (6)
- Cada uno con 10 cuotas del Plan Primaria 2026

### Plan de Pago
- **Plan Primaria 2026**: 10 cuotas de $50.000 c/u

### Escenario Especial 🚨
- **Emma Martínez (A006)**: Cuotas 1 y 2 **VENCIDAS** sin pagar
- **Resto**: Cuotas 1 y 2 **PAGADAS**

## 🔔 Webhooks

Cuando se confirma un pago, se envía webhook a:

```
POST {GESTOR_WS_URL}/webhook/erp/pago-confirmado
```

**Payload:**
```json
{
  "tipo": "pago_confirmado",
  "timestamp": "2026-01-09T10:30:00Z",
  "datos": {
    "cuota_id": "C-A001-03",
    "alumno_id": "A001",
    "monto": 50000,
    "fecha_pago": "2026-01-09T10:30:00Z"
  }
}
```

**Características:**
- Retry automático (3 intentos)
- Backoff exponencial
- Envío en background (no bloquea respuesta)

## 🧪 Tests

```bash
# Ejecutar todos los tests
docker-compose exec api pytest

# Con verbose
docker-compose exec api pytest -v

# Test específico
docker-compose exec api pytest tests/test_api.py::test_health
```

## 🛠️ Comandos Útiles

```bash
# Levantar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f api
docker-compose logs -f postgres

# Poblar datos
docker-compose exec api python scripts/seed.py

# Resetear BD (mantiene estructura)
docker-compose exec api python scripts/reset.py --force

# Resetear BD (elimina tablas)
docker-compose exec api python scripts/reset.py --force --drop

# Ejecutar tests
docker-compose exec api pytest

# Shell en el contenedor
docker-compose exec api bash

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v
```

## ⚙️ Configuración

Variables de entorno (en `docker-compose.yml` o `.env`):

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_URL` | URL de PostgreSQL | `postgresql+asyncpg://erp_user:erp_pass@postgres:5432/erp_mock` |
| `GESTOR_WS_URL` | URL del servicio Gestor WS | `http://host.docker.internal:8000` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `WEBHOOK_MAX_RETRIES` | Reintentos webhook | `3` |
| `WEBHOOK_BASE_DELAY` | Delay base (segundos) | `1.0` |

## 📝 Ejemplos de Uso

### Buscar responsable por WhatsApp

```bash
curl http://localhost:8001/api/v1/responsables/by-whatsapp/+5491112345001
```

**Respuesta:**
```json
{
  "id": "R001",
  "nombre": "María",
  "apellido": "González",
  "whatsapp": "+5491112345001",
  "email": "maria.gonzalez@email.com",
  "tipo": "madre",
  "alumnos": [
    {
      "id": "A001",
      "nombre": "Martín",
      "apellido": "González",
      "grado": "4to A",
      "activo": true
    }
  ]
}
```

### Obtener cuotas pendientes de un alumno

```bash
curl "http://localhost:8001/api/v1/alumnos/A001/cuotas?estado=pendiente"
```

### Confirmar un pago

```bash
curl -X POST http://localhost:8001/api/v1/pagos/confirmar \
  -H "Content-Type: application/json" \
  -d '{
    "cuota_id": "C-A001-03",
    "monto": 50000,
    "metodo_pago": "transferencia",
    "referencia": "REF-12345"
  }'
```

## 🔧 Troubleshooting

### Error de conexión a PostgreSQL

```bash
# Verificar que postgres está corriendo
docker-compose ps

# Ver logs de postgres
docker-compose logs postgres

# Reiniciar postgres
docker-compose restart postgres
```

### API no responde

```bash
# Verificar estado
docker-compose ps

# Ver logs de la API
docker-compose logs api

# Reiniciar API
docker-compose restart api
```

### Datos no aparecen

```bash
# Verificar que se ejecutó el seed
docker-compose exec api python scripts/seed.py

# Verificar datos en la BD
docker-compose exec postgres psql -U erp_user -d erp_mock -c "SELECT * FROM erp_responsables;"
```

## 📄 Licencia

MIT License


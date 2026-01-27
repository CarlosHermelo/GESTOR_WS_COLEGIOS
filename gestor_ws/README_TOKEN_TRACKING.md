# Token Tracking - Guía de Uso

## 📍 Dónde se guardan los logs

Los logs de token usage se guardan en:

1. **Consola (stdout)**: Se muestran en tiempo real cuando ejecutás el agente
2. **Archivo general**: `logs/gestor_ws.log` - Todos los logs de la aplicación
3. **Archivo específico**: `logs/token_usage.log` - Solo logs de token usage (JSON estructurado)

## 🔍 Cómo consultar los logs

### Opción 1: Ver en consola (tiempo real)

Cuando ejecutás el agente, los logs aparecen en la consola:

```powershell
# Ejecutar el agente
python -m app.agents.test_agente

# Los logs aparecen en tiempo real, busca líneas con "TOKEN_USAGE"
```

### Opción 2: Consultar archivo de logs

```powershell
# Ver todos los logs de tokens
Get-Content logs/token_usage.log

# Ver últimas 20 líneas
Get-Content logs/token_usage.log -Tail 20

# Filtrar solo logs JSON
Get-Content logs/token_usage.log | Select-String "TOKEN_USAGE"
```

### Opción 3: Usar script de consulta

```powershell
# Ver últimos 10 registros
python scripts/consultar_logs_tokens.py

# Filtrar por WhatsApp
python scripts/consultar_logs_tokens.py --whatsapp "+5491112345001"

# Filtrar por query_id
python scripts/consultar_logs_tokens.py --query-id "abc-123-def"

# Ver más registros
python scripts/consultar_logs_tokens.py --limit 50
```

## 📊 Formato de los logs

### Log JSON (estructurado)

Cada consulta genera un log JSON con este formato:

```json
{
  "event": "token_usage_summary",
  "query_id": "abc-123-def",
  "whatsapp": "+5491112345001",
  "mensaje": "Cuánto debo...",
  "start_time": "2026-01-20T15:30:00",
  "end_time": "2026-01-20T15:30:05",
  "duration_seconds": 5.2,
  "provider": "google",
  "model": "gemini-2.0-flash-exp",
  "inference_count": 3,
  "inferences": [
    {
      "node_name": "manager",
      "inference_type": "planning",
      "prompt_tokens": 350,
      "completion_tokens": 100,
      "total_tokens": 450,
      "timestamp": "2026-01-20T15:30:01"
    },
    {
      "node_name": "financiero_planificar",
      "inference_type": "specialist",
      "prompt_tokens": 400,
      "completion_tokens": 100,
      "total_tokens": 500,
      "timestamp": "2026-01-20T15:30:02"
    },
    {
      "node_name": "synthesizer",
      "inference_type": "synthesis",
      "prompt_tokens": 250,
      "completion_tokens": 50,
      "total_tokens": 300,
      "timestamp": "2026-01-20T15:30:04"
    }
  ],
  "totals": {
    "prompt_tokens": 1000,
    "completion_tokens": 250,
    "total_tokens": 1250
  }
}
```

### Log legible (humano)

También se genera un log legible con formato:

```
============================================================
TOKEN USAGE SUMMARY - Query ID: abc-123-def
============================================================
WhatsApp: +5491112345001
Mensaje: Cuánto debo...
Provider: google
Model: gemini-2.0-flash-exp
Inferencias: 3

Detalle por inferencia:
  [1] manager (planning): 450 tokens (prompt: 350, completion: 100)
  [2] financiero_planificar (specialist): 500 tokens (prompt: 400, completion: 100)
  [3] synthesizer (synthesis): 300 tokens (prompt: 250, completion: 50)

TOTALES:
  Prompt tokens: 1,000
  Completion tokens: 250
  Total tokens: 1,250
============================================================
```

## 🔧 Configuración

### Activar/Desactivar tracking

El tracking está activo por defecto. Para desactivarlo:

```python
from app.services.token_tracker import token_tracker

# Desactivar
token_tracker.disable()

# Activar
token_tracker.enable()
```

### Cambiar nivel de log

En `.env`:

```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## 📈 Análisis de logs

### Calcular total de tokens por día

```powershell
# Extraer totales de tokens del log JSON
Get-Content logs/token_usage.log | 
    Select-String "TOKEN_USAGE" | 
    ForEach-Object { 
        $json = ($_ -split '\{', 2)[1] | ConvertFrom-Json
        $json.totals.total_tokens 
    } | 
    Measure-Object -Sum
```

### Ver consultas más costosas

```powershell
# Ordenar por total_tokens descendente
python scripts/consultar_logs_tokens.py --limit 20 | 
    Sort-Object -Property "totals.total_tokens" -Descending
```

## 🗄️ Persistencia futura en BD

El modelo `TokenUsage` está preparado para migración futura. Cuando se active:

1. Se creará la tabla `token_usage` en PostgreSQL
2. Los logs se guardarán automáticamente en BD
3. Podrás consultar con SQL:

```sql
-- Total de tokens por día
SELECT 
    DATE(created_at) as fecha,
    SUM(total_tokens) as total_tokens
FROM token_usage
GROUP BY DATE(created_at)
ORDER BY fecha DESC;

-- Consultas más costosas
SELECT 
    query_id,
    whatsapp,
    mensaje,
    total_tokens,
    inference_count
FROM token_usage
ORDER BY total_tokens DESC
LIMIT 10;
```

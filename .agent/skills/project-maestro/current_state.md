# Estado Actual del Proyecto GESTOR_WS (Global Memory)

## Última Sesión
- **Fecha**: 2026-01-30 00:54
- **Actividad**: Gestión de tareas en el sandbox del multiagente, fix de logs y configuración de LLM (OpenAI).

## Completados (Hoy)
- [x] Gestión de Tareas: Agregada tarea "Crear el sandbox del multiagente" a `reminders.md`.
- [x] Fix Log Analysis: Corregido bug en `analizar_logs.py` (fechas y lectura de logs recientes).
- [x] Configuración LLM: Estabilización con OpenAI como provider principal.
- [x] Fix del Code Planner: Arquitectura pura (sin fallback innecesario).
- [x] Sincronización de Logging: Consola y archivos unificados en `app/logging_config.py`.
- [x] Project Maestro Root: Centralizada y tradudida al castellano.
- [x] Startup Check: Mejorado con lógica de diagnóstico para MCP (Puerto 8003).

## Pendientes
- [ ] **Multiagente**: Crear el sandbox del multiagente (tarea en reminders).
- [ ] **Modelos LLM**: Averiguar disponibilidad de `gpt-5-nano` y `Gemini-3`.
- [ ] **GESTOR_WS Tests**: Reparar imports de agentes en carpeta `tests/`.

## Módulos Activos (Infraestructura y Agentes)
- **Code Planner**: ✅ Activo y Funcionando (Arquitectura pura)
- **Project Maestro**: ✅ Activo (Root Level)
- **Servicios MCP**: ✅ Activo (Puerto 8003)

## Arquitectura del Code Planner (FUNCIONANDO)
```
agente_autonomo.py → CodePlannerAgent (code_planner.py)
                          │
                          ├── PLANNER: Genera código Python
                          ├── EXECUTOR: Ejecuta código con MCP tools
                          ├── REFLECTOR: Valida si responde a la consulta
                          └── RESPONDER: Genera respuesta final
```

## Archivos Clave (No Modificar sin Backup)
- `gestor_ws/app/agents/agente_autonomo.py` - Wrapper simple
- `gestor_ws/app/agents/code_planner.py` - Lógica del Code Planner con logs
- `gestor_ws/app/agents/states.py` - Solo CodePlannerState
- `gestor_ws/app/agents/test_agente.py` - Script de prueba

## Infraestructura Global
- **Gestor WS (API)**: Puerto 8000
- **ERP Mock**: Puerto 8001
- **Knowledge Graph**: Puerto 8002
- **MCP Tools**: Puerto 8003 (⚠️ **CRÍTICO PARA CODE PLANNER**)
- **Postgres**: Puertos 5432, 5433
- **Neo4j**: Puertos 7474, 7687

> [!IMPORTANT]
> Para los tests del Code Planner, **solo es obligatorio tener el servidor de MCP Tools (8003) activo**. No se requiere Docker si se corre en modo MOCK local.

## Logs del Sistema

**Ubicaciones de archivos (dentro de `gestor_ws/`):**
- `gestor_ws/logs/gestor_ws.log` - Log principal (flujo completo, errores, traces)
- `gestor_ws/logs/token_usage.log` - Registro JSON de consumo de tokens y costos

**Herramientas de visualización:**
- **`gestor_ws/analizar_logs.py`** - Script recomendado para leer el flujo de forma amigable.

**Comandos útiles (PowerShell):**
```powershell
cd gestor_ws

# Ver última consulta analizada (con todos los pasos)
python analizar_logs.py 1 all

# Ver últimas 3 consultas (resumen)
python analizar_logs.py 3

# Seguir el log principal en tiempo real
Get-Content logs/gestor_ws.log -Wait

# Filtrar solo pasos técnicos del Code Planner
Select-String -Path logs/gestor_ws.log -Pattern "\[PLANNER\]|\[EXECUTOR\]|\[REFLECTOR\]|\[RESPONDER\]"
```

## Estado
- **Modo Actual**: MOCK (Configurado en gestor_ws)
- **Último Test**: ✅ Exitoso (2026-01-27 16:14)

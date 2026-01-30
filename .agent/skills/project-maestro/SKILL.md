---
name: project-maestro
description: El Cerebro Operativo del proyecto GESTOR_WS. Gestiona el estado global, verifica la infraestructura de todos los módulos y corre diagnósticos centralizados.
---

# Project Maestro - El Cerebro Operativo Global

Esta skill es responsable de la orquestación y el control del estado de **todo el ecosistema** `GESTOR_WS` (Backend, ERP Mock, Knowledge Graph, MCP Tools).

## Instrucciones Principales

1.  **Antes de cada sesión**:
    -   Lee el archivo `current_state.md` para entender el contexto global.
    -   Ejecuta `scripts/startup_check.py` para verificar que la infraestructura completa (Docker, Puertos, BDs) esté lista.

2.  **Reporte de Estado**:
    -   Cuando el usuario pregunte "¿En qué estamos?" o similar:
        -   Analiza `current_state.md`.
        -   Corre `scripts/startup_check.py`.
        -   Genera un reporte consolidado con la salud del sistema y las tareas pendientes.

3.  **Gestión de Entorno**:
    -   Usa `scripts/switch_env.py` para cambiar entre modo MOCK y PROD (afectando la configuración central).

5.  **Diagnóstico**:
    -   Si algo falla, ejecuta `scripts/run_diagnostic.py` para correr tests en los módulos afectados.
    -   Usa **`gestor_ws/analizar_logs.py`** para visualizar el flujo completo de las consultas del agente (Planner, Executor, Reflector, Responder) de forma legible.

6.  **Multi-Agente (Code Planner)**:
    -   **IMPORTANTE**: Para testear el Code Planner, el requisito **mínimo** e indispensable es que el servidor de **MCP Tools (Puerto 8003)** esté activo.
    -   **Cómo levantarlo localmente**:
        -   Directorio: `mcp_tools/`
        -   Comando: `python run_local.py` (esto fija `MOCK_MODE=true` por código para seguridad).
    -   **Origen de los datos (MOCK vs REAL)**:
        -   El origen de los datos NO depende solo del agente, sino de la configuración del servidor MCP.
        -   **Si MOCK_MODE=True** (en `mcp_tools/.env` o `run_local.py`): Las herramientas del MCP devolverán datos de prueba (Mocks) sin consultar base de datos ni ERP real.
        -   **Si MOCK_MODE=False**: Las herramientas del MCP intentarán conectar con los servicios reales (ERP en 8001, KG en 8002, etc.).
        -   **Validación**: Antes de testear, confirma el valor de `MOCK_MODE` en el `.env` de la carpeta `mcp_tools/`. Recuerda que `gestor_ws` también tiene su propio `.env` para la lógica del agente, pero quien "toca" los datos es el MCP.
    -   No es obligatorio que Docker esté corriendo si estás probando en modo MOCK local.
    -   Usa `scripts/startup_check.py` para visualizar rápidamente si el puerto 8003 está listo y qué modo de datos está activo.

7.  **Sistema de Memoria Triple (NUEVO)**:
    -   **Leyes del Proyecto (`technical_norms.md`)**: Antes de generar código o proponer arquitecturas, **DEBES** consultar este archivo. Si existe una norma relevante, menciónala y aplícala.
    -   **Base de Conocimiento (`knowledge_base.md`)**: Registra conceptos técnicos aprendidos para evitar redundancia en explicaciones futuras.
    -   **Recordatorios (`reminders.md`)**: Gestiona tareas y notas personales.
    -   **Consultas**: Cuando el usuario pregunte "¿En qué estamos?", además del estado técnico, resume los 3 recordatorios más urgentes de `reminders.md`.

6.  **Protocolo de Cierre de Sesión (OBLIGATORIO)**:
    -   **Disparadores**: "me voy", "ya está por hoy", "voy a dejar", "cerrar sesión".
    -   **Paso 1: Resumen**: Recuento de archivos, lógica y tests globalmente.
    -   **Paso 2: Entrevista**: Preguntar:
        -   "¿Qué tareas quedaron pendientes o a medio camino?"
        -   "¿Hubo algún cambio manual en la infraestructura?"
    -   **Paso 3: Memoria**: Actualizar `current_state.md` y, si es relevante, agregar notas a la Memoria Triple usando `scripts/manage_memory.py`.
    -   **Paso 4: Bye**: Confirmar actualización y despedida.

## Comandos de Voz (Triggers e Intenciones)
El usuario activa esta skill a través de ti con estas frases:
- **Estado**: "¿En qué estamos?", "Dame un resumen", "Status report". (Responde con salud técnica + 3 recordatorios de `reminders.md`).
- **Entorno**: "Cambia a modo PROD", "Activa los mocks", "Switch to MOCK".
- **Salud**: "Corre un diagnóstico", "Algo falló, revisa los logs", "Check system health".

### Sistema de Memoria Dinámica (Comandos Implícitos)
- **Categoría 'Anotar'**:
    - *Frases*: "acordate de...", "anotá que...", "no me quiero olvidar de...".
    - *Acción*: Clasifica automáticamente en `reminders`, `knowledge_base` o `technical_norms` según el contenido y usa `scripts/manage_memory.py add`.
- **Categoría 'Norma'**:
    - *Frases*: "a partir de ahora...", "siempre hay que...", "regla técnica:".
    - *Acción*: Guarda el contenido directamente en `technical_norms.md`.

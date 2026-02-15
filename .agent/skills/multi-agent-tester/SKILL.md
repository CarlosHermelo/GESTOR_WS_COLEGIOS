---
name: multi-agent-tester
description: Skill dedicada a ejecutar pruebas y analizar logs del Code Planner (Multi-Agente).
---

# Multi-Agent Tester

Esta skill centraliza las herramientas necesarias para validar el funcionamiento del **Code Planner** (sistema multi-agente). Permite ejecutar flujos de prueba y analizar la toma de decisiones de los agentes (Planner, Executor, Reflector, Responder).

## Arquitectura del Agente
El Code Planner sigue un flujo jerárquico:
1. **Planner**: Genera código Python dinámicamente basado en la consulta y las tools MCP de `localhost:8003`.
2. **Executor**: Ejecuta el código en un entorno seguro.
3. **Reflector**: Evalúa la calidad de la respuesta generada.
4. **Responder**: Genera la respuesta final empática para WhatsApp.

## Comandos de Prueba

#Opción A: Script de Skill (Recomendado)
```powershell
cd GESTOR_WS
python .agent/skills/multi-agent-tester/scripts/run_agent_test.py --interactivo
```

#Opción B: Módulo Agente (Directo)
```powershell
cd gestor_ws
python -m tests.test_agente --interactivo
```

#Opción C: Script Integrado (Verificación de Entorno + Test) [MEJORADO]
Este script verifica salud del MCP, el modo (Mock/Real) y la configuración de LLM antes de correr el test. Ahora permite limitar la cantidad de pruebas y usar modos de visualización.
```powershell
# 1. Ejecución estándar (Verborrágica) - Ejecutar todos
.\xx\Scripts\python.exe gestor_ws\tests\test_agenteII.py

# 2. Ejecutar solo los primeros N casos
.\xx\Scripts\python.exe gestor_ws\tests\test_agenteII.py 3

# 3. Modo Resumen (--resume): Muestra solo métricas de tiempos y tokens
.\xx\Scripts\python.exe gestor_ws\tests\test_agenteII.py --resume
.\xx\Scripts\python.exe gestor_ws\tests\test_agenteII.py 5 --resume

# 4. Modo QA (--qa): Muestra solo Pregunta y Respuesta (limpio)
.\xx\Scripts\python.exe gestor_ws\tests\test_agenteII.py --qa
.\xx\Scripts\python.exe gestor_ws\tests\test_agenteII.py 1 --qa

# 5. Combinado (QA + Resumen)
.\xx\Scripts\python.exe gestor_ws\tests\test_agenteII.py 3 --qa --resume
```

#Opción D: Prueba de Sistema Completo (3 Terminales - Recomendado para Debugging)
Para probar la integración real entre Agente, MCP y ERP Mock, se requieren 3 terminales activas:

**Terminal 1: ERP Mock (Puerto 8001)**
*Limpia la variable DATABASE_URL para usar SQLite local y levanta el servicio.*
```cmd
set DATABASE_URL= && python -m uvicorn app.main:app --port 8001 --reload
```
*(O en PowerShell: `$env:DATABASE_URL=""; ...`)*

**Terminal 2: MCP Tools (Puerto 8003)**
*Levanta el servidor de herramientas.*
```powershell
cd mcp_tools
python run_local.py
```

**Terminal 3: Agente Interactivo**
*Ejecuta el agente para realizar consultas.*
```powershell
python -m tests.test_agente --interactivo
```

#Opción E: Diagnóstico de ERP (Directo de Skill) [NUEVO]
Permite verificar qué datos está viendo el sistema (RAW ERP) para un número específico.
```powershell
python .agent/skills/multi-agent-tester/scripts/consultar_erp_endpoint.py +5491199999999
```

#Opción F: Diagnóstico de Tool MCP (Directo de Skill) [NUEVO]
Permite verificar la respuesta procesada por la tool del MCP (incluye transformación y lógica de negocio).
```powershell
python .agent/skills/multi-agent-tester/scripts/consultar_mcp_tool.py +5491199999999
```

## Análisis de Logs

El script `analizar_logs.py` (en `gestor_ws/tests`) procesa los archivos `gestor_ws.log` y `token_usage.log` para mostrar el flujo de los agentes.

### Parámetros Disponibles

| Comando | Descripción |
|---------|-------------|
| `python analizar_logs.py` | Muestra el reporte detallado de la **última consulta**. |
| `python analizar_logs.py [N]` | Muestra el reporte de las **últimas [N] consultas**. Ej: `python analizar_logs.py 3` |
| `python analizar_logs.py [N] all` | Muestra los reportes con **todo el detalle** (código generado y respuestas completas). |
| `python analizar_logs.py compacto` | Modo **compacto**: Pregunta, desglose por nodo (tiempo/tokens) y respuesta en una línea. |
| `python analizar_logs.py resume` | Modo **resumen de una línea** por cada consulta (ID, tiempo, tokens, pregunta). |
| `python analizar_logs.py [N] resume` | Tabla de **resumen** de las últimas [N] consultas. Ej: `python analizar_logs.py 10 resume` |

### Ejemplo de Uso
```powershell
cd gestor_ws
# Ver las últimas 5 consultas en formato compacto (ideal para revisión rápida)
python analizar_logs.py 5 compacto

# Ver las últimas 10 consultas en formato tabla
python analizar_logs.py 10 resume
```

## Flujo de Trabajo Completo

### 1. Generación de Datos (Testing)
**Script:** `gestor_ws/tests/test_agenteII.py`
- **Fuente de Datos:** `gestor_ws/tests/test_agente/test_data_larga.txt` (Archivo JSON con los casos de prueba).
- **Soporte Dinámico:** Cada caso de prueba puede incluir un campo `"celular"` para simular diferentes usuarios.
- **Limitación de Casos:** Se puede pasar un número como argumento para ejecutar solo los primeros N registros.
- Verifica automáticamente el entorno (MCP activo, modo Mock/Real, credenciales LLM).
- Genera información fresca en los archivos de log.
- **Comando:** `.\xx\Scripts\python.exe gestor_ws\tests\test_agenteII.py [N]`

### 2. Análisis de Datos (Logs)
**Script:** `gestor_ws/tests/analizar_logs.py`
- Lee los logs generados y presenta reportes legibles.
- **Parametros:**
  - `[N]`: Cantidad de consultas a mostrar.
  - `compacto`: Vista rápida (Pregunta + Tiempo/Tokens por nodo + Respuesta en 1 línea).
  - `resume`: Tabla resumen.
  - `all`: Detalle técnico completo (incluye código generado).

## Gestión de Prompts (NUEVO)

Ahora es posible visualizar y editar las instrucciones de los agentes sin modificar el código fuente. Esto permite ajustar la personalidad o las reglas del sistema de forma dinámica.

### Herramienta Visual
- **Editor Centralizado**: [prompt_editor.html](file:///c:/Users/u14527001/Downloads/GESTOR_WS/prompt_editor.html)
- **Archivo de Configuración**: `gestor_ws/app/agents/prompts.json`

### Procedimiento de Ajuste
1.  **Visualizar**: Abre el `prompt_editor.html` en tu navegador.
2.  **Editar**: Modifica el prompt deseado (puedes usar el botón **"Ampliar"** para pantalla completa).
3.  **Exportar**: Usa el botón **"Exportar JSON"** para descargar la nueva configuración.
4.  **Aplicar**: Pídele al agente que actualice el archivo `/gestor_ws/app/agents/prompts.json` con el contenido del JSON exportado.

### 3. Ubicación de Información
Los logs se buscan inteligentemente en varias carpetas. El script selecciona automáticamente el archivo **modificado más recientemente**.
- **Log Principal:** `gestor_ws/logs/gestor_ws.log` (o en `logs/` dependiendo de desde dónde se corra).
- **Log de Tokens:** `gestor_ws/logs/token_usage.log` (contiene métricas detalladas de consumo por nodo).

## Requisitos
- El servidor de **MCP Tools** debe estar activo en el puerto **8003**.
- Configuración de `LLM_MODEL` en `.env` (Recomendado: `gpt-4o-mini`).

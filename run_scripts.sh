#!/bin/bash

# Script de automatización para GESTOR_WS
echo "--- Iniciando Ejecución de Scripts ---"

# 1. Activar el entorno virtual (usando la ruta de Windows desde Bash)
# Nota: En Bash sobre Windows, usamos 'source' con la ruta del script de activación
if [ -d "xx" ]; then
    echo "Activando entorno virtual..."
    source xx/Scripts/activate
else
    echo "Error: No se encontró el directorio del entorno virtual 'xx'"
    exit 1
fi

# 2. Ejecutar un script de prueba para demostrar el funcionamiento
echo "Ejecutando test_agente.py..."
python -m gestor_ws.app.agents.test_agente

echo "--- Proceso Finalizado ---"

# Portal de Testing (Informativo)

Este skill centraliza la descripción de las pruebas disponibles en el proyecto, proporcionando una guía para el usuario sobre cómo y cuándo ejecutarlas.

## Operatoria

1. **Si el usuario quiere saber qué hay de testing o pide "listar los testing"**:
   - Consulta `resources/testing_inventory.json`.
   - Muestra una tabla con: **Módulo**, **Descripción**, **Tipo** y **Acción**.
   - Usa el comando: `python scripts/testing_viewer.py list`

2. **Si el usuario pide "mostrar un testing [ID]"**:
   - Recupera el detalle completo del ID solicitado desde el JSON.
   - Muestra: Módulo, Tipo, Descripción, **Precondiciones**, **Acción** y **Postcondiciones/Comentarios**.
   - Usa el comando: `python scripts/testing_viewer.py show [ID]`

3. **Si el usuario quiere registrar un nuevo test ("Agregar un testing")**:
   - Pide al usuario los datos necesarios: ID, Módulo, Tipo, Descripción, Precondiciones, Acción y Postcondiciones.
   - Crea un objeto JSON con esta información.
   - Usa el comando: `python scripts/testing_viewer.py add '[JSON_STRING]'`
   - Informa al usuario que el test ha sido registrado exitosamente.

## Regla de Oro
Este skill es puramente **informativo** en su salida, pero permite el **mantenimiento** de su propia base de conocimiento. No ejecuta el testing automáticamente. Su objetivo es informar al usuario sobre los requisitos (precondiciones) y el comando exacto (acción) para que él o el agente lo ejecuten de forma consciente.

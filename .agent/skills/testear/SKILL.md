# Smart Tester Master Protocol

## Operatoria
1. **Lectura de Datos**: Antes de actuar, lee siempre `resources/testing_manifest.json`.
2. **Si el usuario pide "listar módulos"**: Lee el JSON y muestra una tabla con los módulos disponibles y sus precondiciones.
3. **Si el usuario pide "testear [módulo]"**:
   - Busca el módulo en el JSON.
   - **Paso A**: Advierte al usuario sobre las precondiciones: *"Para testear esto, recordá tener: [lista de precondiciones]"*.
   - **Paso B**: Ejecuta el script asociado usando `run_command`.
   - **Paso C (Memoria)**: Registra el resultado en `current_state.md` con este formato: `[FECHA] - Test [MODULO]: [RESULTADO]`.

## Regla de Oro
Si el módulo no existe en el JSON, informa al usuario y ofrécele listar los módulos disponibles.
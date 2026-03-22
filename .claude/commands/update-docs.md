Actualiza la documentacion del proyecto Mimir para reflejar el estado actual.

## Proceso

1. **Lee el estado actual**:
   - Version de `package.json` y `src-tauri/tauri.conf.json`
   - Tablas SQLite: `cd daemon && .venv/bin/python -c "import sqlite3; conn = sqlite3.connect('/tmp/mimir-check.db'); ..."`  (o lee db.py para las migraciones)
   - Endpoints del server: busca `@app.` en `daemon/mimir_daemon/api_server.py`
   - Componentes Vue: lista `src/components/**/*.vue`
   - Composables: lista `src/composables/*.ts`
   - Stores Pinia: lista `src/stores/*.ts`
   - Numero de tests: `cd daemon && .venv/bin/pytest tests/ -q 2>&1 | tail -1`
   - Agentes y commands: lista `.claude/agents/` y `.claude/commands/`

2. **Compara con la documentacion actual** y actualiza lo que haya cambiado:
   - `CLAUDE.md` — version, comandos, arquitectura general
   - `.claude/context/architecture.md` — tablas, endpoints, integraciones, procesos
   - `.claude/context/conventions.md` — componentes, composables, stores, patrones
   - `PROGRESS.md` — estado de features

3. **Presenta un diff** de lo que cambio en cada archivo

## Reglas

- Solo actualizar lo que realmente cambio — no reescribir todo
- Mantener el formato y estilo existente de cada archivo
- No inventar — solo documentar lo que existe en el codigo
- La version siempre viene de package.json (fuente de verdad)
- Los textos de documentacion en espanol sin tildes (como el resto de .md del proyecto)

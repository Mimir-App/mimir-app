# CLAUDE.md — Mimir

## Descripcion
Mimir es un asistente inteligente de imputacion de horas. Captura automaticamente la actividad del empleado, sugiere descripciones con IA, y permite imputar horas a Odoo.

## Stack
- **Frontend**: Tauri 2 + Vue 3 + TypeScript + Vite
- **Backend desktop**: Rust (Tauri commands)
- **Daemon**: Python 3.10+ (asyncio + FastAPI + uvicorn)
- **Base de datos**: SQLite (daemon) + JSON config (Tauri)

## Comandos

```bash
# Frontend + Tauri
npm install
npm run tauri dev    # Desarrollo con hot reload

# Daemon Python
cd daemon
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m mimir_daemon      # Arranca daemon
pytest tests/ -v            # Tests del daemon

# Verificaciones
npx vue-tsc --noEmit        # TypeScript check
cd src-tauri && cargo check  # Rust check
```

## Arquitectura
- `src/` — Frontend Vue 3 + TypeScript
- `src-tauri/` — Backend Rust (Tauri 2)
- `daemon/` — Daemon Python (proceso separado)
- Comunicacion daemon <-> Tauri: HTTP local (localhost:9477)

## Progreso
Ver `PROGRESS.md` para el estado detallado de cada fase.

@.claude/context/architecture.md
@.claude/context/conventions.md
@.claude/context/themes.md

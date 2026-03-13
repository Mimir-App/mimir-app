# CLAUDE.md — Mimir

## Descripción
Mimir es un asistente inteligente de imputación de horas. Captura automáticamente la actividad del empleado, sugiere descripciones con IA, y permite imputar horas a Odoo.

## Stack
- **Frontend**: Tauri 2 + Vue 3 + TypeScript + Vite
- **Backend desktop**: Rust (Tauri commands)
- **Daemon**: Python 3.10+ (asyncio + FastAPI + uvicorn)
- **Base de datos**: SQLite (daemon) + JSON config (Tauri)

## Comandos

```bash
# Frontend + Tauri
cd mimir
npm install
npm run tauri dev    # Desarrollo con hot reload

# Daemon Python
cd mimir/daemon
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m mimir_daemon      # Arranca daemon
pytest tests/               # Tests del daemon
```

## Arquitectura
- `src/` — Frontend Vue 3 + TypeScript
- `src-tauri/` — Backend Rust (Tauri 2)
- `daemon/` — Daemon Python (proceso separado)
- Comunicación daemon ↔ Tauri: HTTP local (localhost:9477)

## Convenciones
- Docstrings en español
- Type hints en todo Python
- TypeScript strict mode
- Errores nunca crashean: se muestran en UI
- JSON con `ensure_ascii=False`, UTF-8

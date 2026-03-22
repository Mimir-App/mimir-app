# CLAUDE.md — Mimir

## Descripcion
Mimir es un asistente inteligente de imputacion de horas. Captura automaticamente la actividad del empleado mediante senales (cada 30s), construye bloques con un algoritmo determinista, sugiere descripciones con IA, y permite imputar horas a Odoo.

**Version actual: v0.4.2**

## Stack
- **Frontend**: Tauri 2 + Vue 3 + TypeScript + Vite
- **Backend desktop**: Rust (Tauri commands)
- **Capture daemon**: Python 3.10+ (asyncio + poller + tray), puerto 9476, systemd service
- **Server daemon**: Python 3.10+ (FastAPI + uvicorn), puerto 9477, child process de Tauri
- **Base de datos**: SQLite compartida (WAL) + JSON config (Tauri)

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
python -m mimir_daemon      # Arranca daemon (capture + server)
pytest tests/ -v            # Tests del daemon (~147 tests)

# Build
bash scripts/build.sh capture   # Solo capture
bash scripts/build.sh server    # Solo server
bash scripts/build.sh daemon    # Ambos + instalador
bash scripts/build.sh app       # Solo app Tauri
bash scripts/build.sh deb       # Paquetes .deb unificados
bash scripts/build.sh           # Todo

# Verificaciones
npx vue-tsc --noEmit        # TypeScript check
cd src-tauri && cargo check  # Rust check
```

## Slash Commands (Claude Code)

| Comando | Descripcion |
|---|---|
| `/test` | Suite completa: pytest + vue-tsc + cargo check |
| `/check` | Verificacion rapida: vue-tsc + cargo check (sin tests) |
| `/build [target]` | Ejecuta scripts/build.sh |
| `/status` | Estado del proyecto: version, git, tests |
| `/learn` | Extrae patrones de la sesion y los guarda |
| `/brainstorm` | Explora una idea: contexto → preguntas → diseno |
| `/update-docs` | Actualiza CLAUDE.md, architecture.md, conventions.md |
| `/review-code [fase]` | Revisa codigo contra el plan |
| `/implement-phase N` | Implementa una fase del plan |
| `/verify-phase N` | Verifica que una fase esta completa |

## Arquitectura
- `src/` — Frontend Vue 3 + TypeScript
- `src-tauri/` — Backend Rust (Tauri 2)
- `daemon/` — Daemon Python (dos procesos: capture y server)
- mimir-capture: puerto 9476, systemd user service, poller + signals + tray + health
- mimir-server: puerto 9477, lanzado por Tauri como child process, FastAPI completo
- SQLite compartida entre ambos procesos (WAL mode)
- Tablas: blocks, signals, block_signals, ai_cache, source_tokens, preferences_cache, item_preferences, notifications, context_mappings

## Progreso
Ver `PROGRESS.md` para el estado detallado de cada fase.

@.claude/context/architecture.md
@.claude/context/conventions.md
@.claude/context/themes.md

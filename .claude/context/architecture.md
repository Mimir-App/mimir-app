## Arquitectura

Seis fases de implementacion — cada una debe dejar el proyecto ejecutable antes de continuar:

**Fase 0 — Scaffold (COMPLETADA)**
- Estructura completa del proyecto: Tauri 2 + Vue 3 + daemon Python
- 6 vistas Vue, 6 stores Pinia, 14 componentes, 3 composables
- Backend Rust con commands, models y daemon HTTP client
- Daemon funcional con poller, block_manager, DB, tray, server

**Fase 1 — Daemon Core (COMPLETADA)**
- `daemon/mimir_daemon/platform/linux.py`: xdotool (llamadas separadas), /proc directo, D-Bus logind
- `daemon/mimir_daemon/context_enricher.py`: cache git, deteccion SSH, alias resolution
- `daemon/mimir_daemon/block_manager.py`: deteccion cambio contexto (app/proyecto), crash recovery, checkpoints
- `daemon/mimir_daemon/db.py`: CRUD completo, summary, open blocks, preferences cache
- `daemon/mimir_daemon/server.py`: CORS, CRUD blocks, /blocks/summary, mode, stubs Odoo/GitLab

**Fase 2 — Config + Auth + Comunicacion**
- Integrar keyring real en Rust (crate `keyring` en Cargo.toml)
- Conectar frontend Tauri con daemon real via HTTP localhost:9477
- SettingsView funcional end-to-end
- Health check daemon desde Tauri

**Fase 3 — Vista "Revisar Dia" + Imputacion Odoo**
- Conectar `integrations/odoo_v11.py` (XMLRPC) y `odoo_v16.py` (REST) con server.py
- BlockEditor con dropdowns funcionales de proyectos/tareas Odoo
- Flujo completo: captura -> revision -> confirmacion -> envio Odoo

**Fase 4 — Descripciones IA**
- Llamada real a Gemini API (stub heuristico existe)
- Cache por hash de senales
- Lazy loading de descripciones en frontend

**Fase 5 — Vistas GitLab**
- Conectar `sources/gitlab.py` con server.py
- Scoring (TypeScript ya en `src/lib/scoring.ts`)

**Fase 6 — Dashboard + Polish**
- DashboardView conectado a datos reales
- Temas oscuro/claro (branding FactorLibre)
- Health check daemon desde Tauri
- Empaquetado

## Comunicacion entre componentes

```
Frontend (Vue 3 + Tauri)
    |
    | invoke() -> Tauri commands (Rust)
    |                 |
    |                 | HTTP requests
    |                 v
    |         Daemon Python (FastAPI)
    |           localhost:9477
    |                 |
    |      +----------+----------+
    |      |          |          |
    |   Poller    Server    Tray Icon
    |      |
    |   Platform (xdotool/D-Bus)
    |      |
    |   BlockManager -> SQLite
```

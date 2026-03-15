## Arquitectura

Todas las fases completadas (v0.2.0). Refactor capture/server realizado.

### Procesos

**mimir-capture** (puerto 9476)
- Proceso independiente, corre como systemd user service
- Poller (ciclo cada 30s), BlockManager, Context Enricher, Tray Icon
- Platform layer (xdotool + D-Bus logind + /proc)
- Endpoint /health para monitoreo
- Siempre corriendo en background, independiente de la app

**mimir-server** (puerto 9477)
- Lanzado por Tauri como child process al abrir la app
- FastAPI completo: CRUD blocks, sync Odoo, GitLab, IA, config
- Se mata al cerrar la app Tauri

**SQLite compartida**
- Ambos procesos acceden a la misma base de datos
- WAL mode para concurrencia segura entre capture y server

### Fases implementadas

**Fase 0 -- Scaffold (COMPLETADA)**
- Estructura completa del proyecto: Tauri 2 + Vue 3 + daemon Python
- 6 vistas Vue, 6 stores Pinia, 14 componentes, 3 composables
- Backend Rust con commands, models y daemon HTTP client

**Fase 1 -- Daemon Core (COMPLETADA)**
- `daemon/mimir_daemon/platform/linux.py`: xdotool (llamadas separadas), /proc directo, D-Bus logind
- `daemon/mimir_daemon/context_enricher.py`: cache git, deteccion SSH, alias resolution
- `daemon/mimir_daemon/block_manager.py`: deteccion cambio contexto (app/proyecto), crash recovery, checkpoints
- `daemon/mimir_daemon/db.py`: CRUD completo, summary, open blocks, preferences cache
- `daemon/mimir_daemon/server.py`: CORS, CRUD blocks, /blocks/summary, mode, stubs Odoo/GitLab

**Fase 2 -- Config + Auth + Comunicacion (COMPLETADA)**
- Keyring real en Rust (crate `keyring`)
- Frontend Tauri conectado con daemon via HTTP localhost:9477
- SettingsView funcional end-to-end
- Health check daemon desde Tauri

**Fase 3 -- Revisar Dia + Imputacion Odoo (COMPLETADA)**
- `integrations/odoo_v11.py` (XMLRPC) y `odoo_v16.py` (REST) conectados con server.py
- BlockEditor con dropdowns funcionales de proyectos/tareas Odoo
- Flujo completo: captura -> revision -> confirmacion -> envio Odoo
- Fichaje de asistencia conectado a hr.attendance

**Fase 4 -- Descripciones IA (COMPLETADA)**
- Providers Gemini/Claude/OpenAI con patron adaptador
- Cache por hash de senales (SHA-256) en SQLite
- Generacion automatica al cerrar bloque + regeneracion bajo demanda

**Fase 5 -- Vistas GitLab (COMPLETADA)**
- GitLabSource conectado con server.py
- Scoring en frontend (computeIssueScore/computeMRScore)
- IssuesView y MergeRequestsView con polling

**Fase 6 -- Dashboard + Polish + Empaquetado (COMPLETADA)**
- DashboardView con datos reales y widgets arrastrables NxM
- Temas oscuro/claro (branding FactorLibre)
- PyInstaller para daemon, Tauri bundle para app

**v0.2.0 -- Refactor capture/server + UI/UX (COMPLETADA)**
- Separacion en dos procesos (capture 9476, server 9477)
- Componentes UI: CustomSelect, CustomDatePicker, CollapsibleGroup, ViewToolbar, DashboardGrid, StatusBanner, LoadingState, EmptyState, HelpTooltip
- Composables: useFormatting, useSortable, useCollapseAll, usePolling, useColumnWidths, useTargets
- Formatos configurables, zoom, sidebar colapsable, columnas redimensionables
- Objetivos semanales, barras de progreso, filtro por usuario, agrupaciones nuevas

## Comunicacion entre componentes

```
Frontend (Vue 3 + Tauri)
    |
    | invoke() -> Tauri commands (Rust)
    |                 |
    |                 | HTTP requests
    |                 v
    |         mimir-server (FastAPI)
    |           localhost:9477
    |           [child process de Tauri]
    |                 |
    |                 | SQLite compartida (WAL)
    |                 |
    |         mimir-capture
    |           localhost:9476
    |           [systemd user service]
    |                 |
    |      +----------+----------+
    |      |          |          |
    |   Poller    Health    Tray Icon
    |      |
    |   Platform (xdotool/D-Bus)
    |      |
    |   BlockManager -> SQLite
```

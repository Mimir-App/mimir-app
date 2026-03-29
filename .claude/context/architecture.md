## Arquitectura

Version actual: v0.8.0. Multi-source (GitHub + GitLab) + Descubrir + auto-asignacion + context affinity + GitHub OAuth + generacion de bloques bajo demanda + revision de bloques + mapeos TOML + historial de navegador.

### Procesos

**mimir-capture** (puerto 9476)
- Proceso independiente, corre como systemd user service
- Poller (ciclo cada 30s), Context Enricher, Tray Icon
- Solo captura senales — NO genera bloques (generacion bajo demanda)
- Platform layer: X11 (xdotool) + Wayland (GNOME Shell extension D-Bus) + D-Bus logind
- Deteccion automatica de entorno via $XDG_SESSION_TYPE
- Context enricher: baja al proceso hijo mas profundo para detectar git repo en terminales
- System context: idle time (Mutter), audio/reuniones (pactl), workspace
- Endpoint /health y /status (incluye backend activo)

**mimir-server** (puerto 9477)
- Lanzado por Tauri como child process al abrir la app
- FastAPI con routers modulares (routers/blocks, vcs, odoo, google, items, signals, notifications, config_router, context_mappings, github_oauth)
- Google Calendar OAuth2 + consulta de eventos
- GitHub OAuth Device Flow (start + poll)
- NotificationService como background task (asyncio, lifespan)
- Context mappings: CRUD + suggest + aprendizaje al confirmar
- Se mata al cerrar la app Tauri

**SQLite compartida**
- Ambos procesos acceden a la misma base de datos
- WAL mode para concurrencia segura entre capture y server
- Migration registry versionado (schema_version table, 4 migraciones)
- Tablas: blocks, signals, block_signals, ai_cache, source_tokens, preferences_cache, item_preferences, notifications, context_mappings, context_affinity

### Integraciones

| Servicio | Auth | Funcionalidad |
|---|---|---|
| Odoo v11 | XMLRPC + password | Timesheets, proyectos, tareas, fichaje |
| Odoo v16+ | REST + API key | Timesheets, proyectos, tareas, fichaje |
| GitLab | Personal Access Token | Issues, MRs, TODOs, scoring, notas, conflictos, labels |
| GitHub | PAT o OAuth Device Flow | Issues, PRs, search, comments, reviews, files, notifications, labels |
| Google Calendar | OAuth2 | Eventos actuales, eventos por fecha, deteccion reuniones |
| Claude Code CLI | Suscripcion | Generacion y revision de bloques bajo demanda (timesheet-generator + timesheet-reviewer) |
| Gemini/Claude/OpenAI | API key | Descripciones automaticas de bloques |

### Multi-source VCS

- SourceRegistry con adaptadores (GitLabSource, GitHubSource)
- Adaptadores normalizan datos al mismo formato (_source, _type, user_notes_count, label_objects, etc.)
- Endpoints genericos (/gitlab/issues, /gitlab/merge_requests) agregan todas las fuentes
- Endpoints especificos (/github/issues/search, /gitlab/issues/{id}/notes) por fuente
- item_preferences guarda metadatos (source, project_path, iid, title) para recuperar items individualmente
- Deduplicacion por project_path#iid (no por id)

### Dashboard

Sistema de widgets configurable:
- Widget registry (`src/lib/widget-registry.ts`) con 10 tipos registrados
- Cada widget es un componente independiente en `src/components/dashboard/widgets/`
- DashboardGrid soporta drag & drop, resize, add/remove
- Config persistente por widget en `dashboard_widgets` de AppConfig
- Galeria para anadir nuevos widgets + modal de configuracion

### Notificaciones

- NotificationService: definido como background task async (FastAPI lifespan), actualmente stub sin instanciar en produccion
- Tabla `notifications` en SQLite con TTL configurable
- NotificationBell en header con polling 30s + dropdown
- Configurable por tipo de evento en Settings > Notificaciones
- Pendiente: instanciar NotificationService, desktop notifications (tauri-plugin-notification), deteccion real de cambios

### Generacion de bloques bajo demanda

Flujo: usuario pulsa "Generar bloques" en ReviewDay → Tauri recopila datos via `/blocks/generation-data` → invoca `claude --print` con agente timesheet-generator.md → parsea JSON → POST `/blocks/generate`.

**Fuentes de datos:**
- Senales de mimir-capture (actividad desktop cada 30s)
- Actividad VCS: GitLab (`/users/{id}/events`) y GitHub (`/users/{username}/events`)
- Google Calendar: eventos del dia (`/calendars/primary/events`)
- Proyectos y tareas Odoo (filtrados por relevancia)
- Historial de navegador: Chrome/Firefox/Brave/etc. agrupado por dominio (on-demand, configurable)
- Mapeos TOML: `~/.config/mimir/mappings.toml` con reglas admin

**Agentes Claude Code CLI:**
- `.claude/agents/timesheet-generator.md`: genera bloques de imputacion
- `.claude/agents/timesheet-reviewer.md`: revisa bloques generados y detecta problemas
- `~/.config/mimir/timesheet-rules.md`: reglas de matching configurables por usuario
- Modelo: haiku (optimizado para velocidad, ~2 min)
- Sin tool calls: datos pre-recopilados en el prompt
- Sin plugins MCP: `--disable-slash-commands --mcp-config empty`
- Helpers Rust: `find_agent()`, `build_full_prompt()`, `invoke_claude()` en `blocks.rs`
- Prioridad agente: repo clonado > built-in. Si repo no tiene el agente, cae a built-in + CLAUDE.md del repo como contexto

**Estrategia incremental:**
- Bloques confirmed/synced/error se preservan
- Bloques auto/closed se reemplazan al regenerar

**Matching Odoo:**
- branch_task_hints: extrae patron `<proyecto>_<tarea>` de ramas VCS
- tasks_by_project: tareas abiertas de proyectos relevantes (filtradas por mes para tareas mensuales)
- context_mappings: mapeos aprendidos (SQLite) + mapeos TOML admin (prioridad TOML sobre DB)
- Reglas de usuario: reuniones → tareas mensuales en "Temas internos"

### Mapeos TOML

Archivo `~/.config/mimir/mappings.toml` con reglas admin-managed. Se resuelve en el daemon (`mappings_toml.py`) antes de enviar datos a Claude (mode-agnostic).

**Tipos de reglas:**
- `[[context_rules]]`: context_key exacto → proyecto + tarea Odoo
- `[[branch_rules]]`: patron de rama → proyecto (se cruza con senales del dia)
- `[[calendar_rules]]`: patron de evento → proyecto + tarea (con expansion `{month}`/`{year}`)
- `[[app_rules]]`: app activa → proyecto (solo si no hay ctx git)
- `[defaults]`: proyecto y confidence por defecto

**Resolucion:** `_build_generation_data()` en `blocks.py` llama a `resolve_all()` que genera context_mappings virtuales, enriquece calendar_events y recopila project IDs referenciados.

### Historial de navegador

Modulo `browser_history.py`: lee DBs SQLite locales de navegadores Chromium (Chrome, Brave, Vivaldi, Edge) y Firefox.

- Activado por config: `capture_browser_history: bool` (default false)
- Navegadores seleccionables: `browser_history_browsers: list[str]` (default todos)
- Deteccion automatica: `detect_browsers()` busca DBs en rutas conocidas + icono del sistema
- Lectura segura: copia DB a tempfile (browser la bloquea) + WAL
- Formato compacto: agrupado por dominio, top 50, con rango temporal y titulos
- Se lee on-demand al generar bloques (no por senal)
- Endpoint: `GET /config/detected-browsers` retorna navegadores con icono base64

### Revision de bloques

Flujo: usuario pulsa "Revisar" en ReviewDay → Tauri obtiene datos via `/blocks/review-data` → invoca `claude --print` con agente timesheet-reviewer.md → parsea JSON → muestra ReviewPanel.

**Verificaciones del reviewer:**
- Temporales: solapamientos, gaps, coherencia duracion, orden cronologico
- Asignacion: confidence baja, proyecto incorrecto, tarea inexistente
- Contenido: descripcion generica, tipo incorrecto, sources incompletos
- Cobertura: horas totales razonables, senales sin cubrir

**UI:** ReviewPanel colapsable con barra de resumen + lista de issues por severidad (error/warning/info)

### Empaquetado

Dos paquetes .deb + AppImage:
- `mimir` (.deb): app Tauri + mimir-server + agente timesheet-generator en /usr/share/mimir/agents/
- `mimir-capture` (.deb): captura + systemd service + extension GNOME Shell
- Version bump bot: /bump patch|minor|major en PRs
- Version check obligatorio en CI

### Comunicacion entre componentes

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
    |           [NotificationService background task]
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
    |   Platform (xdotool / GNOME D-Bus)
    |      |
    |   Context Enricher (git, SSH, child processes)
    |      |
    |   Poller -> SQLite (solo signals, bloques bajo demanda)
    |
    |
    |--- Generacion de bloques (bajo demanda) ---
    |
    |   Tauri command: generate_blocks_with_agent
    |      |
    |      | GET /blocks/generation-data (signals + VCS + calendar + Odoo + TOML + browser)
    |      |
    |      | claude --print --model haiku --system-prompt (timesheet-generator.md + rules)
    |      |
    |      | POST /blocks/generate (JSON -> SQLite)
    |
    |
    |--- Revision de bloques (bajo demanda) ---
    |
    |   Tauri command: review_blocks_with_agent
    |      |
    |      | GET /blocks/review-data (bloques + generation-data)
    |      |
    |      | claude --print --model haiku --system-prompt (timesheet-reviewer.md + rules)
    |      |
    |      | JSON -> ReviewPanel (no modifica datos)
```

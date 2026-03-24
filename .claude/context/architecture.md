## Arquitectura

Version actual: v0.7.0. Multi-source (GitHub + GitLab) + Descubrir + auto-asignacion + context affinity + GitHub OAuth.

### Procesos

**mimir-capture** (puerto 9476)
- Proceso independiente, corre como systemd user service
- Poller (ciclo cada 30s), SignalAggregator, Context Enricher, Tray Icon
- Platform layer: X11 (xdotool) + Wayland (GNOME Shell extension D-Bus) + D-Bus logind
- Deteccion automatica de entorno via $XDG_SESSION_TYPE
- Context enricher: baja al proceso hijo mas profundo para detectar git repo en terminales
- System context: idle time (Mutter), audio/reuniones (pactl), workspace
- Auto-asignacion: consulta context_mappings al crear bloque
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
| Google Calendar | OAuth2 | Eventos actuales, deteccion reuniones |
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

### Empaquetado

Dos paquetes .deb + AppImage:
- `mimir` (.deb): app Tauri + mimir-server en /usr/bin/
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
    |   SignalAggregator -> SQLite (signals + blocks + auto-assign)
```

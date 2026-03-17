## Arquitectura

Version actual: v0.4.1. Dashboard configurable + MR features + notificaciones.

### Procesos

**mimir-capture** (puerto 9476)
- Proceso independiente, corre como systemd user service
- Poller (ciclo cada 30s), SignalAggregator, Context Enricher, Tray Icon
- Platform layer: X11 (xdotool) + Wayland (GNOME Shell extension D-Bus) + D-Bus logind
- Deteccion automatica de entorno via $XDG_SESSION_TYPE
- System context: idle time (Mutter), audio/reuniones (pactl), workspace
- Endpoint /health y /status (incluye backend activo)
- Siempre corriendo en background, independiente de la app

**mimir-server** (puerto 9477)
- Lanzado por Tauri como child process al abrir la app
- FastAPI completo: CRUD blocks, signals, split/merge, sync Odoo, GitLab, IA, config
- Google Calendar OAuth2 + consulta de eventos
- NotificationService como background task (asyncio, lifespan)
- Se mata al cerrar la app Tauri

**SQLite compartida**
- Ambos procesos acceden a la misma base de datos
- WAL mode para concurrencia segura entre capture y server
- Tablas: blocks, signals, block_signals, ai_cache, source_tokens, preferences_cache, item_preferences, notifications, context_mappings

### Flujo de captura (v0.3.0)

```
Poller (cada 30s)
  |
  +-- Platform: get_active_window() [X11 o Wayland]
  +-- Context Enricher: enrich_pid() [git, SSH]
  +-- System Context: get_system_context() [idle, audio, workspace]
  +-- Google Calendar: get_current_event() [evento activo]
  |
  v
Senal -> SQLite (signals table)
  |
  v
SignalAggregator (determinista, tiempo real)
  |-- Reglas: git project > browser domain > app name
  |-- Meeting detection: audio + calendario
  |-- Transient apps: heredan contexto
  |-- Inactivity threshold: 5 min (configurable)
  |
  v
Bloques -> SQLite (blocks + block_signals tables)
  |
  v
Usuario revisa en "Revisar dia"
  +-- Bloques agrupados (vista normal)
  +-- Senales crudas (vista detalle)
  +-- Split/merge bloques
  +-- IA: descripciones + sugerencias
```

### Ciclo de vida de bloques

```
auto -> closed -> confirmed -> synced
                            -> error
```

- auto: bloque abierto, el aggregator lo construye
- closed: aggregator lo cerro (cambio contexto / inactividad)
- confirmed: usuario lo aprobo
- synced: enviado a Odoo
- error: fallo al enviar

### Integraciones

| Servicio | Auth | Funcionalidad |
|---|---|---|
| Odoo v11 | XMLRPC + password | Timesheets, proyectos, tareas, fichaje |
| Odoo v16+ | REST + API key | Timesheets, proyectos, tareas, fichaje |
| GitLab | Personal Access Token | Issues, merge requests, TODOs, scoring, notas, conflictos |
| Google Calendar | OAuth2 | Eventos actuales, deteccion reuniones |
| Gemini/Claude/OpenAI | API key | Descripciones automaticas de bloques |

### Dashboard

Sistema de widgets configurable:
- Widget registry (`src/lib/widget-registry.ts`) con 10 tipos
- Cada widget es un componente independiente en `src/components/dashboard/widgets/`
- DashboardGrid soporta drag & drop, resize, add/remove
- Config persistente por widget en `dashboard_widgets` de AppConfig
- Galeria para anadir nuevos widgets + modal de configuracion

### Notificaciones

- NotificationService: background task async en el server (FastAPI lifespan)
- Tabla `notifications` en SQLite con TTL configurable
- NotificationBell en header con polling 30s + dropdown
- Configurable por tipo de evento en Settings > Notificaciones
- Pendiente: desktop notifications (tauri-plugin-notification), tray badge

### Empaquetado

Dos paquetes .deb + AppImage:
- `mimir` (.deb): app Tauri + mimir-server en /usr/bin/
- `mimir-capture` (.deb): captura + systemd service + extension GNOME Shell
- AppImage: app Tauri standalone

Build: `bash scripts/build.sh deb`
CI: GitHub Actions, trigger en push de tag `v*`

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
    |   SignalAggregator -> SQLite (signals + blocks)
```

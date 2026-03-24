# Mimir - Progreso del Proyecto

Asistente inteligente de imputacion de horas.
Ultima actualizacion: 2026-03-22
Version actual: v0.5.1

---

## Resumen del stack

| Componente | Tecnologia | Estado |
|---|---|---|
| Frontend desktop | Tauri 2 + Vue 3 + TypeScript + Vite | v0.5.1 |
| Backend desktop | Rust (Tauri commands) | v0.5.1 |
| Capture daemon | Python 3.10+ (asyncio + poller + signals) | v0.5.1 |
| Server daemon | Python 3.10+ (FastAPI + uvicorn) | v0.5.1 |
| Base de datos local | SQLite (aiosqlite), compartida capture/server | Operativa |
| CI/CD | GitHub Actions (release en tag) | Operativo |

---

## v0.3.1 — GitHub + Multi-Source + Descubrir + Auto-asignacion

**Fecha:** 2026-03-21/22
**Tests: 156 pasando, 0 errores TS, 0 errores Rust**

### Auto-asignacion y recomendaciones

| Tarea | Estado |
|---|---|
| Migration registry versionado (schema_version + 4 migraciones) | Completado |
| blocks.context_key + backfill desde senales | Completado |
| suggest_mapping: exacto -> parcial -> historial | Completado |
| SignalAggregator auto-asigna proyecto Odoo desde context_mappings | Completado |
| Aprendizaje: confirmar bloque con proyecto guarda mapeo | Completado |
| BlockEditor: sugerencia pre-cargada + boton "Usar" | Completado |
| Tarea Odoo searchable en BlockEditor | Completado |
| 4 endpoints CRUD context_mappings + 4 Tauri commands | Completado |

### Integracion GitHub

| Tarea | Estado |
|---|---|
| GitHubSource adapter (12 metodos: issues, PRs, search, comments, reviews, files, notifications, labels, user) | Completado |
| Normalizacion completa (user_notes_count, milestone, due_date, assignees, label_objects) | Completado |
| 11 endpoints GitHub en server.py | Completado |
| Tab "Repositorios" en Settings (GitLab + GitHub juntos) | Completado |
| Iconos SVG reales (SourceIcon.vue) para GitHub y GitLab | Completado |
| Icono dinamico Odoo (logo de la empresa) | Completado |
| github_token_stored en AppConfig + keyring + push config | Completado |
| GitHub OAuth (opcion OAuth o token) | Pendiente |

### Issues/MRs Multi-Source

| Tarea | Estado |
|---|---|
| _source field + filtro por fuente (dinamico) | Completado |
| Labels con color desde GitHub (label_objects) | Completado |
| Fix scoring NaN (fallbacks seguros) | Completado |
| ScoreBadge editable inline (click -> input) | Completado |
| Prioridad manual: agrupar por manual_priority | Completado |
| Deduplicacion por project_path#iid | Completado |
| Busqueda multi-source (GitHub + GitLab paralelo) | Completado |
| Filtro multi-proyecto con chips | Completado |
| Tiempo imputado Odoo solo para GitLab | Completado |
| Followed items con metadatos (source, project_path, iid, title) | Completado |
| Endpoints followed buscan en ambas fuentes por item individual | Completado |

### Vista Descubrir

| Tarea | Estado |
|---|---|
| Ruta /discover + entrada sidebar "Descubrir" | Completado |
| Barra filtros: fuente + tipo + repo (autocomplete) + busqueda + limite | Completado |
| DiscoverTable con badges Issue/PR, boton Seguir/Siguiendo | Completado |
| Seguimiento con metadatos para recuperar individualmente | Completado |
| Contador "Mostrando N de M" + boton "Mostrar mas" | Completado |
| Busqueda eliminada de IssuesView y MergeRequestsView | Completado |
| Vista Kanban/cards | Pendiente (futuro) |

### Menu contextual

| Tarea | Estado |
|---|---|
| ContextMenu.vue generico con soporte select inline | Completado |
| Click derecho en Issues (Tareas) | Completado |
| Click derecho en Ramas | Completado |
| Dejar de seguir desde tabla (followed-dot clickeable) | Completado |

### UI/UX

| Tarea | Estado |
|---|---|
| IntegrationCard rediseñado (footer unificado, slot #icon) | Completado |
| Modales con Aceptar/Cancelar (edicion en copia local) | Completado |
| Footer modal detalle sticky | Completado |
| Zoom afecta popups | Completado |
| Sidebar: Tareas, Ramas, Descubrir | Completado |
| Senales con tilde en toda la UI | Completado |

### Captura

| Tarea | Estado |
|---|---|
| Fix context_key: baja al proceso hijo mas profundo | Completado |
| _read_deepest_child_cwd + _get_child_pids | Completado |
| No asignar project_path si no hay git root real | Completado |

### Infraestructura

| Tarea | Estado |
|---|---|
| Version bump bot (scripts/bump-version.sh + CI workflows) | Completado |
| __version__ centralizado en __init__.py | Completado |
| build.sh: fix version en DEBIAN/control | Completado |
| DaemonClient timeout 30s | Completado |
| App.vue: retry health check + push config automatico | Completado |
| Banner version mismatch capture vs server | Completado |
| inactivity_threshold_minutes separado de refresh_interval_seconds | Completado |

---

## v0.3.0 — Wayland + Senales + Google Calendar

**Fecha:** 2026-03-16
**Tests: 142 pasando, 0 warnings**

### Arquitectura de senales

| Tarea | Estado |
|---|---|
| SignalAggregator con agrupacion determinista | Completado |
| context_key: git project > browser domain > app name | Completado |
| API: GET /signals, POST split, POST merge | Completado |
| 22 tests del SignalAggregator | Completado |

### Soporte Wayland

| Tarea | Estado |
|---|---|
| Extension GNOME Shell (mimir-window-tracker) | Completado |
| LinuxProvider: deteccion X11/Wayland automatica | Completado |

### Google Calendar + Empaquetado

| Tarea | Estado |
|---|---|
| GoogleCalendarClient con OAuth2 | Completado |
| .deb unificado + GitHub Actions release | Completado |

---

## Fases anteriores (v0.1.0 - v0.2.0)

### v0.1.0 — Scaffold + Core
Daemon Core + Config/Auth + Odoo + IA + GitLab + Dashboard + Empaquetado.

### v0.2.0 — Refactor capture/server + UI/UX
Separacion en dos procesos (capture 9476, server 9477). Componentes UI compartidos.

---

## Pendiente

1. GitHub OAuth (opcion OAuth o token en Settings)
2. NotificationService: deteccion real de cambios (actualmente stub)
3. Widgets placeholder: IssuesProyecto, HorasSemana, Calendario
4. Desktop notifications (tauri-plugin-notification)
5. Vista Kanban/cards en Descubrir
6. UI gestion de servicios (activar capture, instalar extension)
7. Google Cloud Console OAuth2
8. Busqueda de repos/usuarios en Descubrir
9. Optimizar followed items (evitar get_issues() completo)
10. Modelo de monetizacion

---

## Decisiones de arquitectura

| Decision | Detalle |
|---|---|
| Senales como fuente de verdad | Cada poll genera 1 senal. Bloques se derivan con algoritmo determinista |
| SignalAggregator vs BlockManager | Agrupa por context_key (git > web > app) |
| IA no agrupa, solo describe | Agrupacion determinista. IA genera descripciones |
| Separacion capture/server | capture (9476) systemd; server (9477) child Tauri |
| X11 + Wayland | Deteccion automatica. Extension GNOME Shell para Wayland |
| item_preferences generica | Una tabla para issues y MRs con composite key + metadatos (source, project_path, iid) |
| Dashboard dinamico | Widget registry + componentes individuales |
| Notificaciones async | NotificationService background task en FastAPI lifespan |
| Multi-source VCS | SourceRegistry con adaptadores GitLab + GitHub. Normalización en adapters |
| Deduplicacion | Por project_path#iid (no por id, que difiere entre endpoints GitHub) |
| Migration registry | schema_version table + migraciones secuenciales numeradas |
| Context auto-assignment | context_mappings tabla + aprendizaje al confirmar bloques |
| Child process CWD | Baja al proceso hijo mas profundo para detectar git repo en terminales |

# Mimir - Progreso del Proyecto

Asistente inteligente de imputacion de horas.
Ultima actualizacion: 2026-03-17
Version actual: v0.4.1

---

## Resumen del stack

| Componente | Tecnologia | Estado |
|---|---|---|
| Frontend desktop | Tauri 2 + Vue 3 + TypeScript + Vite | v0.4.1 |
| Backend desktop | Rust (Tauri commands) | v0.4.1 |
| Capture daemon | Python 3.10+ (asyncio + poller + signals) | v0.3.0 |
| Server daemon | Python 3.10+ (FastAPI + uvicorn) | v0.4.1 |
| Base de datos local | SQLite (aiosqlite), compartida capture/server | Operativa |
| CI/CD | GitHub Actions (release en tag) | Operativo |

---

## v0.4.1 — Refactor + MRs + Dashboard + Notificaciones

**Fecha:** 2026-03-17
**Tests: 147 pasando, 4 preexistentes (google-genai)**

### Refactor SettingsView

| Tarea | Estado |
|---|---|
| Componentes base: SettingGroup, SettingRow, CredentialField | Completado |
| GeneralTab, CaptureTab, OdooTab, GitLabTab, AITab, GoogleTab, ServicesTab | Completado |
| NotificationsTab (nuevo) | Completado |
| SettingsView reducido a shell (~120 lineas, era 1243) | Completado |

### MR Features

| Tarea | Estado |
|---|---|
| Tabla item_preferences generica (reemplaza issue_preferences) | Completado |
| MR store con preferences/followed/search/filters | Completado |
| MRsView con filtros Todas/Asignados/Revisor/Seguidos | Completado |
| MRDetailModal con conflictos, pipeline, notas, score editable | Completado |
| MRTable actualizado con emit select + followed indicator | Completado |
| Busqueda global de MRs + seguimiento | Completado |
| GitLab: search_merge_requests, get_mr_notes, get_mr_conflicts | Completado |
| GitLab: get_merge_requests_by_ids, get_todos, get_current_user | Completado |
| Issues store migrado a item_preferences | Completado |

### Dashboard configurable

| Tarea | Estado |
|---|---|
| Widget registry (widget-registry.ts) con 10 tipos | Completado |
| Widgets extraidos: Jornada, Servicios, HorasHoy, Progreso, TopIssues | Completado |
| Widgets nuevos: MRsPendientes, Todos | Completado |
| Widgets placeholder: IssuesProyecto, HorasSemana, Calendario | Pendiente |
| DashboardGrid refactorizado para modelo dinamico | Completado |
| WidgetGallery (anadir widgets) | Completado |
| WidgetConfigModal (config por widget) | Completado |
| DashboardView reescrito con add/remove/reorder/config | Completado |

### Notificaciones

| Tarea | Estado |
|---|---|
| Tabla notifications en SQLite + CRUD | Completado |
| NotificationService con loop async (stub) | Completado |
| Endpoints: GET /notifications, PUT read, PUT read-all, GET count | Completado |
| NotificationBell en header con polling + dropdown | Completado |
| NotificationsTab en Settings con toggles por tipo | Completado |
| Deteccion real de cambios en NotificationService | Pendiente |
| Desktop notifications via tauri-plugin-notification | Pendiente |
| Tray badge con conteo no leidas | Pendiente |

---

## v0.4.0 — Bugs X11 + Features Issues + Timesheets

**Fecha:** 2026-03-17

### Bugfixes

| Bug | Solucion |
|---|---|
| Texto Google Calendar "pestana Captura" incorrecto | Cambiado a "pestana Google" |
| Timezone Odoo: 1h offset en fichajes | Usa timezone local (Europe/Madrid) en vez de UTC |
| X11: xdotool no diagnosticado al arrancar | Log ERROR + check al startup |

### Issues features

| Tarea | Estado |
|---|---|
| Score manual complementario (issue_preferences SQLite) | Completado |
| Busqueda global de issues en GitLab + seguimiento | Completado |
| Labels de prioridad configurables desde Settings > GitLab | Completado |
| Popup detalle issue: markdown, notas, tiempo Odoo, score editable | Completado |
| Filtros: Todas / Asignadas / Seguidas | Completado |

### Timesheets

| Tarea | Estado |
|---|---|
| Popup edicion: proyecto, tarea, descripcion, horas | Completado |
| Boton "Ir a Odoo" desde popup | Completado |

### Infraestructura

| Tarea | Estado |
|---|---|
| Sync Rust AppConfig (12 campos faltantes) | Completado |
| 7 Tauri commands + 7 FastAPI endpoints | Completado |
| marked + DOMPurify como dependencias | Completado |
| 9 tests nuevos | Completado |

---

## v0.3.0 — Wayland + Senales + Google Calendar

**Fecha:** 2026-03-16
**Tests: 142 pasando, 0 warnings**

### Arquitectura de senales (reemplazo de BlockManager)

| Tarea | Estado |
|---|---|
| Tabla signals + block_signals en SQLite | Completado |
| SignalAggregator con agrupacion determinista | Completado |
| context_key: git project > browser domain > app name | Completado |
| Apps transitorias heredan contexto | Completado |
| Inactivity threshold configurable (default 5min) | Completado |
| API: GET /signals, POST split, POST merge | Completado |
| Frontend: tabla senales crudas en ReviewDayView | Completado |
| 22 tests del SignalAggregator | Completado |

### Soporte Wayland

| Tarea | Estado |
|---|---|
| Extension GNOME Shell (mimir-window-tracker) | Completado |
| D-Bus service GetActiveWindow (pid, wm_class, title) | Completado |
| LinuxProvider: deteccion X11/Wayland automatica | Completado |
| Extension incluida en .deb de mimir-capture | Completado |

### Google Calendar

| Tarea | Estado |
|---|---|
| GoogleCalendarClient con OAuth2 | Completado |
| Enriquecimiento de senales con calendar_event/attendees | Completado |
| Tab "Google" en Settings con login/logout | Completado |

### Empaquetado y CI

| Tarea | Estado |
|---|---|
| .deb unificado: mimir + mimir-capture | Completado |
| GitHub Actions: release automatica en tag v* | Completado |

---

## Fases anteriores (v0.1.0 - v0.2.0)

### v0.1.0 — Scaffold + Core
Daemon Core + Config/Auth + Odoo + IA + GitLab + Dashboard + Empaquetado.

### v0.2.0 — Refactor capture/server + UI/UX
Separacion en dos procesos (capture 9476, server 9477). Componentes UI compartidos. Composables. Formatos configurables.

---

## Pendiente

1. Bug captura X11 (diagnosticar con journalctl manana)
2. Verificar fix formato horas fichajes Odoo
3. Auto-asignacion de bloques via context_mappings
4. Algoritmo de recomendacion (fuzzy match, historial)
5. UI de gestion de servicios (activar capture, instalar extension)
6. Configurar Google Cloud Console para OAuth2
7. NotificationService: deteccion real de cambios (actualmente stub)
8. Widgets placeholder: IssuesProyecto, HorasSemana, Calendario
9. Desktop notifications (tauri-plugin-notification)
10. Tray badge notificaciones
11. GitLab OAuth2 (aplazado para version enterprise)

---

## Decisiones de arquitectura

| Decision | Detalle |
|---|---|
| Senales como fuente de verdad | Cada poll genera 1 senal. Bloques se derivan con algoritmo determinista |
| SignalAggregator vs BlockManager | Reemplaza BlockManager. Agrupa por context_key (git > web > app) |
| IA no agrupa, solo describe | Agrupacion es determinista. IA solo genera descripciones y sugiere split/merge |
| Bloques confirmados intocables | IA no puede modificar bloques confirmados (solo descripciones) |
| Separacion capture/server | capture (9476) systemd service; server (9477) child process Tauri |
| X11 + Wayland | Deteccion automatica. Extension GNOME Shell para Wayland |
| .deb separados | mimir (app) + mimir-capture (captura, opcional) |
| OAuth2 para Google | Tokens en disco local, refresh automatico |
| Permisos de captura | Cada tipo de dato (window, git, idle, audio, ssh) se puede desactivar |
| item_preferences generica | Una tabla para issues y MRs con composite key (item_id, item_type) |
| Dashboard dinamico | Widget registry + componentes individuales + config persistente por widget |
| Notificaciones async | NotificationService como background task en FastAPI lifespan |

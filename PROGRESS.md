# Mimir - Progreso del Proyecto

Asistente inteligente de imputacion de horas.
Ultima actualizacion: 2026-03-16
Version actual: v0.3.0

---

## Resumen del stack

| Componente | Tecnologia | Estado |
|---|---|---|
| Frontend desktop | Tauri 2 + Vue 3 + TypeScript + Vite | v0.3.0 |
| Backend desktop | Rust (Tauri commands) | v0.3.0 |
| Capture daemon | Python 3.10+ (asyncio + poller + signals) | v0.3.0 |
| Server daemon | Python 3.10+ (FastAPI + uvicorn) | v0.3.0 |
| Base de datos local | SQLite (aiosqlite), compartida capture/server | Operativa |
| CI/CD | GitHub Actions (release en tag) | Operativo |

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
| Extraccion de dominio del titulo del navegador | Completado |
| Apps transitorias (nautilus, etc.) heredan contexto | Completado |
| Inactivity threshold configurable (default 5min) | Completado |
| Crash recovery del aggregator | Completado |
| window_titles_json generado desde senales | Completado |
| Poller escribe senales + llama al aggregator | Completado |
| capture.py usa SignalAggregator en vez de BlockManager | Completado |
| API: GET /signals, POST split, POST merge | Completado |
| Frontend: tabla senales crudas en ReviewDayView | Completado |
| Store blocks: signals state, splitBlock, mergeBlocks | Completado |
| Tauri commands: get_signals, split_block, merge_blocks | Completado |
| 22 tests del SignalAggregator | Completado |

### Soporte Wayland

| Tarea | Estado |
|---|---|
| Extension GNOME Shell (mimir-window-tracker) | Completado |
| D-Bus service GetActiveWindow (pid, wm_class, title) | Completado |
| Compatible GNOME 42-46 (formato legacy) | Completado |
| LinuxProvider: deteccion X11/Wayland via $XDG_SESSION_TYPE | Completado |
| Backend Wayland con conexion D-Bus persistente | Completado |
| Reconnect automatico si conexion se pierde | Completado |
| /status incluye backend activo (x11/wayland) | Completado |
| Extension incluida en .deb de mimir-capture | Completado |
| 9 tests del platform layer | Completado |

### System context

| Tarea | Estado |
|---|---|
| Idle time via Mutter IdleMonitor D-Bus | Completado |
| Deteccion audio activo via pactl | Completado |
| Deteccion automatica de reuniones (Meet, Zoom, Teams, etc.) | Completado |
| Meeting detection: audio + Google Calendar | Completado |
| Permisos de captura configurables en Settings | Completado |
| Tab "Captura" con toggles individuales | Completado |

### Google Calendar

| Tarea | Estado |
|---|---|
| GoogleCalendarClient con OAuth2 | Completado |
| Flujo: auth URL -> callback -> tokens | Completado |
| Consulta evento actual (summary, attendees, meet_link) | Completado |
| Enriquecimiento de senales con calendar_event/attendees | Completado |
| context_key "meeting:Nombre evento" cuando hay reunion | Completado |
| Endpoints: auth-url, callback, status, current-event, disconnect | Completado |
| Tab "Google" en Settings con login/logout | Completado |
| Tauri commands: get_google_auth_url, status, disconnect | Completado |

### Bugfixes

| Bug | Solucion |
|---|---|
| Timezone desfasada en widget Jornada | Odoo devuelve UTC sin 'Z', ahora se anade. formatTime usa timezone configurable |
| Boton "Fichar salida" no aparece | Odoo v11 devuelve check_out=false, normalizado a null |
| Captura no registra bloques en Wayland | xdotool no funciona en Wayland, ahora usa extension GNOME D-Bus |

### UI/UX

| Tarea | Estado |
|---|---|
| IntegrationCard: patron unificado login/logout | Completado |
| ModalDialog: popups para editar config integraciones | Completado |
| Tabs Odoo/GitLab/Google con IntegrationCard | Completado |
| Timezone configurable en Settings | Completado |
| Migracion google-generativeai a google-genai (0 warnings) | Completado |

### Empaquetado y CI

| Tarea | Estado |
|---|---|
| .deb unificado: mimir (app+server) + mimir-capture (capture+systemd+extension) | Completado |
| GitHub Actions: release automatica en tag v* | Completado |
| build.sh target 'deb' | Completado |

### Pendiente para siguiente sesion

- Separar tabs de SettingsView en componentes individuales (OdooTab, GitLabTab, GoogleTab, CaptureTab)
- Configuracion de retencion de datos (TTL de senales y bloques)
- UI de gestion de servicios (activar/desactivar capture desde la app, instalar extension)
- Probar end-to-end en el otro ordenador
- Integracion Google Calendar: configurar proyecto en Google Cloud Console

---

## Fases anteriores (v0.1.0 - v0.2.0)

### Fase 0-6 (v0.1.0)
Scaffold + Daemon Core + Config/Auth + Odoo + IA + GitLab + Dashboard + Empaquetado.
Ver commits historicos para detalle.

### v0.2.0 — Refactor capture/server + UI/UX
Separacion en dos procesos (capture 9476, server 9477). Componentes UI compartidos. Composables. Formatos configurables, zoom, sidebar colapsable, columnas redimensionables, objetivos semanales.

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

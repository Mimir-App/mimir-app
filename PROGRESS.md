# Mimir - Progreso del Proyecto

Asistente inteligente de imputacion de horas para FactorLibre.
Ultima actualizacion: 2026-03-15

---

## Resumen del stack

| Componente | Tecnologia | Estado |
|---|---|---|
| Frontend desktop | Tauri 2 + Vue 3 + TypeScript + Vite | v0.2.0 completo |
| Backend desktop | Rust (Tauri commands) | v0.2.0 completo |
| Capture daemon | Python 3.10+ (asyncio + poller + tray) | v0.2.0 completo |
| Server daemon | Python 3.10+ (FastAPI + uvicorn) | v0.2.0 completo |
| Base de datos local | SQLite (aiosqlite), compartida capture/server | Operativa |
| Base de datos config | JSON (Tauri) | Operativa |

---

## Fase 0 - Scaffold COMPLETADA

**Fecha:** 2026-03-12

### Daemon Python (`daemon/`)

| Modulo | Fichero | Estado | Notas |
|---|---|---|---|
| Entry point | `main.py` | Implementado | Arranca DB + Platform + Poller + Server + Tray |
| Servidor API | `server.py` | Implementado | CORS, CRUD blocks, summary, mode; stubs Odoo/GitLab |
| Poller | `poller.py` | Implementado | Ciclo asyncio cada 30s |
| Block Manager | `block_manager.py` | Implementado | Herencia contexto, cambio contexto, recovery, checkpoints |
| Context Enricher | `context_enricher.py` | Implementado | /proc, git info con cache, SSH detection, alias resolution |
| Base de datos | `db.py` | Implementado | CRUD completo, summary, open blocks, preferences cache |
| Config | `config.py` | Implementado | Configuracion del daemon |
| Tray icon | `tray.py` | Implementado | pystray en ThreadPoolExecutor |
| Platform base | `platform/base.py` | Implementado | Clase abstracta |
| Platform Linux | `platform/linux.py` | Implementado | xdotool (llamadas separadas) + D-Bus logind + /proc directo |
| Platform Windows | `platform/windows.py` | Stub | NotImplementedError |
| Source base | `sources/base.py` | Implementado | Interfaces CalendarSource, VCSSource |
| Source registry | `sources/registry.py` | Implementado | Registro de adaptadores |
| Source GitLab | `sources/gitlab.py` | Stub | Estructura preparada, sin logica real |
| Integration base | `integrations/base.py` | Implementado | Interfaz TimesheetClient |
| Integration registry | `integrations/registry.py` | Implementado | Registro de adaptadores |
| Integration Odoo v11 | `integrations/odoo_v11.py` | Stub | XMLRPC, sin logica real |
| Integration Odoo v16 | `integrations/odoo_v16.py` | Stub | REST, sin logica real |
| AI base | `ai/base.py` | Implementado | Interfaz AIClient |
| AI Gemini | `ai/gemini.py` | Stub | Heuristico con cache por hash |
| Tests | `tests/` | 34/34 pasando | block_manager, server, poller, context_enricher |

### Frontend Vue 3 + TypeScript (`src/`)

| Modulo | Fichero(s) | Estado | Notas |
|---|---|---|---|
| App principal | `App.vue`, `main.ts` | Implementado | Router + Pinia configurados |
| Layout | `AppSidebar.vue`, `AppHeader.vue`, `TrayStatus.vue` | Implementado | Sidebar con navegacion |
| Vista Dashboard | `DashboardView.vue` | Placeholder | Sin datos reales |
| Vista Revisar Dia | `ReviewDayView.vue` | Placeholder | Sin datos reales |
| Vista Issues | `IssuesView.vue` | Placeholder | Sin datos reales |
| Vista MRs | `MergeRequestsView.vue` | Placeholder | Sin datos reales |
| Vista Timesheets | `TimesheetsView.vue` | Placeholder | Sin datos reales |
| Vista Settings | `SettingsView.vue` | Placeholder | Sin datos reales |
| Componentes blocks | `BlockTable.vue`, `BlockRow.vue`, `BlockEditor.vue` | Placeholder | Estructura creada |
| Componentes issues | `IssueTable.vue`, `IssueDetail.vue` | Placeholder | Estructura creada |
| Componentes MRs | `MRTable.vue`, `MRDetail.vue` | Placeholder | Estructura creada |
| Componentes shared | `FilterBar.vue`, `ScoreBadge.vue`, `ConfidenceBadge.vue`, `SyncStatusBadge.vue` | Placeholder | Estructura creada |
| Stores | `daemon.ts`, `config.ts`, `blocks.ts`, `issues.ts`, `merge_requests.ts`, `timesheets.ts` | Implementados | Con invoke calls a Tauri |
| Composables | `useDaemon.ts`, `useScoring.ts`, `useOdooProjects.ts` | Implementados | Logica reutilizable |
| Lib | `types.ts`, `scoring.ts` | Implementados | Tipos TS + motor scoring portado |

### Backend Rust / Tauri (`src-tauri/`)

| Modulo | Fichero(s) | Estado | Notas |
|---|---|---|---|
| Entry point | `main.rs`, `lib.rs` | Implementado | Configuracion Tauri 2 |
| Commands daemon | `commands/daemon.rs` | Implementado | Proxy HTTP hacia daemon |
| Commands config | `commands/config.rs` | Implementado | Persistencia JSON |
| Commands auth | `commands/auth.rs` | Implementado | Keyring (crate keyring en Cargo.toml) |
| Models | `models/block.rs`, `issue.rs`, `merge_request.rs`, `timesheet.rs` | Implementados | Structs serde |
| Clients | `clients/daemon_client.rs` | Implementado | HTTP client hacia localhost:9477 |

### Verificaciones Fase 0

| Check | Resultado |
|---|---|
| TypeScript (`vue-tsc --noEmit`) | OK - 0 errores |
| Rust (`cargo check`) | OK - compila (2 warnings menores) |
| Vite build | OK - bundle 102KB |
| Daemon arranca (`python -m mimir_daemon`) | OK - HTTP en localhost:9477 |
| Tests daemon (`pytest`) | OK - 8/8 pasando |
| Endpoint `/health` | OK - `{"status": "ok"}` |

---

## Fase 1 - Daemon Core COMPLETADA

**Fecha:** 2026-03-13
**Objetivo:** Que el daemon capture actividad real y genere bloques en SQLite.

| Tarea | Estado | Notas |
|---|---|---|
| Captura de actividad real en Linux (xdotool funcional) | Completado | Llamadas xdotool separadas (mas fiable), lectura /proc directa |
| D-Bus listener para bloqueo/desbloqueo de sesion | Completado | logind LockedHint via dbus-next |
| Context enricher mejorado | Completado | Cache git, deteccion SSH, resolucion alias ~/.ssh/config |
| Block manager: deteccion cambio de contexto | Completado | Nuevo bloque al cambiar app o proyecto; apps transitivas ignoradas |
| Block manager: recuperacion tras crash | Completado | Bloques abiertos >1h se cierran; recientes se retoman |
| Server API mejorada | Completado | CORS, GET/PUT/DELETE por ID, /blocks/summary, validacion 404 |
| Testing end-to-end del poller | Completado | 6 tests con FakePlatform |
| Tests context enricher | Completado | git root, SSH alias, defaults |
| Tests block manager ampliados | Completado | 11 tests (cambio contexto, lock/unlock, recovery) |
| Tests server ampliados | Completado | 12 tests (CRUD, summary, modes) |
| Script instalacion systemd | Completado | `daemon/install-service.sh` |

**Tests: 34/34 pasando** (antes 8/8)

---

## Fase 2 - Config + Auth + Comunicacion COMPLETADA

**Fecha:** 2026-03-13
**Objetivo:** Conectar el frontend Tauri con el daemon real.

| Tarea | Estado | Notas |
|---|---|---|
| Integrar keyring real en Rust | Completado | store/get/delete credential via keyring crate, tokens seguros en keyring del sistema |
| Conectar frontend con daemon real | Completado | Puerto leido de config, DaemonClient usa puerto configurable, api.ts dual mode Tauri/HTTP |
| SettingsView funcional end-to-end | Completado | Formulario completo: Daemon, GitLab, Odoo, General. Tokens en keyring, push config al daemon |
| Health check daemon desde Tauri | Completado | Health check al arrancar App.vue, polling cada 10s, test connection en Settings |
| Push config al daemon | Completado | PUT /config envia credenciales y configura integraciones Odoo en tiempo real |
| Endpoint /config en daemon | Completado | GET/PUT /config, GET /config/integration-status |
| Borrar credenciales | Completado | deleteCredential en keyring, botones en SettingsView |
| useOdooProjects via api.ts | Completado | Migrado de invoke directo a capa api.ts |
| Tests config endpoints | Completado | 6 tests nuevos: config GET/PUT, tokens no expuestos, integration status |

**Tests: 46/46 pasando** (40 existentes + 6 nuevos de config endpoints)

---

## Fase 3 - Revisar Dia + Imputacion Odoo COMPLETADA

**Fecha:** 2026-03-13
**Objetivo:** Flujo completo de captura a imputacion en Odoo.

| Tarea | Estado | Notas |
|---|---|---|
| Implementar `odoo_v11.py` completo | Completado | XMLRPC via asyncio.to_thread, error handling robusto, logging completo |
| Implementar `odoo_v16.py` completo | Completado | REST/JSONRPC via httpx async, error handling robusto, logging completo |
| Conectar clientes Odoo con `server.py` | Completado | GET /odoo/projects, GET /odoo/tasks/{id}, GET /odoo/entries con error handling |
| Sync lifecycle completo | Completado | pending -> sent (con remote_id) o error (con sync_error); update si ya existe remote_id |
| Endpoint retry sync | Completado | POST /blocks/{id}/retry para reintentar bloques con error |
| Editar bloque tras sync | Completado | PUT /blocks/{id} marca bloques synced como confirmed para reenvio |
| BlockEditor con dropdowns funcionales | Completado | Proyectos/tareas de Odoo, filtro de busqueda, guardar + confirmar |
| ReviewDayView funcional | Completado | Navegacion por fecha, confirmar todos, enviar a Odoo, estadisticas |
| BlockRow con retry y tooltips | Completado | Boton reintentar para errores, tooltip en SyncStatusBadge |
| SyncStatusBadge mejorado | Completado | Soporte para estados auto/closed/confirmed/synced/error con tooltips |
| Comando Tauri retry_sync_block | Completado | Proxy HTTP para reintento individual |
| Tests Odoo v11 | Completado | 14 tests con mock de XMLRPC |
| Tests Odoo v16 | Completado | 15 tests con mock de httpx |
| Tests server (sync flow) | Completado | 7 tests nuevos: retry, update synced, sync no client, etc. |

**Tests: 86/86 pasando** (45 Fase 2 + 14 Odoo v11 + 18 Odoo v16 + 9 server nuevos)

---

## Fase 4 - Descripciones IA COMPLETADA

**Fecha:** 2026-03-14
**Objetivo:** Generar descripciones automaticas para los bloques de tiempo.

| Tarea | Estado | Notas |
|---|---|---|
| EnrichedContext con last_commit_message | Completado | git log -1 --format=%s al enriquecer contexto |
| Historial de titulos de ventana | Completado | BlockManager acumula titulos unicos (max 20), guarda en window_titles_json |
| Tabla ai_cache en SQLite | Completado | Cache por hash de senales (SHA-256), evita llamadas repetidas |
| AIService orquestador | Completado | Cache -> provider -> fallback heuristico; nunca bloquea cierre de bloque |
| Providers Gemini/Claude/OpenAI | Completado | Patron adaptador, 3 implementaciones con SDK real + mocks en tests |
| Integracion en block lifecycle | Completado | Genera descripcion al cerrar bloque automaticamente |
| Endpoint generate-description | Completado | POST /blocks/{id}/generate-description para regenerar bajo demanda |
| Configuracion IA en PUT /config | Completado | ai_provider, ai_api_key, ai_user_role, ai_custom_context |
| Frontend tipos + api.ts | Completado | AppConfig extendido, generateDescription en api |
| SettingsView seccion IA | Completado | Proveedor, API key, perfil usuario, contexto adicional |
| BlockEditor boton regenerar | Completado | Boton "Generar con IA" en editor de bloques |
| Tauri command generate_block_description | Completado | Proxy HTTP + campos IA en push_config_to_daemon |

**Tests: 100/100 pasando** (88 Fase 3 + 1 context_enricher + 1 block_manager + 4 ai_service + 4 ai_providers + 2 server)

---

## Fase 5 - Vistas GitLab COMPLETADA

**Fecha:** 2026-03-14
**Objetivo:** Mostrar issues y MRs de GitLab con scoring.

| Tarea | Estado | Notas |
|---|---|---|
| Conectar GitLabSource con server.py | Completado | Endpoints reales via SourceRegistry, error handling robusto |
| Configurar GitLab via PUT /config | Completado | Crea GitLabSource con url+token, registra en SourceRegistry |
| Integration-status para GitLab | Completado | GET /config/integration-status incluye estado GitLab |
| Tests GitLabSource | Completado | 4 tests con mock httpx (issues, MRs, dedup, errors) |
| Tests server GitLab | Completado | 4 tests (endpoints con/sin source, config, integration-status) |
| Scoring en frontend | Ya existia | computeIssueScore/computeMRScore en scoring.ts |
| IssuesView con polling | Completado | Carga + boton refrescar + polling periodico (refresh_interval_seconds) |
| MergeRequestsView con polling | Completado | Mismo patron, cleanup al desmontar vista |
| SettingsView estado GitLab | Completado | Badge GitLab en seccion Integraciones |

**Tests: 108/108 pasando** (100 Fase 4 + 4 GitLabSource + 4 server GitLab)

---

## Fase 6 - Dashboard + Polish + Empaquetado COMPLETADA

**Fecha:** 2026-03-14
**Objetivo:** Pulido final, dashboard con datos reales, y empaquetado para distribucion.

| Tarea | Estado | Notas |
|---|---|---|
| DashboardView conectado a datos reales | Ya existia | Daemon status, horas hoy, bloques pendientes, top issues |
| Temas oscuro/claro (branding FactorLibre) | Ya existia | CSS variables, cambio reactivo, selector en Settings |
| Health check daemon desde Tauri | Ya existia | App.vue: health check al arrancar + polling 10s |
| PyInstaller spec para daemon | Completado | Binario standalone ~56MB, sin dependencia de Python |
| install-service.sh actualizado | Completado | Soporta binario PyInstaller, fallback a Python, DBUS_SESSION_BUS_ADDRESS |
| Tauri bundle config Linux | Completado | .deb y .AppImage, metadata FactorLibre, dependencias declaradas |
| Script build.sh unificado | Completado | `scripts/build.sh [daemon|app|all]` — orquesta PyInstaller + Tauri build |
| .gitignore artefactos build | Completado | PyInstaller build/, *.spec.bak |

**Tests: 108/108 pasando** (sin cambios funcionales)

---

## v0.2.0 - Refactor capture/server + UI/UX completa

**Fecha:** 2026-03-14 a 2026-03-15
**Objetivo:** Separar daemon en dos procesos, mejorar toda la UI/UX, y conectar funcionalidades avanzadas.

### Refactor arquitectura capture/server

| Tarea | Estado | Notas |
|---|---|---|
| Separar daemon en mimir-capture y mimir-server | Completado | capture: poller+blocks+tray+health (puerto 9476); server: FastAPI completa (puerto 9477) |
| SQLite compartida entre ambos procesos | Completado | Misma BD, WAL mode para concurrencia |
| Tauri arranca/mata server como child process | Completado | Server se lanza al iniciar la app y se mata al cerrar |
| systemd service para capture | Completado | Servicio independiente, siempre corriendo en background |
| Control de servicios desde frontend | Completado | Iniciar/detener capture y server desde la UI |
| Script build.sh actualizado | Completado | Targets individuales: capture, server, daemon, app, all |

### Componentes UI/UX nuevos

| Componente | Tipo | Notas |
|---|---|---|
| `CustomSelect` | shared | Reemplaza todos los `<select>` nativos, tema oscuro correcto |
| `CustomDatePicker` | shared | Selector de fecha con navegacion |
| `CollapsibleGroup` | shared | Grupos colapsables con useCollapseAll |
| `ViewToolbar` | shared | Header compartido para todas las vistas |
| `DashboardGrid` | shared | Widgets arrastrables y redimensionables (NxM) |
| `StatusBanner` | shared | Banner de estado para conexion/servicios |
| `LoadingState` | shared | Estado de carga consistente |
| `EmptyState` | shared | Estado vacio consistente |
| `HelpTooltip` | shared | Tooltips de ayuda en Settings y formularios |

### Composables nuevos

| Composable | Funcion |
|---|---|
| `useFormatting` | Formatos configurables de horas y fechas, centralizado |
| `useSortable` | Sorting por click en cabeceras de tabla |
| `useCollapseAll` | Colapsar/expandir todos los grupos |
| `usePolling` | Polling generico con cleanup automatico |
| `useColumnWidths` | Anchos de columna redimensionables y persistentes |
| `useTargets` | Objetivos semanales por dia, calculo progreso |

### Funcionalidades nuevas

| Funcionalidad | Estado | Notas |
|---|---|---|
| Formatos configurables (horas, fechas) | Completado | Decimal/HH:MM, formato fecha configurable en Settings |
| Zoom/escala de interfaz | Completado | Ajuste de escala desde Settings |
| Sidebar colapsable | Completado | Se colapsa para ganar espacio, estado persistente |
| Dashboard con widgets arrastrables NxM | Completado | Grid redimensionable, posiciones guardadas en config |
| Fichaje de asistencia Odoo | Completado | Conectado a hr.attendance via API Odoo |
| Objetivos semanales por dia | Completado | Configuracion de horas objetivo por dia de la semana |
| Barras de progreso dia/semana/mes | Completado | Progreso visual contra objetivos configurados |
| Filtro por usuario en timesheets | Completado | Selector de usuario para ver timesheets de otros |
| Agrupaciones nuevas en tablas | Completado | Por tarea, semana, prioridad, sin agrupar |
| Sorting por click en cabeceras | Completado | Ascendente/descendente con indicador visual |
| Columnas redimensionables y persistentes | Completado | Anchos guardados en config, drag para redimensionar |
| Settings con tabs | Completado | Organizacion por pestanas: General, Odoo, GitLab, IA |
| Tooltips de ayuda en Settings | Completado | HelpTooltip con explicaciones en cada campo |
| Botones probar conexion Odoo/GitLab | Completado | Test connection con feedback visual |
| Tema oscuro corregido para selects | Completado | CustomSelect con estilos dark mode correctos |

### Correcciones

| Bug | Solucion |
|---|---|
| keyring sync-secret-service | Configuracion correcta del backend keyring en Linux |
| GitLab serde_json::Value | Usar serde_json::Value en vez de tipos estrictos para respuestas GitLab |
| `from __future__ import annotations` | Eliminado en ficheros donde causaba problemas con evaluacion lazy de type hints |
| provide/inject hierarchy | Corregido orden de provide/inject en componentes anidados |

**Tests: ~110 pasando**

**Verificaciones:**
- Daemon tests: `cd daemon && .venv/bin/python -m pytest tests/ -v`
- TypeScript: `npx vue-tsc --noEmit`
- Rust: `cd src-tauri && cargo check`
- Build: `bash scripts/build.sh`

---

## Decisiones de arquitectura

| Decision | Detalle |
|---|---|
| Separacion capture/server | capture (puerto 9476) corre como systemd service; server (puerto 9477) lo lanza Tauri como child process |
| SQLite compartida | Ambos procesos acceden a la misma BD con WAL mode |
| Comunicacion daemon-Tauri | HTTP localhost:9477 (server) |
| Arranque capture | systemd user service, siempre corriendo |
| Arranque server | Tauri lo lanza/mata como child process |
| Imputacion Odoo | Batch por defecto |
| Odoo v11 + v16 | Ambos en MVP (XMLRPC y OAuth respectivamente) |
| Fichaje asistencia | Conectado a hr.attendance de Odoo |
| pytest-asyncio 0.24 | Compatible con `asyncio_mode = "auto"` |
| pystray | En ThreadPoolExecutor para no bloquear asyncio |
| Componentizacion agresiva | Todo reutilizable va a components/shared/, nunca duplicar markup |
| Formatos via useFormatting | Nunca .toFixed() o .toLocaleDateString() directo |
| Dashboard NxM | Widgets arrastrables con grid redimensionable |

---

## Proyecto predecesor: task-management-view (PyQt6)

La aplicacion original PyQt6 de gestion de tareas de GitLab esta operativa y se mantiene hasta que Mimir la reemplace. Implementa:

- Conexion GitLab API v4 (issues, MRs, pipelines)
- Motor de scoring y priorizacion
- Paneles con tablas agrupadas por proyecto
- System tray con notificaciones
- Temas claro/oscuro
- Time tracker local
- Refresco automatico en background (QThread)

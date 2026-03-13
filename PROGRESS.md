# Mimir - Progreso del Proyecto

Asistente inteligente de imputacion de horas para FactorLibre.
Ultima actualizacion: 2026-03-13

---

## Resumen del stack

| Componente | Tecnologia | Estado |
|---|---|---|
| Frontend desktop | Tauri 2 + Vue 3 + TypeScript + Vite | Scaffold completo |
| Backend desktop | Rust (Tauri commands) | Scaffold completo |
| Daemon local | Python 3.10+ (asyncio + FastAPI + uvicorn) | Scaffold completo |
| Base de datos local | SQLite (aiosqlite) | Esquema creado |
| Base de datos config | JSON (Tauri) | Estructura definida |

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

**Verificacion:** Ejecutar el daemon, trabajar unos minutos, y verificar con `curl http://localhost:9477/blocks`.

---

## Fase 2 - Config + Auth + Comunicacion PENDIENTE

**Objetivo:** Conectar el frontend Tauri con el daemon real.

| Tarea | Estado | Notas |
|---|---|---|
| Integrar keyring real en Rust | Pendiente | Crate `keyring` ya en Cargo.toml |
| Conectar frontend con daemon real | Pendiente | Stores ya tienen invoke calls |
| SettingsView funcional end-to-end | Pendiente | |
| Health check daemon desde Tauri | Pendiente | |

---

## Fase 3 - Revisar Dia + Imputacion Odoo PENDIENTE

**Objetivo:** Flujo completo de captura a imputacion en Odoo.

| Tarea | Estado | Notas |
|---|---|---|
| Conectar `odoo_v11.py` con `server.py` | Pendiente | Stubs vacios en server.py |
| Conectar `odoo_v16.py` con `server.py` | Pendiente | Stubs vacios en server.py |
| Implementar endpoints reales de Odoo | Pendiente | |
| BlockEditor con dropdowns de proyectos/tareas | Pendiente | |
| Flujo: captura -> revision -> confirmacion -> envio Odoo | Pendiente | |

---

## Fase 4 - Descripciones IA PENDIENTE

**Objetivo:** Generar descripciones automaticas para los bloques de tiempo.

| Tarea | Estado | Notas |
|---|---|---|
| Implementar llamada real a Gemini API | Pendiente | Stub heuristico existe |
| Cache por hash de senales | Pendiente | Estructura creada |
| Lazy loading de descripciones en frontend | Pendiente | |

---

## Fase 5 - Vistas GitLab PENDIENTE

**Objetivo:** Mostrar issues y MRs de GitLab con scoring.

| Tarea | Estado | Notas |
|---|---|---|
| Conectar `sources/gitlab.py` con `server.py` | Pendiente | Endpoints stub existen |
| Portar scoring completo | Pendiente | TypeScript ya implementado en `src/lib/scoring.ts` |
| Vista Issues funcional | Pendiente | |
| Vista MRs funcional | Pendiente | |

---

## Fase 6 - Dashboard + Polish PENDIENTE

**Objetivo:** Pulido final y dashboard con datos reales.

| Tarea | Estado | Notas |
|---|---|---|
| DashboardView conectado a datos reales | Pendiente | |
| Temas oscuro/claro completos (branding FactorLibre) | Pendiente | |
| Health check daemon desde Tauri | Pendiente | |
| Empaquetado PyInstaller | Pendiente | |

---

## Decisiones de arquitectura

| Decision | Detalle |
|---|---|
| Ubicacion temporal | `mimir/` como subdirectorio de task-management-view. Se creara repo GitHub separado |
| Comunicacion daemon-Tauri | HTTP localhost:9477 |
| Arranque daemon | systemd user service + manual + health check |
| SQLite separados | daemon (bloques) y Tauri (config) |
| Imputacion Odoo | Batch por defecto |
| Odoo v11 + v16 | Ambos en MVP (XMLRPC y OAuth respectivamente) |
| pytest-asyncio 0.24 | Compatible con `asyncio_mode = "auto"` |
| pystray | En ThreadPoolExecutor para no bloquear asyncio |
| Stubs | Endpoints FastAPI devuelven listas vacias; preparados para conectar implementaciones reales |

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

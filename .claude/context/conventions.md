## Convenciones de codigo

### Python (daemon)
- Python 3.10+ minimo. Usar `asyncio` en todo el daemon; nada de threading salvo `pystray`
- Todas las clases y metodos publicos con **docstrings en espanol**
- **Type hints** completos en todas las funciones y metodos
- Todas las llamadas de red en async; UI updates solo via HTTP responses
- Todos los errores capturados — nunca crash; loggear errores, no tracebacks
- JSON guardado con `ensure_ascii=False`, UTF-8 en todo
- `logging` module a nivel INFO; loggear cada refresh, error y cambio de config
- Patron adaptador en todo: IA, integracion, notificaciones, fuentes externas
- VCS sources: GitLabSource y GitHubSource normalizan datos al mismo formato
- Tokens OAuth NUNCA salen del ordenador local
- SQLite local: nunca queries sobre campos dentro de JSON blobs
- Todo codigo OS-specific va en `platform/`. Si aparece fuera, es un bug de arquitectura
- No usar `from __future__ import annotations` — causa problemas con evaluacion lazy de type hints en algunos contextos
- Version centralizada en `__init__.py`, importada por api_server.py y capture.py

### TypeScript / Vue (frontend)
- TypeScript strict mode
- Vue 3 con Composition API (`<script setup>`). No usar Options API
- **Componentizacion agresiva**: toda UI repetida o reutilizable debe ser un componente en `components/shared/` o `components/settings/`. Nunca duplicar markup entre vistas.
- Componentes shared: CustomSelect, CustomDatePicker, CollapsibleGroup, ViewToolbar, DashboardGrid, StatusBanner, LoadingState, EmptyState, HelpTooltip, FilterBar, ScoreBadge, IntegrationCard, ModalDialog, NotificationBell, ContextMenu, SourceIcon
- Componentes settings: SettingGroup, SettingRow, CredentialField + tabs individuales (GeneralTab, CaptureTab, OdooTab, GitLabTab, AITab, GoogleTab, ServicesTab, NotificationsTab)
- Componentes dashboard/widgets: JornadaWidget, ServiciosWidget, HorasHoyWidget, ProgresoWidget, TopIssuesWidget, MRsPendientesWidget, TodosWidget + WidgetGallery, WidgetConfigModal
- Componentes issues: IssueTable, IssueDetailModal
- Componentes merge_requests: MRTable, MRDetailModal
- Componentes discover: DiscoverTable
- Composables en `composables/` para logica reutilizable:
  - `useFormatting` — formatos de horas, fechas y timestamps (obligatorio, nunca `.toFixed()` o `.toLocaleDateString()` directo)
  - `useSortable` — sorting por click en cabeceras de tabla
  - `useCollapseAll` — colapsar/expandir todos los grupos
  - `usePolling` — polling generico con cleanup automatico
  - `useColumnWidths` — anchos de columna redimensionables y persistentes
  - `useTargets` — objetivos semanales por dia, calculo progreso
  - `useOdooProjects` — carga de proyectos/tareas Odoo
  - `useDaemon` — estado y control del daemon
  - `useScoring` — scoring de issues/MRs
- Pinia: un store por dominio (`blocks`, `config`, `daemon`, `issues`, `merge_requests`, `timesheets`)
- El store `blocks` incluye signals state (fetchSignals, splitBlock, mergeBlocks)
- Comunicacion con daemon via Tauri invoke commands (proxy HTTP en Rust)
- No usar `<select>` nativo — usar `CustomSelect` para consistencia visual
- Formatos de horas y fechas siempre via `useFormatting` (nunca `.toFixed()` o `.toLocaleDateString()` directo)
- `ViewToolbar` como header compartido en todas las vistas
- `DashboardGrid` para widgets arrastrables y redimensionables (formato NxM)
- `IntegrationCard` para patron unificado de integraciones: footer con Editar/Comprobar/Desconectar, slot #icon
- `ModalDialog` para popups: showFooter + confirm para edicion con Aceptar/Cancelar, slot #footer para contenido sticky
- `ContextMenu` para click derecho: items normales + select inline con chips
- `SourceIcon` para iconos SVG de GitHub/GitLab
- Deduplicacion de items por `project_path#iid` (no por id)
- Reactividad de Map: siempre crear `new Map()` al actualizar (Vue no detecta `Map.set()`)

### Rust (Tauri backend)
- Tauri 2 commands para proxy HTTP al daemon
- Keyring para almacenamiento seguro de tokens (backend sync-secret-service en Linux)
- Config JSON local para preferencias de la app
- Modelos serde para serializar/deserializar
- Usar `serde_json::Value` para respuestas externas con esquema variable (ej: GitLab API, signals)
- Server daemon lanzado como child process, matado al cerrar la app
- DaemonClient timeout 30s (endpoints externos pueden ser lentos)
- urlencoding crate para encode de parametros en URLs

### General
- Tests: para cada adaptador, al menos un test con mock del servicio externo (~147 tests en daemon)
- Distribucion: scripts/build.sh con targets individuales (capture, server, daemon, app, deb, all)
- CI: GitHub Actions con release automatica al push de tag v*. Version bump bot obligatorio.
- Textos de la interfaz en espanol (con tildes: "señales", no "senales")
- Sidebar: Tareas (issues), Ramas (MRs), Descubrir (busqueda universal)
- Todo debe ser configurable desde Settings (formatos, zoom, objetivos, intervalos, permisos de captura)
- Settings organizados en tabs: General, Captura, Odoo, Repositorios (GitLab + GitHub), IA, Google, Servicios, Notificaciones
- Integraciones siguen patron IntegrationCard: slot #icon, footer con acciones, edicion en modal con Aceptar/Cancelar

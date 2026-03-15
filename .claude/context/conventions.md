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
- Tokens OAuth NUNCA salen del ordenador local
- SQLite local: nunca queries sobre campos dentro de JSON blobs
- Todo codigo OS-specific va en `platform/`. Si aparece fuera, es un bug de arquitectura
- No usar `from __future__ import annotations` — causa problemas con evaluacion lazy de type hints en algunos contextos

### TypeScript / Vue (frontend)
- TypeScript strict mode
- Vue 3 con Composition API (`<script setup>`). No usar Options API
- **Componentizacion agresiva**: toda UI repetida o reutilizable debe ser un componente en `components/shared/` (ej: CustomSelect, CustomDatePicker, CollapsibleGroup, ViewToolbar, DashboardGrid, StatusBanner, LoadingState, EmptyState, HelpTooltip, FilterBar, ScoreBadge). Nunca duplicar markup entre vistas.
- Composables en `composables/` para logica reutilizable:
  - `useFormatting` — formatos de horas y fechas (obligatorio, nunca `.toFixed()` o `.toLocaleDateString()` directo)
  - `useSortable` — sorting por click en cabeceras de tabla
  - `useCollapseAll` — colapsar/expandir todos los grupos
  - `usePolling` — polling generico con cleanup automatico
  - `useColumnWidths` — anchos de columna redimensionables y persistentes
  - `useTargets` — objetivos semanales por dia, calculo progreso
  - `useOdooProjects` — carga de proyectos/tareas Odoo
  - `useDaemon` — estado y control del daemon
  - `useScoring` — scoring de issues/MRs
- Pinia: un store por dominio (`blocks`, `config`, `daemon`, `issues`, `merge_requests`, `timesheets`)
- Comunicacion con daemon via Tauri invoke commands (proxy HTTP en Rust)
- No usar `<select>` nativo — usar `CustomSelect` para consistencia visual
- Formatos de horas y fechas siempre via `useFormatting` (nunca `.toFixed()` o `.toLocaleDateString()` directo)
- `ViewToolbar` como header compartido en todas las vistas
- `DashboardGrid` para widgets arrastrables y redimensionables (formato NxM)

### Rust (Tauri backend)
- Tauri 2 commands para proxy HTTP al daemon
- Keyring para almacenamiento seguro de tokens (backend sync-secret-service en Linux)
- Config JSON local para preferencias de la app
- Modelos serde para serializar/deserializar
- Usar `serde_json::Value` para respuestas externas con esquema variable (ej: GitLab API)
- Server daemon lanzado como child process, matado al cerrar la app

### General
- Considerar `BaseItemPanel` o composable compartido para logica comun Issues/MRs
- Tests: para cada adaptador, al menos un test con mock del servicio externo (~110 tests en daemon)
- Distribucion: scripts/build.sh con targets individuales (capture, server, daemon, app, all)
- Textos de la interfaz en espanol
- Todo debe ser configurable desde Settings (formatos, zoom, objetivos, intervalos)

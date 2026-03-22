# Bugs X11 + Features Issues + Popup Timesheets

Fecha: 2026-03-17

## Contexto

Pruebas en ordenador con X11 revelan bugs en captura, texto incorrecto de Google Calendar, y offset de 1h en fichajes Odoo. Ademas se requieren mejoras en la vista de Issues (score manual, busqueda/seguimiento, labels configurables, popup detalle) y un popup de edicion para timesheets.

---

## Sprint 1: Bugs

### 1.1 Texto Google Calendar

**Archivo**: `src/views/SettingsView.vue:764`
**Problema**: Dice "pestaña Captura" cuando deberia decir "pestaña Google".
**Fix**: Cambiar el texto literal.

### 1.2 Timezone Odoo (offset 1h)

**Problema**: El backend usa `datetime.now(timezone.utc).strftime("%Y-%m-%d")` para determinar "hoy" al buscar attendances. Si el usuario esta en `Europe/Madrid` (UTC+1/+2), entre las 00:00-01:00 hora local, UTC es el dia anterior. Ademas, los timestamps se envian con sufijo "Z" (UTC) y el frontend debe convertirlos a hora local.

**Archivos afectados**:
- `daemon/mimir_daemon/integrations/odoo_v16.py` — lines 238-296
- `daemon/mimir_daemon/integrations/odoo_v11.py` — lines 201-259

**Fix backend**:
- Reutilizar el campo `timezone` que ya existe en `AppConfig` (line 162 en types.ts, default `Europe/Madrid`).
- En `get_today_attendance()`, usar `timezone` del usuario para calcular "hoy" en hora local.
- El check-in/check-out se sigue enviando en UTC (correcto para Odoo).
- **Nota**: Los endpoints `get_blocks`, `get_blocks_summary`, `get_signals` en `server.py` reciben la fecha desde el frontend, por lo que no tienen este problema. Solo `get_today_attendance()` calcula "hoy" internamente.

**Fix frontend**:
- Verificar que los timestamps con "Z" se convierten a hora local al mostrar en el dashboard (widget Jornada).

### 1.3 Captura X11

**Problema**: Solo 1 bloque registrado en todo un dia de trabajo. Senales crudas vacias. Pendiente de diagnostico con `journalctl --user -u mimir-capture`.
**Mejoras inmediatas**:
- Cambiar log de `xdotool no encontrado` de WARNING a ERROR para mayor visibilidad.
- Agregar check diagnostico al arrancar: ejecutar `xdotool getactivewindow` una vez y loguear resultado/error.
- Incluir resultado del check de xdotool en el endpoint `/status` del capture daemon.

**Verificacion**: Confirmar que xdotool esta instalado en el equipo X11 (`which xdotool`).

---

## Sprint 2: Features Issues

### 2.1 Score manual

**Tabla SQLite nueva**: `issue_preferences`
```sql
CREATE TABLE IF NOT EXISTS issue_preferences (
    issue_id INTEGER PRIMARY KEY,  -- GitLab global ID (no iid)
    manual_score INTEGER DEFAULT 0,
    followed BOOLEAN DEFAULT FALSE,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
```

**Nota**: Se usa `id` global de GitLab (unico en toda la instancia), no `iid` (que es scoped por proyecto y causaria colisiones).

**Endpoint nuevo**: `PUT /gitlab/issues/{issue_id}/preferences`
- Body: `{"manual_score": 25, "followed": true}`
- Upsert en `issue_preferences`.
- `issue_id` es el ID global de GitLab.

**Endpoint nuevo**: `GET /gitlab/issues/preferences`
- Retorna todas las preferencias guardadas para merge con issues del frontend.

**Frontend**:
- `computeIssueScore()` ya suma `manual_priority` — solo necesita recibir el valor desde la tabla local.
- En la tabla de issues: celda del score clickeable para editar inline (input numerico).
- En el popup de detalle: campo editable de score manual.

### 2.2 Busqueda y seguimiento de issues

**Endpoint nuevo**: `GET /gitlab/issues/search?q=texto`
- Busca via GitLab API (`GET /issues?search=texto&scope=all`).
- Limitado a 20 resultados (`per_page=20`), sin paginacion adicional (es busqueda interactiva con debounce).
- Retorna lista de issues con misma estructura que `GET /gitlab/issues`.

**Endpoint nuevo**: `GET /gitlab/issues/followed`
- Obtiene las issues seguidas por sus IDs globales.
- Lee `issue_preferences` donde `followed=true`, y consulta GitLab API `GET /issues?iids[]=X&iids[]=Y` para obtener datos frescos.
- Se llama al inicio junto con `GET /gitlab/issues` (asignadas).

**Frontend**:
- Campo de busqueda nuevo encima de la tabla en IssuesView (separado del filtro existente).
- Al escribir (debounce 300ms), muestra dropdown con resultados.
- Cada resultado tiene boton "Seguir" que guarda `followed=true` en `issue_preferences`.
- Las issues seguidas se cargan al inicio via `GET /gitlab/issues/followed` y se muestran junto a las asignadas.
- Indicador visual (icono ojo) en issues seguidas.
- Filtro para mostrar: "Todas", "Asignadas", "Seguidas".

### 2.3 Labels configurables para prioridad

**Endpoint nuevo**: `GET /gitlab/labels`
- Obtiene labels unicas de los proyectos donde el usuario tiene issues (no todos los proyectos accesibles).
- Agrupa y deduplica por nombre.
- Cache en memoria por 1 hora para evitar multiples llamadas a la API de GitLab.

**Config**:
- Nuevo campo en config JSON: `gitlab_priority_labels` — array de `{label: string, weight: number}`.
- Default: el mapeo actual hardcoded (`priority::critical: 100`, `priority::high: 75`, etc.).
- Agregar a TypeScript `AppConfig`, y al struct Rust `AppConfig` (ver nota sobre Rust config).

**Frontend — pestana GitLab en Ajustes**:
- Seccion "Mapeo de prioridad".
- Tabla editable: columna Label (selector con labels disponibles) + columna Peso (input numerico 0-100).
- Boton "Anadir regla" y boton eliminar por fila.
- Al guardar se persiste en config.

**Scoring**:
- `scoring.ts` recibe `PRIORITY_LABELS` desde config en vez de constante hardcoded.
- `scoreLabelPriority()` usa el mapeo dinamico.

### 2.4 Popup detalle de issue

**Componente**: `IssueDetailModal.vue` en `src/components/issues/`
- Usa `ModalDialog` como base (componente shared existente).

**Estructura**:
- **Cabecera**: Titulo, proyecto (`project_path`), `#iid`, labels como chips coloreados
- **Cuerpo**:
  - Descripcion (markdown renderizado con `marked` + `DOMPurify` — nuevas dependencias)
  - Milestone, asignados, fecha limite
  - Score: automatico (readonly) + manual (editable inline)
  - Tiempo dedicado: total horas de Odoo para la tarea — `GET /odoo/entries?task_id=X` (requiere nuevo parametro en endpoint existente)
  - Ultimos N comentarios (notas): `GET /gitlab/issues/{project_id}/{issue_iid}/notes?per_page=N`
  - N configurable, default 5, guardado en config como `issue_notes_count`
- **Footer**: Boton "Ir a GitLab" → abre `web_url` en navegador

**Endpoint nuevo**: `GET /gitlab/issues/{project_id}/{issue_iid}/notes`
- Proxy a GitLab API: `GET /projects/:project_id/issues/:iid/notes?sort=desc&per_page=N`
- Filtra solo notas de tipo "user" (excluye system notes de labels, asignaciones, etc.).

**Endpoint existente modificado**: `GET /odoo/entries`
- Agregar parametro opcional `task_id` para filtrar por tarea.
- Cuando se pasa `task_id`, retorna entradas de esa tarea (sin rango de fecha) y suma total de horas.

**Interaccion**:
- Click izquierdo en fila de issue → abre popup.
- Click derecho en titulo o link directo → abre GitLab (comportamiento actual preservado como acceso rapido).

---

## Sprint 3: Popup edicion timesheets

### 3.1 Popup desde Parte de horas

**Componente**: `TimesheetEditModal.vue` en `src/components/timesheets/`
- Usa `ModalDialog` como base.

**Estructura**:
- **Campos readonly**: Fecha
- **Campos editables**:
  - Proyecto (selector, reutiliza `useOdooProjects`)
  - Tarea (selector dependiente del proyecto seleccionado)
  - Descripcion (textarea)
  - Horas (input numerico, paso 0.25)
- **Footer**: Boton "Guardar", Boton "Ir a Odoo" (abre URL del timesheet en navegador)

**Interaccion**:
- Click en fila de timesheet → abre popup con datos precargados.
- Guardar → llama endpoint, refresca lista.

### 3.2 Endpoint actualizacion timesheet

**Endpoint nuevo**: `PUT /odoo/entries/{entry_id}`
- Body: `{"description": "...", "hours": 1.5, "project_id": 123, "task_id": 456}`
- Backend: Delega a `TimesheetClient.update_entry()` (interfaz base ya define este metodo).
- Si Odoo rechaza la operacion (permiso), se captura el error y se retorna 400 con mensaje (sin pre-read adicional).

### 3.3 URL de timesheet en Odoo

- Construir URL: `{odoo_url}/web#id={entry_id}&model=account.analytic.line&view_type=form`
- Nota: Este formato funciona en v11 y v16. v17+ usa rutas diferentes pero no es version soportada actualmente.

---

## Rust AppConfig — sincronizacion de campos

**Problema critico**: El struct `AppConfig` en `src-tauri/src/commands/config.rs` no tiene todos los campos que existen en el TypeScript `AppConfig`. Al usar `#[serde(default)]`, los campos desconocidos se ignoran al leer pero se **pierden al guardar** (`save_config` serializa solo los campos del struct Rust).

**Campos faltantes en Rust** (ya existentes en TS):
- `timezone: String`
- `signals_retention_days: u32`
- `blocks_retention_days: u32`
- `google_client_id: String`
- `google_client_secret: String`
- `capture_window: bool`
- `capture_git: bool`
- `capture_idle: bool`
- `capture_audio: bool`
- `capture_ssh: bool`

**Campos nuevos a agregar** (este spec):
- `gitlab_priority_labels: Vec<PriorityLabelMapping>` (donde `PriorityLabelMapping { label: String, weight: u32 }`)
- `issue_notes_count: u32` (default 5)

**Fix**: Agregar todos los campos faltantes al struct Rust con defaults apropiados.

---

## Capa Tauri — commands necesarios

Cada endpoint nuevo del daemon necesita un Tauri command correspondiente (proxy HTTP):

| Rust command | Endpoint daemon | Archivos |
|---|---|---|
| `get_issue_preferences` | `GET /gitlab/issues/preferences` | `daemon.rs`, `lib.rs`, `api.ts` |
| `update_issue_preferences` | `PUT /gitlab/issues/{id}/preferences` | `daemon.rs`, `lib.rs`, `api.ts` |
| `search_gitlab_issues` | `GET /gitlab/issues/search?q=` | `daemon.rs`, `lib.rs`, `api.ts` |
| `get_followed_issues` | `GET /gitlab/issues/followed` | `daemon.rs`, `lib.rs`, `api.ts` |
| `get_gitlab_labels` | `GET /gitlab/labels` | `daemon.rs`, `lib.rs`, `api.ts` |
| `get_issue_notes` | `GET /gitlab/issues/{}/notes` | `daemon.rs`, `lib.rs`, `api.ts` |
| `update_timesheet_entry` | `PUT /odoo/entries/{id}` | `daemon.rs`, `lib.rs`, `api.ts` |

---

## Dependencias nuevas

| Paquete | Uso | Sprint |
|---------|-----|--------|
| `marked` (npm) | Renderizar markdown en popup detalle issue | 2 |
| `dompurify` (npm) | Sanitizar HTML del markdown renderizado | 2 |

---

## Tests

Cada endpoint nuevo requiere al menos un test con mock del servicio externo (convencion del proyecto, ~142 tests existentes):

- `test_issue_preferences_crud` — crear, leer, actualizar preferencias
- `test_search_issues` — busqueda con mock GitLab
- `test_followed_issues` — carga de issues seguidas
- `test_gitlab_labels` — obtener y cachear labels
- `test_issue_notes` — notas filtradas (solo user notes)
- `test_update_timesheet` — actualizar entry via adaptador
- `test_odoo_entries_task_filter` — filtro por task_id en entries

---

## Resumen de endpoints

| Metodo | Ruta | Sprint | Descripcion |
|--------|------|--------|-------------|
| PUT | `/gitlab/issues/{id}/preferences` | 2 | Guardar score manual / seguimiento |
| GET | `/gitlab/issues/preferences` | 2 | Obtener todas las preferencias |
| GET | `/gitlab/issues/search?q=texto` | 2 | Buscar issues (max 20 resultados) |
| GET | `/gitlab/issues/followed` | 2 | Issues seguidas con datos frescos |
| GET | `/gitlab/labels` | 2 | Labels unicas (cache 1h) |
| GET | `/gitlab/issues/{project_id}/{iid}/notes` | 2 | Notas/comentarios de una issue |
| GET | `/odoo/entries?task_id=X` | 2 | Entries filtradas por tarea (mod endpoint existente) |
| PUT | `/odoo/entries/{id}` | 3 | Actualizar timesheet entry |

## Resumen de componentes nuevos

| Componente | Ubicacion | Base | Sprint |
|------------|-----------|------|--------|
| `IssueDetailModal.vue` | `src/components/issues/` | `ModalDialog` | 2 |
| `TimesheetEditModal.vue` | `src/components/timesheets/` | `ModalDialog` | 3 |

## Tabla SQLite nueva

| Tabla | Sprint | Descripcion |
|-------|--------|-------------|
| `issue_preferences` | 2 | Score manual, seguimiento por issue (clave: GitLab global ID) |

# Refactor Settings + MR Popup + Dashboard Configurable + Notificaciones

Fecha: 2026-03-17

## Contexto

SettingsView.vue es un archivo enorme que necesita refactorizacion. Se requieren nuevas features: popup detalle de MRs con conflictos y filtros (mismo patron que Issues), dashboard configurable con widgets editables, y sistema de notificaciones (in-app + desktop + tray badge).

Nota: La base de datos se reinicia desde cero para pruebas. No se requiere migracion.

---

## Seccion 1: Refactor SettingsView

### Componentes base compartidos

Nuevos componentes en `src/components/settings/`:

**`SettingGroup.vue`** — Wrapper para un grupo de ajustes con titulo y borde.
- Props: `title: string`, `description?: string`
- Slot default para contenido

**`SettingRow.vue`** — Fila individual de ajuste (label + control).
- Props: `label: string`, `help?: string`
- Slot default para el control (input, select, toggle)

**`CredentialField.vue`** — Campo de credencial con boton test/guardar.
- Props: `label: string`, `stored: boolean`, `placeholder?: string`
- Emits: `save(value)`, `delete`, `test`
- Muestra "**** (guardado)" si stored, input si no.

### Tabs como componentes

Cada tab se extrae a su propio componente:

| Componente | Tab | Contenido |
|---|---|---|
| `GeneralTab.vue` | General | Tema, formato horas/fechas, font size, timezone |
| `CaptureTab.vue` | Captura | Permisos captura, retencion de datos |
| `OdooTab.vue` | Odoo | IntegrationCard, URL, version, credenciales |
| `GitLabTab.vue` | GitLab | IntegrationCard, URL, token, mapeo prioridad labels, notes count |
| `AITab.vue` | IA | Proveedor, API key, perfil, contexto custom |
| `GoogleTab.vue` | Google | IntegrationCard, OAuth2, Calendar config |
| `ServicesTab.vue` | Servicios | Estado servicios, start/stop, health |
| `NotificationsTab.vue` | Notificaciones | Toggles por tipo de evento (nueva, ver seccion 4) |

**`SettingsView.vue`** queda como shell:
- Header con tabs
- `<component :is="currentTabComponent" />` para renderizar el tab activo
- Solo logica de routing entre tabs, nada de formularios

Cada tab recibe `configStore` via `useConfigStore()` directamente (no props).

---

## Seccion 2: MR Popup detalle + conflictos + filtros

### Tabla SQLite: `item_preferences`

Reemplaza `issue_preferences`. Soporta issues y MRs.

```sql
CREATE TABLE IF NOT EXISTS item_preferences (
    item_id INTEGER NOT NULL,
    item_type TEXT NOT NULL CHECK(item_type IN ('issue', 'mr')),
    manual_score INTEGER DEFAULT 0,
    followed BOOLEAN DEFAULT FALSE,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (item_id, item_type)
);
```

### Backend: Metodos GitLab nuevos (gitlab.py)

- `search_merge_requests(query, per_page=20)` — Busqueda global de MRs.
- `get_mr_notes(project_id, mr_iid, per_page=5)` — Notas de usuario de un MR.
- `get_mr_conflicts(project_id, mr_iid)` — Proxy a `GET /projects/:id/merge_requests/:iid/changes`, extrae archivos con conflicto (`diff.conflict == true` o similar).
- `get_merge_requests_by_ids(mr_ids)` — MRs por IDs globales (para seguidos).
- `get_todos()` — Obtiene TODOs del usuario desde GitLab API (`GET /todos`).

### Backend: Endpoints FastAPI nuevos (server.py)

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/gitlab/merge_requests/search?q=texto` | Buscar MRs (max 20) |
| GET | `/gitlab/merge_requests/followed` | MRs seguidos con datos frescos |
| GET | `/gitlab/merge_requests/{project_id}/{mr_iid}/notes` | Notas usuario de un MR |
| GET | `/gitlab/merge_requests/{project_id}/{mr_iid}/conflicts` | Archivos en conflicto |
| PUT | `/items/{item_type}/{item_id}/preferences` | Upsert preferencia (body: manual_score, followed) |
| GET | `/items/preferences?type=issue` | Preferencias por tipo |
| GET | `/gitlab/todos` | TODOs del usuario |

Nota: Los endpoints `/gitlab/issues/{id}/preferences` y `/gitlab/issues/preferences` existentes se reemplazan por los genericos `/items/*`.

### Backend: Actualizar db.py

- Borrar tabla `issue_preferences` y sus metodos CRUD.
- Crear tabla `item_preferences` con metodos:
  - `upsert_item_preference(item_id, item_type, manual_score?, followed?)`
  - `get_item_preferences(item_type)` — retorna todas del tipo
  - `get_followed_item_ids(item_type)` — IDs seguidos de un tipo

### Tauri commands nuevos

| Command | Endpoint |
|---------|----------|
| `search_gitlab_merge_requests` | `GET /gitlab/merge_requests/search?q=` |
| `get_followed_merge_requests` | `GET /gitlab/merge_requests/followed` |
| `get_mr_notes` | `GET /gitlab/merge_requests/{}/{}/notes` |
| `get_mr_conflicts` | `GET /gitlab/merge_requests/{}/{}/conflicts` |
| `update_item_preferences` | `PUT /items/{type}/{id}/preferences` |
| `get_item_preferences` | `GET /items/preferences?type=` |
| `get_gitlab_todos` | `GET /gitlab/todos` |

Nota: Los Tauri commands existentes `get_issue_preferences` y `update_issue_preferences` se reemplazan por los genericos.

### Frontend: MR store (stores/merge_requests.ts)

Mismo patron que issues store actualizado:
- State: `mergeRequests`, `preferences`, `followedMRs`, `searchResults`, `activeFilter` (all/assigned/reviewer/followed), `currentUsername` (from GitLab API `/user`)
- Computed: `allMRs`, `scoredMRs`, `filteredMRs`, `groupedMRs`
- Actions: `fetchMRs`, `fetchPreferences`, `fetchFollowedMRs`, `searchMRs`, `updatePreference`, `followMR`, `unfollowMR`

### Frontend: MRDetailModal.vue

Componente `src/components/merge_requests/MRDetailModal.vue`:

- **Cabecera**: proyecto#iid, titulo, labels, estado (open/merged/closed)
- **Pipeline**: Badge con status (passed/failed/running/pending), link al pipeline
- **Conflictos**: Seccion destacada (rojo) si `has_conflicts=true`:
  - Lista de archivos en conflicto con rutas
  - Icono de warning
  - Texto "N archivos en conflicto"
- **Meta**: Asignados, reviewers, milestone, source branch → target branch
- **Score**: Automatico + manual editable (mismo patron IssueDetailModal)
- **Notas**: Ultimos N comentarios
- **Footer**: "Ir a GitLab"

### Frontend: MRsView.vue actualizacion

- Filter tabs: Todas | Asignados | Revisor | Seguidos
- Barra de busqueda con dropdown (mismo patron IssuesView)
- Click en fila → popup MRDetailModal
- MRTable.vue: emit `select`, indicador visual de seguidos

---

## Seccion 3: Dashboard configurable

### Modelo de datos

Reemplazar `dashboard_order: string[]` y `dashboard_spans: Record<string, [number, number]>` por:

```typescript
interface DashboardWidget {
  id: string;           // UUID unico
  type: string;         // 'jornada' | 'servicios' | 'horas_hoy' | 'progreso' | 'top_issues' | 'mrs_pendientes' | 'issues_proyecto' | 'horas_semana' | 'calendario' | 'todos'
  position: number;     // Orden en el grid
  span: [number, number]; // [cols, rows]
  config: Record<string, any>; // Config especifica por tipo
}

// En AppConfig:
dashboard_widgets: DashboardWidget[];
```

### Galeria de widgets disponibles

| Tipo | Nombre | Config editable |
|------|--------|-----------------|
| `jornada` | Jornada | — |
| `servicios` | Servicios | — |
| `horas_hoy` | Horas hoy | `target: number` (objetivo horas) |
| `progreso` | Progreso | `bars: string[]` (cuales mostrar: hoy/semana/mes) |
| `top_issues` | Top Issues | `count: number`, `project_filter?: string` |
| `mrs_pendientes` | MRs pendientes | `show_only_conflicts: bool`, `show_only_failed: bool` |
| `issues_proyecto` | Issues por proyecto | `project_filter?: string` |
| `horas_semana` | Horas por semana | `weeks: number` (cuantas semanas mostrar) |
| `calendario` | Calendario | — (requiere Google Calendar conectado) |
| `todos` | TODOs GitLab | `count: number` |

### UI de edicion

El boton "Editar dashboard" ya existe. En modo edicion:
- Cada widget muestra overlay con:
  - Boton × (eliminar widget)
  - Boton engranaje (abrir config del widget)
- Aparece boton "+ Anadir widget" que abre un popup/dropdown con la galeria
- Galeria muestra: icono + nombre + descripcion corta de cada widget disponible
- Al seleccionar un widget se anade al final del grid con config default

### Popup config de widget

`WidgetConfigModal.vue` — modal generico que recibe el `type` del widget y renderiza los controles apropiados:
- Usa un mapa de componentes: `{ top_issues: TopIssuesConfig, progreso: ProgresoConfig, ... }`
- Cada sub-componente tiene los inputs especificos
- Al guardar se actualiza `widget.config` y se persiste en AppConfig

### Componentes de widgets

Cada widget es un componente independiente en `src/components/dashboard/widgets/`:
- `JornadaWidget.vue` (existente, extraer de DashboardView)
- `ServiciosWidget.vue` (existente, extraer)
- `HorasHoyWidget.vue` (existente, extraer)
- `ProgresoWidget.vue` (existente, extraer)
- `TopIssuesWidget.vue` (existente, extraer)
- `MRsPendientesWidget.vue` (nuevo)
- `IssuesProyectoWidget.vue` (nuevo)
- `HorasSemanaWidget.vue` (nuevo)
- `CalendarioWidget.vue` (nuevo)
- `TodosWidget.vue` (nuevo)

Todos reciben `config` como prop y emiten `update:config` para cambios.

### Widget registry

`src/lib/widget-registry.ts`:
```typescript
export const WIDGET_REGISTRY: Record<string, WidgetDefinition> = {
  jornada: { name: 'Jornada', component: JornadaWidget, defaultSpan: [1,1], defaultConfig: {} },
  // ...
}
```

Centraliza la definicion de widgets, sus defaults y componentes.

---

## Seccion 4: Notificaciones

### Tabla SQLite: `notifications`

```sql
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    link TEXT,
    item_id INTEGER,
    read BOOLEAN DEFAULT FALSE,
    created_at TEXT DEFAULT (datetime('now'))
);
```

Tipos: `comment`, `pipeline_failed`, `mr_approved`, `changes_requested`, `conflict_detected`, `todo`

### Backend: NotificationService

`daemon/mimir_daemon/notifications.py`:

- Servicio que corre como background task en el server FastAPI via `asyncio.create_task` en el evento startup del app.
- Cada N minutos (configurable, default 5min) compara estado anterior vs nuevo:
  - Issues/MRs: compara `user_notes_count` para detectar nuevos comentarios
  - MRs: compara `pipeline_status` para detectar fallos
  - MRs: compara `has_conflicts` para detectar conflictos nuevos
  - MRs: compara estado de reviews (approved/changes_requested)
  - TODOs: compara lista actual vs anterior
- Almacena "snapshot" anterior en memoria para comparacion
- Nuevas notificaciones se insertan en la tabla `notifications`
- TTL configurable (default 7 dias), cleanup automatico en cada ciclo de comprobacion

### Backend: Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/notifications` | Notificaciones no leidas (o todas con `?all=true`) |
| PUT | `/notifications/{id}/read` | Marcar como leida |
| PUT | `/notifications/read-all` | Marcar todas como leidas |
| GET | `/notifications/count` | Conteo de no leidas |

### Frontend: NotificationBell

Componente `src/components/shared/NotificationBell.vue`:
- Icono campana en el header de la app (al lado del status "ACTIVO")
- Badge con numero de no leidas
- Click → dropdown con lista de notificaciones
- Cada notificacion: icono por tipo, titulo, timestamp relativo, link
- Click en notificacion → navega al item (issue/MR/todo)
- Boton "Marcar todas como leidas"
- Polling cada 30s para actualizar count

### Frontend: Desktop notifications

- Usar Tauri `notification` plugin para enviar notificaciones nativas del sistema
- Solo se envian si:
  - El toggle global esta activado
  - El toggle especifico del tipo esta activado
  - La app no tiene el foco (evitar duplicar con in-app)

### Frontend: Tray icon badge

- Actualizar el icono del tray con el conteo de no leidas
- En Linux: usar D-Bus `com.canonical.Unity.LauncherEntry` o similar si disponible
- Fallback: cambiar icono del tray a uno con punto rojo si hay no leidas

### Settings: NotificationsTab.vue

- Toggle global: "Notificaciones de escritorio"
- Intervalo de comprobacion: numero en minutos (default 5)
- TTL: dias de retencion (default 7)
- Toggles por tipo:
  - Nuevos comentarios en issues/MRs
  - Pipeline fallido
  - MR aprobado
  - Cambios solicitados en MR
  - Conflictos detectados
  - Nuevos TODOs

---

## Cambios transversales

### Migracion issues store a item_preferences

La issues store existente (`src/stores/issues.ts`) y `IssueDetailModal.vue` usan `api.getIssuePreferences()` y `api.updateIssuePreferences()`. Deben migrar a los endpoints genericos:
- `api.getItemPreferences('issue')` reemplaza `api.getIssuePreferences()`
- `api.updateItemPreferences('issue', issueId, data)` reemplaza `api.updateIssuePreferences(issueId, data)`
- `api.getFollowedIssues()` sin cambios (el backend internamente usa `item_preferences`)

### Tipo ItemPreference (types.ts)

Reemplaza `IssuePreference`:
```typescript
export interface ItemPreference {
  item_id: number;
  item_type: 'issue' | 'mr';
  manual_score: number;
  followed: boolean;
}
```

### api.ts — metodos nuevos y modificados

Nuevos:
- `searchMergeRequests(q: string)`
- `getFollowedMergeRequests()`
- `getMRNotes(projectId, mrIid, perPage)`
- `getMRConflicts(projectId, mrIid)`
- `getGitlabTodos()`
- `getNotifications(all?: boolean)`
- `markNotificationRead(id: number)`
- `markAllNotificationsRead()`
- `getNotificationCount()`

Reemplazados:
- `getIssuePreferences()` → `getItemPreferences(type: string)`
- `updateIssuePreferences(id, body)` → `updateItemPreferences(type: string, id: number, body)`

### lib.rs — registro de commands

Todos los Tauri commands nuevos deben registrarse en `src-tauri/src/lib.rs` en el `generate_handler!` macro. Los commands existentes `get_issue_preferences` y `update_issue_preferences` se eliminan.

### DashboardGrid refactor

El componente `DashboardGrid.vue` existente acepta `order: string[]` y `spans: Record<string, [number, number]>`. Debe refactorizarse para trabajar con el nuevo modelo `DashboardWidget[]` que incluye `type`, `position`, `span` y `config`. El `DashboardView.vue` existente tiene widgets hardcoded que se extraeran a componentes individuales.

### Identidad GitLab (username actual)

Para el filtro "Revisor" en MRs, se necesita conocer el username del usuario. Nuevo endpoint:
- `GET /gitlab/user` — proxy a GitLab API `GET /user`, retorna `{ username, name, id }`
- Se llama una vez al configurar GitLab y se cachea en el MR store

### Dependencias nuevas

| Paquete | Uso |
|---------|-----|
| `tauri-plugin-notification` (Cargo) | Notificaciones desktop nativas |

Nota: `marked` y `dompurify` ya estan instalados del sprint anterior.

---

## Resumen de archivos nuevos

| Archivo | Seccion |
|---------|---------|
| `src/components/settings/SettingGroup.vue` | 1 |
| `src/components/settings/SettingRow.vue` | 1 |
| `src/components/settings/CredentialField.vue` | 1 |
| `src/components/settings/GeneralTab.vue` | 1 |
| `src/components/settings/CaptureTab.vue` | 1 |
| `src/components/settings/OdooTab.vue` | 1 |
| `src/components/settings/GitLabTab.vue` | 1 |
| `src/components/settings/AITab.vue` | 1 |
| `src/components/settings/GoogleTab.vue` | 1 |
| `src/components/settings/ServicesTab.vue` | 1 |
| `src/components/settings/NotificationsTab.vue` | 4 |
| `src/components/merge_requests/MRDetailModal.vue` | 2 |
| `src/components/merge_requests/MRTable.vue` | 2 |
| `src/components/dashboard/widgets/*.vue` | 3 |
| `src/components/dashboard/WidgetConfigModal.vue` | 3 |
| `src/components/shared/NotificationBell.vue` | 4 |
| `src/lib/widget-registry.ts` | 3 |
| `daemon/mimir_daemon/notifications.py` | 4 |

## Resumen de tablas SQLite

| Tabla | Reemplaza | Seccion |
|-------|-----------|---------|
| `item_preferences` | `issue_preferences` | 2 |
| `notifications` | (nueva) | 4 |

## Resumen de endpoints nuevos

| Metodo | Ruta | Seccion |
|--------|------|---------|
| GET | `/gitlab/merge_requests/search?q=` | 2 |
| GET | `/gitlab/merge_requests/followed` | 2 |
| GET | `/gitlab/merge_requests/{}/{}/notes` | 2 |
| GET | `/gitlab/merge_requests/{}/{}/conflicts` | 2 |
| PUT | `/items/{type}/{id}/preferences` | 2 |
| GET | `/items/preferences?type=` | 2 |
| GET | `/gitlab/todos` | 2 |
| GET | `/notifications` | 4 |
| PUT | `/notifications/{id}/read` | 4 |
| PUT | `/notifications/read-all` | 4 |
| GET | `/notifications/count` | 4 |

# CLAUDE.md — Mimir

Asistente inteligente de imputación de horas para FactorLibre.
Guía de arquitectura y desarrollo para Claude Code CLI.
Lee este fichero completo antes de tocar cualquier fichero del proyecto.

---

## Principios fundamentales (no negociables)

- **Privacidad por diseño**: los datos de actividad NUNCA salen del ordenador del empleado. Solo salen las imputaciones que el empleado confirma explícitamente hacia el sistema de imputación (Odoo).
- **Tokens OAuth de fuentes externas**: se almacenan cifrados en el SQLite local del daemon. NUNCA llegan al backend.
- **El empleado siempre tiene la última palabra**: el sistema recomienda, nunca impone.
- **Patrón adaptador en todo**: IA, integración de imputación, notificaciones y fuentes externas son siempre adaptadores intercambiables. El MVP implementa uno; el resto son stubs o futuro.
- **Mejora continua**: cada corrección manual del empleado alimenta el motor de recomendación.

---

## Estructura del repositorio

```
/
├── daemon/                    # Proceso local Python (por empleado)
│   ├── main.py                # Entry point; arranca el event loop asyncio
│   ├── poller.py              # Bucle asyncio cada 30s; delega a platform/
│   ├── dbus_listener.py       # Bloqueo/desbloqueo de sesión (dbus-next; solo Linux)
│   ├── context_enricher.py    # /proc/{pid}/cwd, cmdline, ~/.claude/, ~/.ssh/config
│   ├── block_manager.py       # Herencia de contexto, contextos simultáneos, checkpoints
│   ├── sources_manager.py     # Ciclo de vida adaptadores de fuentes externas
│   ├── db.py                  # aiosqlite; esquema y queries del log local
│   ├── server.py              # uvicorn embebido; sirve PWA y API local
│   ├── tray.py                # pystray en ThreadPoolExecutor
│   ├── platform/
│   │   ├── __init__.py        # Factory: instancia monitor según sys.platform
│   │   ├── base.py            # Clase abstracta: get_active_windows(), get_session_events()
│   │   ├── linux.py           # v1.0: xdotool, D-Bus, /proc/{pid}/cwd
│   │   └── windows.py         # Stub post-MVP: interfaz definida, NotImplementedError
│   └── sources/
│       ├── base.py            # CalendarSource, VCSSource, CalendarEvent, Commit
│       ├── registry.py        # Adaptadores disponibles
│       ├── gcal.py            # Google Calendar API [MVP]
│       ├── outlook.py         # Microsoft Graph API [futuro]
│       ├── gitlab.py          # GitLab API + git local [MVP]
│       ├── github.py          # GitHub API + git local [futuro]
│       └── bitbucket.py       # Bitbucket API + git local [futuro]
│
├── backend/                   # FastAPI; preferencias, asociaciones, IA proxy, bot
│   ├── main.py                # App FastAPI; monta routers; arranca APScheduler
│   ├── auth.py                # JWT; validación Odoo XMLRPC (v11) / Google OAuth (v16)
│   ├── models.py              # SQLAlchemy o sql puro; esquema de tablas
│   ├── routers/
│   │   ├── preferences.py     # GET/PUT /preferences
│   │   ├── associations.py    # CRUD /associations
│   │   ├── decisions.py       # POST/GET /decisions
│   │   ├── maps.py            # /domain-map, /ssh-map
│   │   ├── org_config.py      # /org-config (admin)
│   │   ├── users.py           # /users (admin)
│   │   ├── ai.py              # POST /ai/describe, GET /ai/describe/{job_id}
│   │   ├── bot.py             # POST /bot/inbound
│   │   ├── departments.py     # /departments (admin)
│   │   └── manager.py         # /manager/team-hours
│   ├── ai/
│   │   ├── base.py            # AIClient (interfaz)
│   │   ├── prompt_builder.py  # Construcción de prompts (común a todos los adaptadores)
│   │   ├── registry.py        # Adaptadores disponibles
│   │   ├── gemini.py          # Gemini Pro/Flash [MVP]
│   │   ├── openai.py          # GPT-4o / GPT-4o Mini
│   │   ├── anthropic.py       # Claude Sonnet / Haiku
│   │   └── ollama.py          # Modelos locales
│   ├── integrations/
│   │   ├── base.py            # TimesheetClient (interfaz)
│   │   ├── registry.py
│   │   ├── odoo_v11.py        # Odoo v11 XMLRPC [MVP]
│   │   └── odoo_v16.py        # Odoo v16 REST [MVP]
│   └── notifications/
│       ├── base.py            # NotificationClient, NotificationMessage, InboundMessage
│       ├── registry.py
│       ├── slack.py           # Slack Bot API [MVP]
│       ├── teams.py           # [futuro]
│       ├── telegram.py        # [futuro]
│       └── email.py           # SMTP sin inbound [futuro]
│
├── pwa/                       # Vue 3 + Vite + vite-plugin-pwa
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── stores/            # Pinia
│   │   │   ├── blocks.js
│   │   │   ├── preferences.js
│   │   │   └── auth.js
│   │   ├── views/
│   │   │   ├── ReviewView.vue      # Tabla de bloques del día
│   │   │   ├── TimelineView.vue    # Línea de tiempo del día
│   │   │   ├── WeeklyView.vue      # Resumen semanal
│   │   │   ├── SettingsView.vue    # Preferencias personales
│   │   │   └── AdminView.vue       # Solo rol admin
│   │   └── components/
│   │       ├── BlockRow.vue        # Fila de bloque en tabla Revisar
│   │       ├── ConfidenceBadge.vue
│   │       ├── SimultaneousContext.vue  # Sliders para tiempo distribuido
│   │       └── SyncStatusBadge.vue
│   ├── vite.config.js
│   └── public/
│       └── manifest.json      # PWA manifest
│
└── CLAUDE.md                  # Este fichero
```

---

## Componente 1: Daemon local (Python)

### Stack

| Módulo | Librería | Razón |
|--------|----------|-------|
| Concurrencia | `asyncio` | D-Bus es nativo async; no bloquea el event loop |
| SQLite local | `aiosqlite` | Driver async sobre sqlite3 |
| D-Bus | `dbus-next` | Librería moderna; construida sobre asyncio |
| Servidor PWA | `uvicorn` + `fastapi` | Embebido en el mismo proceso |
| Tray icon | `pystray` | `ThreadPoolExecutor`; comunica con event loop via `asyncio.run_coroutine_threadsafe` |
| Empaquetado | `PyInstaller` | Binario autocontenido para Fleet |

### Comportamiento del poller (`poller.py`)

- Ciclo asyncio cada **30 segundos** (configurable por empleado; mínimo 15s).
- Delega la captura al módulo `platform/` (nunca llama `xdotool` directamente desde aquí).
- Resultado de cada poll → `block_manager.py` para decidir si extender el bloque activo o crear uno nuevo.

### Herencia de contexto (`block_manager.py`)

- Las decisiones de herencia se toman **en memoria**, no en DB.
- Cada **5 polls (~2.5 min)** se persiste un checkpoint del bloque activo en SQLite.
- Pérdida máxima ante caída del daemon: 2.5 minutos de contexto.
- **Umbral de herencia** (`inherit_threshold`): si la interrupción dura menos que el umbral (default 15 min), se extiende el bloque; si lo supera, se crea uno nuevo.
- **Contextos simultáneos**: cuando dos señales se solapan, se guardan en el mismo bloque con su distribución de tiempo. En la PWA aparecen como sliders al hacer clic en el bloque.

### Enriquecimiento de contexto (`context_enricher.py`)

- `/proc/{pid}/cwd` del terminal con foco → repositorio activo.
- `cmdline` → detección de sesión SSH activa.
- Parseo de `~/.ssh/config` → resolución alias SSH → hostname real.
- Lectura de `~/.claude/` → sesiones de Claude Code CLI activas.

### SQLite local — esquema

```sql
CREATE TABLE blocks (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at      TEXT NOT NULL,
  ended_at        TEXT,
  app             TEXT,
  title           TEXT,
  url             TEXT,
  cwd             TEXT,
  ssh_host        TEXT,
  source          TEXT DEFAULT 'auto',    -- 'auto' | 'manual' | 'claude_code'
  status          TEXT DEFAULT 'open',   -- 'open' | 'closed' | 'locked_out'
  sources_detail  TEXT,                  -- JSON; metadatos por fuente
  checkpoint_at   TEXT,
  sync_status     TEXT DEFAULT 'pending', -- 'pending' | 'sent' | 'error'
  sync_error      TEXT,
  remote_id       TEXT
);

CREATE INDEX idx_blocks_started_at ON blocks(started_at);
CREATE INDEX idx_blocks_status     ON blocks(status);

-- Caché de eventos de Calendar (evita llamadas repetidas)
CREATE TABLE calendar_events_cache (
  event_id     TEXT NOT NULL,
  adapter      TEXT NOT NULL,    -- 'gcal' | 'outlook'
  title        TEXT NOT NULL,
  start_at     TEXT NOT NULL,
  end_at       TEXT NOT NULL,
  duration_min INTEGER NOT NULL,
  is_recurring BOOLEAN NOT NULL DEFAULT FALSE,
  meet_url     TEXT,
  fetched_at   TEXT NOT NULL,
  PRIMARY KEY (event_id, adapter)
);

-- Tokens OAuth de fuentes externas (NUNCA salen del ordenador)
CREATE TABLE source_tokens (
  adapter      TEXT PRIMARY KEY,   -- 'gcal' | 'gitlab' | 'github' | etc.
  access_token TEXT NOT NULL,      -- cifrado en reposo
  refresh_token TEXT,
  expires_at   TEXT,
  scopes       TEXT,
  needs_reauth BOOLEAN DEFAULT FALSE
);

-- Caché de preferencias del backend (fallback sin conexión)
CREATE TABLE preferences_cache (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  cached_at  TEXT NOT NULL
);
```

### Fuentes externas (`sources_manager.py` + `sources/`)

- **Google Calendar (MVP)**: descarga eventos del día al arrancar; refresco cada 2h.
- **GitLab (MVP)**: git log local como primaria; GitLab API como secundaria.
- Al cerrar cada bloque, `sources_manager` enriquece `sources_detail` con eventos solapados y commits del período.
- Token OAuth caducado → `needs_reauth = TRUE` en `source_tokens` → aviso en tray icon y banner en PWA.
- Refresco de token: comprobar `expires_at` antes de cada llamada; refrescar si quedan < 5 minutos.

### Autenticación del daemon

- Al arrancar, obtiene un JWT del backend (largo plazo: 30 días sliding refresh).
- Dual-token: `access_token` (24h) + `refresh_token` (30 días), ambos almacenados cifrados en `preferences_cache`.
- El módulo `auth_client` abstrae v11 (XMLRPC) vs v16 (Google OAuth). El resto del daemon no sabe qué versión está activa.

---

## Componente 2: PWA (Vue 3 + Vite)

### Stack

- **Framework**: Vue 3 + Vite + `vite-plugin-pwa` + Workbox
- **Estado**: Pinia
- **Estilo**: FactorLibre brand tokens (ver sección de Branding)
- **Instalación**: Chrome/Edge; layout de escritorio con sidebar fija

### Vistas

| Vista | Ruta | Descripción |
|-------|------|-------------|
| `ReviewView` | `/` o `/?date=YYYY-MM-DD&view=review` | Tabla de bloques del día; revisar y confirmar |
| `TimelineView` | `/timeline` | Línea de tiempo del día; detectar huecos |
| `WeeklyView` | `/?week=YYYY-Www&view=weekly` | Resumen semanal |
| `SettingsView` | `/settings` | Preferencias personales |
| `AdminView` | `/admin` | Solo rol `admin` |

### Deep links

```
http://localhost:{PORT}/?date=YYYY-MM-DD&view=review   ← aviso diario del bot
http://localhost:{PORT}/?week=YYYY-Www&view=weekly     ← aviso semanal del bot
```
Sin parámetros → vista del día actual.

### Comportamientos clave de la vista Revisar

- **Tabla horizontal**: columnas `Hora inicio`, `Hora fin`, `App/Fuente`, `Descripción IA` (editable inline), `Proyecto`, `Tarea`, `Estado`.
- **Indicador de confianza**: badge visual por bloque. < 30% → etiqueta "Requiere atención" (color ámbar).
- **Descripciones IA lazy**: se solicitan bloque a bloque conforme entran en el viewport. Spinner mientras se genera; campo editable cuando llega. No bloquea la tabla.
- **Contextos simultáneos**: al hacer clic en un bloque que tiene solapamiento, aparece un panel lateral con sliders para distribuir el tiempo entre ambos contextos. Los sliders tienen inputs numéricos sincronizados. No siempre visibles — solo al hacer clic.
- **Estados de sincronización**:
  - `pending` → sin badge especial
  - `sent` → badge verde "✅ Enviado"
  - `error` → badge ámbar "⚠️ Error" con tooltip del mensaje; botón "Reintentar"
- **Backlog de días pasados**: selector de fecha en el header. Dos estados distintos:
  - **Log vacío** (daemon corrió pero no hay actividad): mensaje "Sin actividad registrada este día"
  - **Log expirado** (fuera del período de retención): "Datos no disponibles — consulta Odoo directamente"
- **Auto-balance** (pendiente de especificación detallada): configuración de modos `manual` / `on_confirm` / `always_active` para distribución automática de horas entre bloques del día.

### Autenticación PWA

- Flujo OAuth estándar del navegador (redirect + callback).
- JWT en memoria del navegador (no localStorage); expira al cerrar el navegador.
- Independiente del JWT del daemon.

---

## Componente 3: Backend (FastAPI + SQLite)

### Propósito

Almacena solo conocimiento reutilizable (preferencias, asociaciones, decisiones aprendidas). **No almacena datos de actividad**.

### Despliegue

- Servidor propio de FactorLibre (red interna o VPN). Requiere TLS.
- Política de backups de SQLite a definir en Fase 5.

### Esquema de datos

```sql
CREATE TABLE users (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  email       TEXT UNIQUE NOT NULL,
  role        TEXT DEFAULT 'employee',  -- 'employee' | 'manager' | 'admin'
  created_at  TEXT NOT NULL,
  archived_at TEXT
);

-- Asociaciones Calendar → Proyecto/Tarea
CREATE TABLE calendar_associations (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id           INTEGER REFERENCES users(id),
  scope             TEXT DEFAULT 'personal',  -- 'personal' | 'global'
  calendar_event_id TEXT NOT NULL,
  project_id        TEXT NOT NULL,
  task_id           TEXT,
  description       TEXT,           -- si existe, omite llamada a IA
  override_instance TEXT,           -- ID instancia específica (sobreescribe global)
  created_at        TEXT NOT NULL
);

-- Historial de decisiones (motor de recomendación)
CREATE TABLE decision_history (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id      INTEGER REFERENCES users(id),
  signal_type  TEXT NOT NULL,   -- 'gitlab_repo' | 'ssh_host' | 'domain' | 'app'
  signal_value TEXT NOT NULL,
  project_id   TEXT NOT NULL,
  task_id      TEXT,
  confidence   REAL DEFAULT 1.0,
  last_seen    TEXT NOT NULL
);

CREATE TABLE domain_map (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER REFERENCES users(id),
  domain     TEXT NOT NULL,
  label      TEXT NOT NULL,
  project_id TEXT
);

CREATE TABLE ssh_map (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER REFERENCES users(id),
  ssh_alias  TEXT NOT NULL,
  project_id TEXT NOT NULL
);

CREATE TABLE org_config (
  id         INTEGER PRIMARY KEY,
  updated_at TEXT NOT NULL,
  updated_by INTEGER REFERENCES users(id),
  data       TEXT NOT NULL  -- JSON blob (ver estructura abajo)
);

CREATE TABLE preferences (
  user_id    INTEGER PRIMARY KEY REFERENCES users(id),
  updated_at TEXT NOT NULL,
  data       TEXT NOT NULL  -- JSON blob (ver estructura abajo)
);

CREATE TABLE description_cache (
  hash        TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  created_at  TEXT NOT NULL,
  hits        INTEGER DEFAULT 1
);

CREATE TABLE notification_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL REFERENCES users(id),
  job_type      TEXT NOT NULL,  -- 'daily' | 'weekly' | 'ondemand' | 'team'
  triggered_at  TEXT NOT NULL,
  period_start  TEXT NOT NULL,
  period_end    TEXT NOT NULL,
  hours_actual  REAL,
  hours_target  REAL,
  deficit       REAL,
  sent          BOOLEAN DEFAULT FALSE,
  error         TEXT
);

CREATE TABLE notification_users (
  user_id      INTEGER PRIMARY KEY REFERENCES users(id),
  adapter      TEXT NOT NULL,
  platform_ref TEXT NOT NULL,
  resolved_at  TEXT NOT NULL
);

CREATE TABLE departments (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE department_members (
  department_id INTEGER REFERENCES departments(id),
  user_id       INTEGER REFERENCES users(id),
  is_leader     BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (department_id, user_id)
);
```

### JSON `preferences.data`

```json
{
  "profile": {
    "name": "Jesús Lorenzo",
    "type": "technical",
    "custom_desc": ""
  },
  "schedule": { "L": 8.5, "M": 8.5, "X": 8.5, "J": 8.5, "V": 6 },
  "daemon": {
    "polling_interval": 30,
    "inherit_threshold": 15,
    "retention_days": 30,
    "excluded_apps": ["Spotify"]
  },
  "sources": {
    "vscode": true, "gitlab": true, "slack": true,
    "meet": true, "calendar": true, "gmail": true
  },
  "ai": { "show_raw": true },
  "notifications": {
    "daily": { "enabled": true, "time": "17:30" },
    "weekly": { "enabled": false, "weekday": "friday", "time": "16:00" },
    "positive_confirmation": false
  },
  "integration": {
    "sync_on_confirm": false,
    "extra_fields": { "employee_id": "42" }
  }
}
```

### JSON `org_config.data`

```json
{
  "integration": {
    "adapter": "odoo_v16",
    "config": { "url": "https://odoo.factorlibre.com", "api_key": "***" },
    "extra_fields": [{ "key": "employee_id", "required": true }]
  },
  "ai": {
    "adapter": "gemini",
    "config": { "api_key": "***", "model": "gemini-2.0-flash" }
  },
  "notification": {
    "adapter": "slack",
    "config": { "bot_token": "xoxb-***", "signing_secret": "***" }
  },
  "defaults": {
    "polling_interval": 30,
    "retention_days_max": 90,
    "inherit_threshold": 15
  }
}
```

### Endpoints REST

```
GET  /preferences
PUT  /preferences

GET  /associations
POST /associations              (scope 'global' requiere manager o admin)
DEL  /associations/{id}

POST /decisions
GET  /decisions?signal={value}

GET  /domain-map
PUT  /domain-map

GET  /ssh-map
PUT  /ssh-map

GET  /org-config                (admin)
PUT  /org-config                (admin)

GET  /users                     (admin)
PUT  /users/{id}/role           (admin)

POST /ai/describe
GET  /ai/describe/{job_id}

POST /bot/inbound               (webhook Slack)
GET  /departments               (admin)
POST /departments               (admin)
PUT  /departments/{id}/members  (admin)
GET  /manager/team-hours?week={iso_week}
GET  /notification-log?user_id={id}  (admin)
```

### Roles

| Rol | Permisos |
|-----|----------|
| `employee` | Configuración personal, asociaciones personales |
| `manager` | Todo de employee + asociaciones globales |
| `admin` | Todo de manager + org config, usuarios, departamentos |

> `is_leader` en `department_members` es **independiente** del rol `manager`. Un `employee` puede ser líder de departamento (visibilidad de equipo en el bot) sin permisos de manager en la PWA.

---

## Componente 4: Motor de recomendación

### Algoritmo

- **Frecuencia ponderada con decaimiento exponencial**: `score = Σ e^(-λ·Δt)` donde λ = 0.05 (~14 días de semivida).
- **Asociaciones de manager** (`scope = 'global'`): peso fijo 0.5, **no decaen**.
- **Decisiones personales**: sí decaen con λ = 0.05.
- **Umbral "requiere atención"**: < 30% confianza → badge ámbar en la PWA.

### Precedencia de señales Calendar

1. Asociación personal del empleado → usar proyecto/tarea. Si tiene `description` → skip IA.
2. Asociación global del manager → sugerencia con confianza alta. Si tiene `description` → skip IA.
3. Sin asociación → resto de señales + llamada a proxy IA.

### Señales y pesos relativos

| Señal | Peso |
|-------|------|
| Asociación Calendar personal | Máximo |
| Asociación Calendar global (manager) | Alto |
| Historial reuniones recurrentes | Alto |
| Commits GitLab | Medio |
| Issues GitLab | Medio |
| CWD terminal / Claude Code log | Medio |
| Alias SSH + mapa proyectos | Medio |
| Ventana activa (app/título) | Medio |
| Sin contexto claro | Pregunta |

---

## Componente 5: Proxy IA centralizado

### Flujo

```
PWA (bloque entra en viewport)
  → daemon local
    → POST /ai/describe
        ¿hash en caché?
          Sí → devuelve descripción inmediata
          No → encola job
               → respeta RPM del proveedor
               → llama al AI adapter
               → guarda en description_cache
               → devuelve descripción
```

### Clave de caché

Hash de señales semánticas del bloque (`calendar_event_id`, `gitlab_repo+commits`, `cwd`, `ssh_host`) + `profile_type` del usuario. El timestamp NO forma parte de la clave.

### Output esperado

Descripción de ~80 caracteres en una línea. Ejemplos por perfil:

| Bloque | Perfil técnico | Perfil funcional |
|--------|---------------|-----------------|
| Daily standup | `Daily standup — coordinación y seguimiento de sprint` | `Reunión diaria de equipo — revisión de estado del sprint` |
| 3 commits en odoo-v16/account | `Desarrollo módulo account: fix VAT multicurrency (3 commits)` | `SIN_CONTEXTO` |
| Slack #cliente-b + Gmail | `Comunicación cliente B — soporte y seguimiento` | `Gestión cliente B — soporte y coordinación` |

Si no hay señales → devuelve `SIN_CONTEXTO`. La confianza se fija a 0%. El empleado lo rellena manualmente.

### Interfaz del adaptador de IA

```python
class AIClient:
    async def generate_description(
        self,
        system_prompt: str,
        user_message: str,
        max_chars: int = 80
    ) -> str  # devuelve descripción o 'SIN_CONTEXTO'
```

---

## Componente 6: Capa de integración (TimesheetClient)

### Interfaz

```python
class TimesheetClient:
    async def get_projects(self) -> list[Project]
    async def get_tasks(self, project_id: str) -> list[Task]
    async def create_entry(self, entry: TimesheetEntry) -> str  # devuelve remote_id
    async def update_entry(self, remote_id: str, entry: TimesheetEntry) -> None
    async def get_entries(self, date_range: DateRange, employee_id: str) -> list[TimesheetEntry]
```

- `extra_fields`: cada adaptador declara sus campos adicionales requeridos.
- Wizard de onboarding en primera ejecución para configurar el adaptador activo.

### Ciclo de vida de `sync_status`

```
bloque confirmado     → sync_status = 'pending'
envío exitoso         → sync_status = 'sent', remote_id = {id}
error de envío        → sync_status = 'error', sync_error = {mensaje}
reintento exitoso     → sync_status = 'sent', sync_error = NULL
editado tras enviarse → sync_status = 'pending', remote_id conservado
                        (el adaptador hace UPDATE en lugar de CREATE)
```

### Modos de envío

| Modo | `sync_on_confirm` | Comportamiento |
|------|------------------|----------------|
| Batch | `false` | El empleado confirma y después pulsa "Enviar X bloques" |
| Auto | `true` | Cada confirmación envía inmediatamente a Odoo |

---

## Componente 7: Bot de notificaciones

### Jobs (APScheduler `AsyncIOScheduler` embebido en FastAPI)

| Job | Trigger | Comprueba |
|-----|---------|-----------|
| `daily_check:{user_id}` | Cron L–V a la hora configurada | Horas hoy vs. objetivo diario |
| `weekly_check:{user_id}` | Cron al día y hora configurados | Horas semana vs. objetivo semanal |

- Los jobs son dinámicos: se actualizan en tiempo real cuando el empleado cambia su configuración.
- El scheduler usa el adaptador de integración con credenciales org-level + `employee_id` del usuario. No necesita credenciales individuales.
- `resolve_user(email)` se llama en el primer envío; el resultado se cachea en `notification_users`.

### Comandos slash

- `/timesheet status` → estado desde inicio de semana hasta ahora
- `/timesheet equipo` → vista de equipo (requiere `is_leader = true`; si lidera varios departamentos, muestra selector)

### Interfaz del adaptador

```python
class NotificationClient:
    async def send_message(self, user_ref: str, message: NotificationMessage) -> bool
    async def resolve_user(self, email: str) -> str | None
    async def handle_inbound(self, payload: dict) -> InboundMessage
```

---

## Branding FactorLibre

```js
const FL = {
  red:       "#cb1b21",
  redDark:   "#a51519",
  black:     "#2d2d33",
  aegean:    "#4d5a70",
  grayBlue:  "#a2b0b4",
  gray:      "#a3a3a3",
  grayLight: "#d8d8d8",
  // Dark mode UI
  bg:        "#1e2029",
  surface:   "#2d2d33",
  surface2:  "#383840",
  border:    "#3d3d46",
  text:      "#f0f0f0",
  textMuted: "#a2b0b4",
}
const FONT = "'Poppins', sans-serif"
```

---

## Fases de desarrollo

| Fase | Descripción | Duración estimada |
|------|-------------|-------------------|
| F1 | Daemon base (poller, block_manager, SQLite, tray) | 3 semanas |
| F2 | Integraciones (Odoo + Google Calendar + GitLab) | 3 semanas |
| F3 | PWA MVP (vista Revisar, confirmación, envío a Odoo) | 5 semanas |
| F4 | Configuración + resúmenes | 2 semanas (paralelo con F5 y F7) |
| F5 | Backend de preferencias (FastAPI, SQLite, JWT, auth) | 3 semanas (paralelo con F4 y F7) |
| F6 | Motor de recomendación (decay, señales, proxy IA) | 4 semanas |
| F7 | Bot de Slack (scheduler, comandos, vista equipo) | 2 semanas (paralelo con F4 y F5) |

**Primer valor tangible para el equipo: al finalizar F3 (semana ~11).**

---

## Convenciones y restricciones técnicas

- **Python**: mínimo 3.11. Usar `asyncio` en todo el daemon; nada de threading salvo `pystray`.
- **Vue**: versión 3 con Composition API (`<script setup>`). No usar Options API.
- **Pinia**: un store por dominio (`blocks`, `preferences`, `auth`).
- **Backend**: FastAPI con tipo estricto (Pydantic v2). Ningún endpoint devuelve datos sin validación de esquema.
- **SQLite local**: nunca hacer queries sobre campos dentro de JSON blobs. Los blobs se leen y escriben como bloque completo.
- **Tokens OAuth**: NUNCA pasar por el backend. Si algún módulo intenta enviar un token OAuth al backend, es un bug crítico de privacidad.
- **Adaptadores**: todos los adaptadores (IA, integración, notificación, fuentes) implementan la interfaz base de su familia. Nunca usar una implementación concreta directamente desde fuera del módulo.
- **Tests**: para cada adaptador, incluir al menos un test de integración con mock del servicio externo.
- **Distribución**: el binario `PyInstaller` es el artefacto de distribución. No depender de Python instalado en el equipo del empleado.
- **Cross-platform**: toda la captura OS-specific va en `platform/`. Si se añade código OS-specific fuera de `platform/`, es un bug de arquitectura.
- **Cuando arranques en Fase 1**: implementa primero `platform/base.py` y `platform/linux.py`. Prepara `platform/windows.py` como stub con `NotImplementedError`. El resto del daemon solo usa `platform/__init__.py`.

---

## Casos esquina a tener en cuenta durante la implementación

- **Caída del daemon**: al arrancar, leer el último bloque `open` en SQLite y decidir si cerrarlo (si el timestamp es de hace más de 1h) o continuar (si es reciente).
- **Pérdida de conexión con el backend**: preferencias cacheadas en `preferences_cache` del SQLite local. El daemon sigue funcionando.
- **Token OAuth revocado**: `needs_reauth = TRUE` en `source_tokens`; badge en tray icon + banner en PWA; el resto del sistema sigue funcionando.
- **Repo git sin remote**: git log local igualmente; no llamar a API VCS.
- **Bloqueo de pantalla**: D-Bus detecta evento → `status = 'locked_out'` en el bloque activo. Desbloqueo → nuevo bloque.
- **Trabajo fuera de horario**: el daemon sigue corriendo. No hay restricción horaria.
- **Día ya confirmado**: puede reabrirse para editar; genera UPDATE en Odoo via adaptador (usando `remote_id`).
- **Cambio de ordenador**: preferencias y reglas en el backend; el nuevo equipo las recibe al sincronizar en el primer arranque.
- **Migración Odoo v11 → v16**: el admin cambia el adaptador activo en org_config. El resto del sistema no cambia.
- **Líder en varios departamentos**: el comando `/timesheet equipo` muestra selector de departamento.

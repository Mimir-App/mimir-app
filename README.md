# Mimir

Asistente inteligente de imputacion de horas. Captura automaticamente la actividad del escritorio, sugiere descripciones con IA, y permite imputar horas a Odoo.

## Funcionalidades

- **Captura automatica de actividad** — Senales cada 30s: ventana activa, proyecto git, idle time, audio/reuniones
- **Soporte X11 y Wayland** — Deteccion automatica, extension GNOME Shell para Wayland
- **Bloques inteligentes** — Agrupacion determinista por proyecto git, dominio del navegador o app
- **Revision del dia** — Edita, confirma, parte/fusiona bloques, vista de senales crudas
- **Descripciones con IA** — Genera descripciones automaticas con Gemini, Claude u OpenAI
- **Integracion Odoo** — Soporte v11 (XMLRPC) y v16+ (REST), timesheets y fichaje de asistencia
- **Integracion GitLab** — Issues y merge requests con scoring y priorizacion
- **Integracion Google Calendar** — Deteccion automatica de reuniones via OAuth2
- **Parte de horas** — Vista de timesheets agrupable por fecha, semana, proyecto o tarea
- **Dashboard personalizable** — Widgets arrastrables y redimensionables con progreso dia/semana/mes
- **Fichaje de jornada** — Check-in/check-out conectado a hr.attendance de Odoo
- **Temas** — Oscuro y claro con branding FactorLibre, zoom configurable
- **Permisos de captura** — Controla que datos se recopilan (ventana, git, idle, audio, SSH)

## Stack

| Componente | Tecnologia |
|---|---|
| Frontend | Tauri 2 + Vue 3 + TypeScript + Vite |
| Backend desktop | Rust (Tauri commands, keyring) |
| Capture daemon | Python 3.10+ (asyncio, poller, tray) |
| Server daemon | Python 3.10+ (FastAPI, uvicorn) |
| Base de datos | SQLite (compartida, WAL mode) |

## Arquitectura

```
Frontend (Vue 3 + Tauri)
    |
    | invoke() -> Tauri commands (Rust)
    |                 |
    |                 | HTTP
    |                 v
    |         mimir-server :9477
    |         [child process de Tauri]
    |                 |
    |                 | SQLite compartida
    |                 |
    |         mimir-capture :9476
    |         [systemd user service]
    |                 |
    |         Poller -> Platform (xdotool / GNOME D-Bus)
    |                 |
    |         SignalAggregator -> SQLite (signals + blocks)
```

**mimir-capture** corre siempre como servicio del sistema, capturando senales en background. **mimir-server** se lanza automaticamente al abrir la app y se cierra al cerrarla.

## Instalacion

### Desde paquetes .deb

```bash
# 1. Instalar la app (incluye mimir-server)
sudo apt install ./mimir_0.3.0_amd64.deb

# 2. Opcional: instalar captura automatica
sudo apt install ./mimir-capture_0.3.0_amd64.deb
systemctl --user daemon-reload
systemctl --user enable --now mimir-capture

# 3. Si usas Wayland (GNOME), activar la extension
gnome-extensions enable mimir-window-tracker@mimir.app
# (cerrar sesion y volver a entrar)
```

### Desde codigo fuente

```bash
git clone https://github.com/Mimir-App/mimir-app.git
cd mimir-app

# Frontend
npm install

# Daemon Python
cd daemon
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Desarrollo
npm run tauri dev
```

## Build

```bash
bash scripts/build.sh              # Todo (capture + server + app)
bash scripts/build.sh deb          # Paquetes .deb unificados
bash scripts/build.sh capture      # Solo mimir-capture
bash scripts/build.sh server       # Solo mimir-server
bash scripts/build.sh daemon       # Ambos daemons + instalador
bash scripts/build.sh app          # Solo app Tauri (.deb + .AppImage)
```

## Configuracion

Toda la configuracion se gestiona desde **Ajustes** dentro de la app:

| Tab | Que configura |
|---|---|
| General | Tema, formatos de hora/fecha/timezone, escala interfaz, objetivos semanales |
| Captura | Permisos: ventana activa, git, idle time, audio/reuniones, SSH |
| Odoo | URL, version, credenciales, test de conexion |
| GitLab | URL, token, test de conexion |
| IA | Proveedor (Gemini/Claude/OpenAI), API key, perfil, contexto |
| Google | OAuth2 login, Calendar, estado de servicios Google |
| Servicios | Estado de capture/server, iniciar/detener, integraciones activas |

## Tests

```bash
cd daemon
.venv/bin/python -m pytest tests/ -v    # ~142 tests
```

```bash
npx vue-tsc --noEmit                    # TypeScript check
cd src-tauri && cargo check             # Rust check
```

## Verificar que funciona

```bash
# Servicio de captura
systemctl --user status mimir-capture
curl http://127.0.0.1:9476/health
curl http://127.0.0.1:9476/status    # Incluye backend (x11/wayland)

# Servidor API (cuando la app esta abierta)
curl http://127.0.0.1:9477/health
```

## Estructura del proyecto

```
src/                              # Frontend Vue 3 + TypeScript
  components/
    shared/                       # IntegrationCard, ModalDialog, CustomSelect, etc.
    settings/                     # (pendiente) tabs de Settings separados
    blocks/                       # BlockTable, BlockRow, BlockEditor
  composables/                    # useFormatting, useSortable, usePolling, etc.
  stores/                         # blocks (+ signals), config, daemon, issues, etc.
  views/                          # DashboardView, ReviewDayView, SettingsView, etc.
src-tauri/                        # Backend Rust (Tauri 2)
daemon/                           # Daemon Python
  mimir_daemon/
    capture.py                    # Entry point capture (systemd)
    api_server.py                 # Entry point server (Tauri child)
    server.py                     # FastAPI routes
    signal_aggregator.py          # Agrupacion de senales a bloques
    poller.py                     # Ciclo de polling
    integrations/                 # Odoo v11, v16, Google Calendar
    sources/                      # GitLab
    ai/                           # Gemini, Claude, OpenAI
    platform/                     # X11 (xdotool), Wayland (GNOME D-Bus), idle, audio
      gnome_extension/            # Extension GNOME Shell para Wayland
  tests/                          # ~142 tests
scripts/
  build.sh                        # Build unificado + .deb packaging
packaging/                        # Templates .deb para mimir-capture
.github/
  workflows/release.yml           # CI: build + release en tag v*
```

## CI/CD

GitHub Actions: al hacer push de un tag `v*`, se construyen los .deb y AppImage y se publican como release.

```bash
git tag v0.3.0
git push origin v0.3.0
```

## Licencia

Propiedad de Jesus Lorenzo Limon.

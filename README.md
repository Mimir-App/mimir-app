# Mimir

Asistente inteligente de imputacion de horas para [FactorLibre](https://factorlibre.com). Captura automaticamente la actividad del escritorio, sugiere descripciones con IA, y permite imputar horas a Odoo.

## Funcionalidades

- **Captura automatica de actividad** — Detecta ventana activa, proyecto git, rama y ultimo commit cada 30 segundos
- **Revision del dia** — Edita, confirma y envia bloques de actividad a Odoo en batch
- **Descripciones con IA** — Genera descripciones automaticas con Gemini, Claude u OpenAI (configurable)
- **Integracion Odoo** — Soporte v11 (XMLRPC) y v16+ (REST/OAuth), timesheets y fichaje de asistencia
- **Integracion GitLab** — Issues y merge requests con scoring y priorizacion
- **Parte de horas** — Vista de timesheets agrupable por fecha, semana, proyecto o tarea
- **Dashboard personalizable** — Widgets arrastrables y redimensionables con progreso dia/semana/mes
- **Fichaje de jornada** — Check-in/check-out conectado a hr.attendance de Odoo
- **Temas** — Oscuro y claro con branding FactorLibre, zoom configurable

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
    |         Poller -> Platform (xdotool/D-Bus)
    |                 |
    |         BlockManager -> SQLite
```

**mimir-capture** corre siempre como servicio del sistema, capturando actividad en background. **mimir-server** se lanza automaticamente al abrir la app y se cierra al cerrarla.

## Instalacion

### Requisitos

- Linux (Ubuntu 22.04+)
- `xdotool` (captura de ventana activa)
- `libwebkit2gtk-4.1` (Tauri)

### Desde binarios

```bash
# 1. Instalar la app de escritorio
sudo dpkg -i mimir_0.2.0_amd64.deb
# o usar el AppImage:
chmod +x mimir_0.2.0_amd64.AppImage

# 2. Instalar el servicio de captura
bash install-daemon.sh
```

### Desde codigo fuente

```bash
# Clonar
git clone https://github.com/factorlibre/mimir-app.git
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
bash scripts/build.sh capture      # Solo mimir-capture
bash scripts/build.sh server       # Solo mimir-server
bash scripts/build.sh daemon       # Ambos daemons + instalador
bash scripts/build.sh app          # Solo app Tauri (.deb + .AppImage)
```

## Configuracion

Toda la configuracion se gestiona desde **Ajustes** dentro de la app:

| Tab | Que configura |
|---|---|
| General | Tema, formatos de hora/fecha, escala interfaz, objetivos semanales |
| Odoo | URL, version, credenciales, test de conexion |
| GitLab | URL, token, test de conexion |
| IA | Proveedor (Gemini/Claude/OpenAI), API key, perfil, contexto |
| Servicios | Estado de capture/server, iniciar/detener, integraciones activas |

## Tests

```bash
cd daemon
.venv/bin/python -m pytest tests/ -v    # ~110 tests
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

# Servidor API (cuando la app esta abierta)
curl http://127.0.0.1:9477/health
```

## Estructura del proyecto

```
src/                          # Frontend Vue 3 + TypeScript
  components/shared/          # Componentes reutilizables
  composables/                # Logica compartida
  stores/                     # Pinia stores
  views/                      # Vistas de la app
src-tauri/                    # Backend Rust (Tauri 2)
daemon/                       # Daemon Python
  mimir_daemon/
    capture.py                # Entry point capture (systemd)
    api_server.py             # Entry point server (Tauri child)
    server.py                 # FastAPI routes
    block_manager.py          # Gestion de bloques
    integrations/             # Odoo v11, v16
    sources/                  # GitLab
    ai/                       # Providers IA
    platform/                 # OS-specific (xdotool, D-Bus)
  tests/                      # ~110 tests
scripts/
  build.sh                    # Build unificado
docs/plans/                   # Documentos de diseno
```

## Licencia

Propiedad de FactorLibre.

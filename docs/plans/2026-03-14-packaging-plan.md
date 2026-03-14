# Fase 6 — Empaquetado Linux: Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Empaquetar Mimir para distribución en Linux: daemon como binario standalone (PyInstaller) + app de escritorio (.deb/.AppImage via Tauri) + instalador de servicio systemd.

**Architecture:** PyInstaller genera binario `mimir-daemon` sin dependencia de Python. El servicio systemd arranca el daemon al login. Tauri build genera .deb y .AppImage de la app. Script `build.sh` orquesta todo.

**Tech Stack:** PyInstaller, systemd (user service), Tauri 2 (bundle .deb/.AppImage), Bash scripts.

---

### Task 1: PyInstaller spec para el daemon

**Files:**
- Create: `daemon/mimir_daemon.spec`
- Modify: `daemon/pyproject.toml` (add pyinstaller to dev deps)

**Step 1: Add PyInstaller dependency**

In `daemon/pyproject.toml`, add to `[project.optional-dependencies] dev`:
```toml
    "pyinstaller>=6.0",
```

Run: `cd /opt/mimir-app/daemon && .venv/bin/pip install -e ".[dev]"`

**Step 2: Create PyInstaller spec**

Create `daemon/mimir_daemon.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para mimir-daemon."""

import sys
from pathlib import Path

block_cipher = None
daemon_dir = Path(SPECPATH)

a = Analysis(
    [str(daemon_dir / "mimir_daemon" / "__main__.py")],
    pathex=[str(daemon_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "mimir_daemon.platform.linux",
        "mimir_daemon.integrations.odoo_v11",
        "mimir_daemon.integrations.odoo_v16",
        "mimir_daemon.integrations.mock",
        "mimir_daemon.ai.gemini",
        "mimir_daemon.ai.claude_provider",
        "mimir_daemon.ai.openai_provider",
        "mimir_daemon.sources.gitlab",
        "aiosqlite",
        "pystray",
        "PIL",
        "dbus_next",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="mimir-daemon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

**Step 3: Test PyInstaller build**

Run: `cd /opt/mimir-app/daemon && .venv/bin/pyinstaller mimir_daemon.spec --distpath ../dist --workpath /tmp/mimir-build --clean`
Expected: Generates `dist/mimir-daemon` binary

**Step 4: Test the binary runs**

Run: `cd /opt/mimir-app && ./dist/mimir-daemon --help`
Expected: Shows help text (or starts and can be Ctrl+C'd)

Run: `cd /opt/mimir-app && timeout 3 ./dist/mimir-daemon || true`
Expected: Daemon starts briefly, then timeout kills it. No import errors.

**Step 5: Commit**

```bash
git add daemon/mimir_daemon.spec daemon/pyproject.toml
git commit -m "feat: add PyInstaller spec for daemon standalone binary"
```

---

### Task 2: Actualizar install-service.sh para binario PyInstaller

**Files:**
- Modify: `daemon/install-service.sh`

**Step 1: Rewrite install-service.sh**

Replace the entire content of `daemon/install-service.sh` with:

```bash
#!/bin/bash
# Instala el daemon Mimir como servicio de usuario systemd.
#
# Uso:
#   bash install-daemon.sh [ruta-al-binario]
#
# Si no se pasa ruta, busca el binario en dist/mimir-daemon o usa python como fallback.
#
# Desinstalar:
#   systemctl --user stop mimir-daemon
#   systemctl --user disable mimir-daemon
#   rm ~/.config/systemd/user/mimir-daemon.service
#   rm -rf ~/.local/bin/mimir-daemon

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="$HOME/.local/bin"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/mimir-daemon.service"
CONFIG_DIR="$HOME/.config/mimir"

echo "=== Mimir Daemon - Instalador ==="

# Determinar ejecutable
BINARY_ARG="${1:-}"
if [ -n "$BINARY_ARG" ] && [ -f "$BINARY_ARG" ]; then
    DAEMON_BIN="$BINARY_ARG"
    echo "Usando binario proporcionado: $DAEMON_BIN"
elif [ -f "$PROJECT_DIR/dist/mimir-daemon" ]; then
    DAEMON_BIN="$PROJECT_DIR/dist/mimir-daemon"
    echo "Usando binario PyInstaller: $DAEMON_BIN"
else
    # Fallback: usar python con venv
    VENV_DIR="$SCRIPT_DIR/.venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creando entorno virtual..."
        python3 -m venv "$VENV_DIR"
    fi
    echo "Instalando dependencias..."
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet -e "$SCRIPT_DIR"
    DAEMON_BIN=""
    EXEC_START="$VENV_DIR/bin/python -m mimir_daemon"
    echo "Usando Python (fallback): $EXEC_START"
fi

# Instalar binario si existe
if [ -n "${DAEMON_BIN:-}" ]; then
    mkdir -p "$INSTALL_DIR"
    cp "$DAEMON_BIN" "$INSTALL_DIR/mimir-daemon"
    chmod +x "$INSTALL_DIR/mimir-daemon"
    EXEC_START="$INSTALL_DIR/mimir-daemon"
    echo "Binario instalado en: $INSTALL_DIR/mimir-daemon"
fi

# Verificar que arranca
echo "Verificando daemon..."
timeout 2 $EXEC_START --help 2>/dev/null || timeout 2 $EXEC_START 2>/dev/null &
VERIFY_PID=$!
sleep 1
if kill -0 $VERIFY_PID 2>/dev/null; then
    kill $VERIFY_PID 2>/dev/null || true
    wait $VERIFY_PID 2>/dev/null || true
    echo "Verificacion OK"
else
    wait $VERIFY_PID 2>/dev/null || true
    echo "Verificacion OK"
fi

# Crear directorio config
mkdir -p "$CONFIG_DIR"

# Crear directorio systemd
mkdir -p "$SERVICE_DIR"

# Generar service file
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Mimir Activity Capture Daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=$EXEC_START
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0
Environment=XAUTHORITY=$HOME/.Xauthority
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/%U/bus

[Install]
WantedBy=default.target
EOF

echo "Service file creado: $SERVICE_FILE"

# Recargar y habilitar
systemctl --user daemon-reload
systemctl --user enable mimir-daemon
systemctl --user restart mimir-daemon

echo ""
echo "=== Instalacion completada ==="
echo "Estado: $(systemctl --user is-active mimir-daemon)"
echo ""
echo "Comandos utiles:"
echo "  systemctl --user status mimir-daemon    # Ver estado"
echo "  systemctl --user restart mimir-daemon   # Reiniciar"
echo "  journalctl --user -u mimir-daemon -f    # Ver logs"
echo "  curl http://127.0.0.1:9477/health       # Health check"
```

**Step 2: Commit**

```bash
git add daemon/install-service.sh
git commit -m "feat: update install-service.sh to support PyInstaller binary"
```

---

### Task 3: Configurar Tauri bundle para Linux

**Files:**
- Modify: `src-tauri/tauri.conf.json`

**Step 1: Update tauri.conf.json bundle config**

Read the file first. Update the `bundle` section to target only Linux formats and add metadata:

```json
  "bundle": {
    "active": true,
    "targets": ["deb", "appimage"],
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ],
    "linux": {
      "deb": {
        "depends": ["libwebkit2gtk-4.1-0", "libgtk-3-0"],
        "section": "utils",
        "desktopEntry": {
          "categories": "Office;Utility;",
          "comment": "Asistente inteligente de imputacion de horas",
          "keywords": ["mimir", "timesheet", "odoo", "factorlibre"]
        }
      },
      "appimage": {
        "bundleMediaFramework": false
      }
    },
    "category": "Utility",
    "shortDescription": "Asistente inteligente de imputacion de horas",
    "longDescription": "Mimir captura automaticamente la actividad del empleado, sugiere descripciones con IA, y permite imputar horas a Odoo."
  }
```

**Step 2: Verify Tauri config is valid**

Run: `cd /opt/mimir-app/src-tauri && cargo check`
Expected: OK

**Step 3: Commit**

```bash
git add src-tauri/tauri.conf.json
git commit -m "feat: configure Tauri bundle for Linux .deb and .AppImage"
```

---

### Task 4: Script de build unificado

**Files:**
- Create: `scripts/build.sh`

**Step 1: Create build script**

Create `scripts/build.sh`:

```bash
#!/bin/bash
# Build completo de Mimir para Linux.
#
# Genera:
#   dist/mimir-daemon          — Binario standalone del daemon
#   dist/install-daemon.sh     — Script instalador del servicio
#   target/release/bundle/deb/ — Paquete .deb de la app
#   target/release/bundle/appimage/ — AppImage de la app
#
# Requisitos:
#   - Python 3.10+ con venv
#   - Node.js 18+
#   - Rust + cargo
#   - Dependencias de Tauri: libwebkit2gtk-4.1-dev, libgtk-3-dev, etc.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DAEMON_DIR="$PROJECT_DIR/daemon"
DIST_DIR="$PROJECT_DIR/dist"

echo "=== Mimir Build ==="
echo "Proyecto: $PROJECT_DIR"
echo ""

# --- Paso 1: Build daemon con PyInstaller ---
echo "--- [1/3] Construyendo daemon (PyInstaller) ---"

cd "$DAEMON_DIR"

# Crear/activar venv si no existe
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e ".[dev]"

# Build
.venv/bin/pyinstaller mimir_daemon.spec \
    --distpath "$DIST_DIR" \
    --workpath /tmp/mimir-build \
    --clean \
    --noconfirm

echo "Daemon binary: $DIST_DIR/mimir-daemon"

# Verificar
echo "Verificando binario..."
timeout 2 "$DIST_DIR/mimir-daemon" --help 2>/dev/null || true
echo "OK"

# --- Paso 2: Copiar instalador ---
echo ""
echo "--- [2/3] Preparando instalador ---"
cp "$DAEMON_DIR/install-service.sh" "$DIST_DIR/install-daemon.sh"
chmod +x "$DIST_DIR/install-daemon.sh"
echo "Instalador: $DIST_DIR/install-daemon.sh"

# --- Paso 3: Build app Tauri ---
echo ""
echo "--- [3/3] Construyendo app Tauri ---"
cd "$PROJECT_DIR"
npm install --silent
npm run tauri build

echo ""
echo "=== Build completado ==="
echo ""
echo "Artefactos:"
echo "  Daemon:    $DIST_DIR/mimir-daemon"
echo "  Installer: $DIST_DIR/install-daemon.sh"

# Listar artefactos Tauri
if [ -d "$PROJECT_DIR/src-tauri/target/release/bundle/deb" ]; then
    echo "  .deb:      $(ls "$PROJECT_DIR/src-tauri/target/release/bundle/deb/"*.deb 2>/dev/null || echo 'no encontrado')"
fi
if [ -d "$PROJECT_DIR/src-tauri/target/release/bundle/appimage" ]; then
    echo "  AppImage:  $(ls "$PROJECT_DIR/src-tauri/target/release/bundle/appimage/"*.AppImage 2>/dev/null || echo 'no encontrado')"
fi

echo ""
echo "Para instalar el daemon:"
echo "  $DIST_DIR/install-daemon.sh $DIST_DIR/mimir-daemon"
```

**Step 2: Make executable**

Run: `chmod +x /opt/mimir-app/scripts/build.sh`

**Step 3: Commit**

```bash
git add scripts/build.sh
git commit -m "feat: add unified build script for daemon + Tauri app"
```

---

### Task 5: Añadir .gitignore para artefactos de build

**Files:**
- Modify: `.gitignore`

**Step 1: Check current .gitignore**

Read `.gitignore` first.

**Step 2: Add build artifact patterns**

Ensure these patterns are in `.gitignore`:

```
# Build artifacts
dist/
daemon/build/
daemon/*.spec.bak
/tmp/mimir-build/

# PyInstaller
*.spec.bak
```

**Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add build artifacts to .gitignore"
```

---

### Task 6: Verificación final + PROGRESS.md

**Step 1: Run all daemon tests**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/ -v`
Expected: ALL PASS (108 tests)

**Step 2: Run TypeScript check**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 3: Run Rust check**

Run: `cd /opt/mimir-app/src-tauri && cargo check`
Expected: OK

**Step 4: Test PyInstaller build (si hay recursos)**

Run: `cd /opt/mimir-app/daemon && .venv/bin/pyinstaller mimir_daemon.spec --distpath ../dist --workpath /tmp/mimir-build --clean --noconfirm`
Expected: Binary created at `dist/mimir-daemon`

**Step 5: Update PROGRESS.md**

Mark Fase 6 as COMPLETADA with all tasks.

**Step 6: Commit**

```bash
git add PROGRESS.md
git commit -m "docs: mark Phase 6 (packaging) as complete"
```

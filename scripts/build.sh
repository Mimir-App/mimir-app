#!/bin/bash
# Build completo de Mimir para Linux.
#
# Genera:
#   dist/daemon/mimir-capture             — Binario capture (servicio systemd)
#   dist/daemon/mimir-server              — Binario server (lanzado por Tauri)
#   dist/daemon/install-daemon.sh         — Script instalador
#   src-tauri/target/release/bundle/deb/  — Paquete .deb de la app
#   src-tauri/target/release/bundle/appimage/ — AppImage de la app
#
# Requisitos:
#   - Python 3.10+ con venv
#   - Node.js 18+
#   - Rust + cargo
#   - Dependencias Tauri: libwebkit2gtk-4.1-dev, libgtk-3-dev, etc.
#
# Uso:
#   bash scripts/build.sh           # Build completo
#   bash scripts/build.sh daemon    # Solo capture + server
#   bash scripts/build.sh app       # Solo app Tauri

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DAEMON_DIR="$PROJECT_DIR/daemon"
DIST_DIR="$PROJECT_DIR/dist/daemon"
TARGET="${1:-all}"

echo "=== Mimir Build ==="
echo "Proyecto: $PROJECT_DIR"
echo "Target: $TARGET"
echo ""

ensure_venv() {
    cd "$DAEMON_DIR"
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -e ".[dev]"
    mkdir -p "$DIST_DIR"
}

build_capture() {
    echo "--- [capture] Construyendo mimir-capture (PyInstaller) ---"
    ensure_venv
    .venv/bin/pyinstaller mimir_capture.spec \
        --distpath "$DIST_DIR" \
        --workpath /tmp/mimir-build-capture \
        --clean --noconfirm 2>&1 | tail -3
    echo "Capture: $DIST_DIR/mimir-capture"
    echo ""
}

build_server() {
    echo "--- [server] Construyendo mimir-server (PyInstaller) ---"
    ensure_venv
    .venv/bin/pyinstaller mimir_server.spec \
        --distpath "$DIST_DIR" \
        --workpath /tmp/mimir-build-server \
        --clean --noconfirm 2>&1 | tail -3
    echo "Server: $DIST_DIR/mimir-server"
    echo ""
}

build_daemon() {
    build_capture
    build_server
    cp "$DAEMON_DIR/install-service.sh" "$DIST_DIR/install-daemon.sh"
    chmod +x "$DIST_DIR/install-daemon.sh"
}

build_app() {
    echo "--- [app] Construyendo app Tauri ---"
    cd "$PROJECT_DIR"
    npm install --silent
    npm run tauri build

    echo ""
}

# Ejecutar segun target
case "$TARGET" in
    capture)
        build_capture
        ;;
    server)
        build_server
        ;;
    daemon)
        build_daemon
        ;;
    app)
        build_app
        ;;
    all)
        build_daemon
        build_app
        ;;
    *)
        echo "Target no valido: $TARGET"
        echo "Uso: build.sh [capture|server|daemon|app|all]"
        exit 1
        ;;
esac

echo "=== Build completado ==="
echo ""
echo "Artefactos:"

if [ -f "$DIST_DIR/mimir-capture" ]; then
    echo "  Capture:   $DIST_DIR/mimir-capture ($(du -h "$DIST_DIR/mimir-capture" | cut -f1))"
fi
if [ -f "$DIST_DIR/mimir-server" ]; then
    echo "  Server:    $DIST_DIR/mimir-server ($(du -h "$DIST_DIR/mimir-server" | cut -f1))"
fi
if [ -f "$DIST_DIR/install-daemon.sh" ]; then
    echo "  Installer: $DIST_DIR/install-daemon.sh"
fi

if [ -d "$PROJECT_DIR/src-tauri/target/release/bundle/deb" ]; then
    echo "  .deb:      $(ls "$PROJECT_DIR/src-tauri/target/release/bundle/deb/"*.deb 2>/dev/null || echo 'no encontrado')"
fi
if [ -d "$PROJECT_DIR/src-tauri/target/release/bundle/appimage" ]; then
    echo "  AppImage:  $(ls "$PROJECT_DIR/src-tauri/target/release/bundle/appimage/"*.AppImage 2>/dev/null || echo 'no encontrado')"
fi

echo ""
echo "Para instalar:"
echo "  $DIST_DIR/install-daemon.sh"

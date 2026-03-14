#!/bin/bash
# Build completo de Mimir para Linux.
#
# Genera:
#   dist/daemon/mimir-daemon              — Binario standalone del daemon
#   dist/daemon/install-daemon.sh         — Script instalador del servicio
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
#   bash scripts/build.sh daemon    # Solo daemon
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

build_daemon() {
    echo "--- [daemon] Construyendo daemon (PyInstaller) ---"
    cd "$DAEMON_DIR"

    # Crear/activar venv si no existe
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -e ".[dev]"

    # Build
    mkdir -p "$DIST_DIR"
    .venv/bin/pyinstaller mimir_daemon.spec \
        --distpath "$DIST_DIR" \
        --workpath /tmp/mimir-build \
        --clean \
        --noconfirm

    # Copiar instalador
    cp "$DAEMON_DIR/install-service.sh" "$DIST_DIR/install-daemon.sh"
    chmod +x "$DIST_DIR/install-daemon.sh"

    echo "Daemon binary: $DIST_DIR/mimir-daemon"
    echo "Instalador:    $DIST_DIR/install-daemon.sh"
    echo ""
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
        echo "Uso: build.sh [daemon|app|all]"
        exit 1
        ;;
esac

echo "=== Build completado ==="
echo ""
echo "Artefactos:"

if [ -f "$DIST_DIR/mimir-daemon" ]; then
    echo "  Daemon:    $DIST_DIR/mimir-daemon ($(du -h "$DIST_DIR/mimir-daemon" | cut -f1))"
    echo "  Installer: $DIST_DIR/install-daemon.sh"
fi

if [ -d "$PROJECT_DIR/src-tauri/target/release/bundle/deb" ]; then
    echo "  .deb:      $(ls "$PROJECT_DIR/src-tauri/target/release/bundle/deb/"*.deb 2>/dev/null || echo 'no encontrado')"
fi
if [ -d "$PROJECT_DIR/src-tauri/target/release/bundle/appimage" ]; then
    echo "  AppImage:  $(ls "$PROJECT_DIR/src-tauri/target/release/bundle/appimage/"*.AppImage 2>/dev/null || echo 'no encontrado')"
fi

echo ""
echo "Para instalar el daemon:"
echo "  $DIST_DIR/install-daemon.sh $DIST_DIR/mimir-daemon"

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
#   bash scripts/build.sh deb       # Paquetes .deb unificados

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

package_deb() {
    echo "--- [deb] Empaquetando .deb ---"

    # Extraer version de tauri.conf.json
    VERSION=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/src-tauri/tauri.conf.json'))['version'])")
    ARCH="amd64"
    DEB_OUT="$PROJECT_DIR/dist/packages"
    mkdir -p "$DEB_OUT"

    # --- 1. Reempaquetar .deb de Tauri con mimir-server ---
    TAURI_DEB=$(ls "$PROJECT_DIR/src-tauri/target/release/bundle/deb/"*.deb 2>/dev/null | head -1)
    if [ -z "$TAURI_DEB" ]; then
        echo "ERROR: No se encontro .deb de Tauri. Ejecuta build_app() primero."
        exit 1
    fi

    REPACK_DIR=$(mktemp -d /tmp/mimir-repack-XXXX)
    dpkg-deb -R "$TAURI_DEB" "$REPACK_DIR"

    # Inyectar mimir-server
    cp "$DIST_DIR/mimir-server" "$REPACK_DIR/usr/bin/mimir-server"
    chmod 755 "$REPACK_DIR/usr/bin/mimir-server"

    # Inyectar mimir-uninstall
    cp "$PROJECT_DIR/scripts/uninstall.sh" "$REPACK_DIR/usr/bin/mimir-uninstall"
    chmod 755 "$REPACK_DIR/usr/bin/mimir-uninstall"

    # Inyectar agente Claude Code para generacion de bloques
    AGENTS_DIR="$REPACK_DIR/usr/share/mimir/agents"
    mkdir -p "$AGENTS_DIR"
    cp "$PROJECT_DIR/.claude/agents/timesheet-generator.md" "$AGENTS_DIR/"
    chmod 644 "$AGENTS_DIR/timesheet-generator.md"

    # Inyectar postinst y prerm para el paquete mimir
    cat > "$REPACK_DIR/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
if [ "$1" = "configure" ]; then
    echo ""
    echo "=== Mimir instalado ==="
    echo "Ejecuta 'mimir' para abrir la aplicación."
    echo "Para desinstalar: mimir-uninstall"
    echo ""
fi
POSTINST
    chmod 755 "$REPACK_DIR/DEBIAN/postinst"

    cat > "$REPACK_DIR/DEBIAN/prerm" << 'PRERM'
#!/bin/bash
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    echo ""
    echo "=== Desinstalando mimir ==="
    # Parar server si esta corriendo
    pkill -f 'mimir-server' 2>/dev/null || true
    pkill -x 'mimir' 2>/dev/null || true
    echo "Para limpieza completa (datos, capture, config):"
    echo "  mimir-uninstall --full"
    echo "  (ejecutar ANTES de desinstalar si quieres limpiar datos)"
    echo ""
fi
PRERM
    chmod 755 "$REPACK_DIR/DEBIAN/prerm"

    # Actualizar version en control
    sed -i "s/^Version:.*/Version: $VERSION/" "$REPACK_DIR/DEBIAN/control"

    # Regenerar md5sums
    (cd "$REPACK_DIR" && find usr -type f -exec md5sum {} \;) > "$REPACK_DIR/DEBIAN/md5sums"

    # Recalcular Installed-Size (en KB)
    INSTALLED_SIZE=$(du -sk "$REPACK_DIR" --exclude=DEBIAN | cut -f1)
    sed -i "s/^Installed-Size:.*/Installed-Size: $INSTALLED_SIZE/" "$REPACK_DIR/DEBIAN/control"

    # Deduplicar Depends
    DEPS=$(grep "^Depends:" "$REPACK_DIR/DEBIAN/control" | sed 's/^Depends: //' | tr ',' '\n' | sed 's/^ *//' | sort -u | paste -sd',' | sed 's/,/, /g')
    sed -i "s/^Depends:.*/Depends: $DEPS/" "$REPACK_DIR/DEBIAN/control"

    dpkg-deb --build --root-owner-group "$REPACK_DIR" "$DEB_OUT/mimir_${VERSION}_${ARCH}.deb"
    rm -rf "$REPACK_DIR"
    echo "App .deb: $DEB_OUT/mimir_${VERSION}_${ARCH}.deb"

    # --- 2. Construir mimir-capture .deb ---
    CAPTURE_PKG=$(mktemp -d /tmp/mimir-capture-pkg-XXXX)
    cp -r "$PROJECT_DIR/packaging/mimir-capture/"* "$CAPTURE_PKG/"

    # Copiar binario
    mkdir -p "$CAPTURE_PKG/usr/bin"
    cp "$DIST_DIR/mimir-capture" "$CAPTURE_PKG/usr/bin/mimir-capture"
    chmod 755 "$CAPTURE_PKG/usr/bin/mimir-capture"

    # Copiar extension GNOME Shell
    GNOME_EXT_DIR="$CAPTURE_PKG/usr/share/gnome-shell/extensions/mimir-window-tracker@mimir.app"
    mkdir -p "$GNOME_EXT_DIR"
    cp "$PROJECT_DIR/daemon/mimir_daemon/platform/gnome_extension/metadata.json" "$GNOME_EXT_DIR/"
    cp "$PROJECT_DIR/daemon/mimir_daemon/platform/gnome_extension/extension.js" "$GNOME_EXT_DIR/"
    chmod 644 "$GNOME_EXT_DIR/metadata.json" "$GNOME_EXT_DIR/extension.js"

    # Actualizar version y Installed-Size
    CAPTURE_SIZE=$(du -sk "$CAPTURE_PKG" --exclude=DEBIAN | cut -f1)
    sed -i "s/^Version:.*/Version: $VERSION/" "$CAPTURE_PKG/DEBIAN/control"
    sed -i "s/^Installed-Size:.*/Installed-Size: $CAPTURE_SIZE/" "$CAPTURE_PKG/DEBIAN/control"

    # Permisos DEBIAN scripts
    chmod 755 "$CAPTURE_PKG/DEBIAN/postinst" "$CAPTURE_PKG/DEBIAN/prerm"
    chmod 644 "$CAPTURE_PKG/DEBIAN/control"

    dpkg-deb --build --root-owner-group "$CAPTURE_PKG" "$DEB_OUT/mimir-capture_${VERSION}_${ARCH}.deb"
    rm -rf "$CAPTURE_PKG"
    echo "Capture .deb: $DEB_OUT/mimir-capture_${VERSION}_${ARCH}.deb"

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
    deb)
        build_app
        build_daemon
        package_deb
        ;;
    *)
        echo "Target no valido: $TARGET"
        echo "Uso: build.sh [capture|server|daemon|app|deb|all]"
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

MIMIR_DEB=$(ls "$PROJECT_DIR/dist/packages/mimir_"*.deb 2>/dev/null | head -1)
if [ -n "$MIMIR_DEB" ]; then
    echo "  Mimir .deb: $MIMIR_DEB ($(du -h "$MIMIR_DEB" | cut -f1))"
fi
CAPTURE_DEB=$(ls "$PROJECT_DIR/dist/packages/mimir-capture_"*.deb 2>/dev/null | head -1)
if [ -n "$CAPTURE_DEB" ]; then
    echo "  Capture .deb: $CAPTURE_DEB ($(du -h "$CAPTURE_DEB" | cut -f1))"
fi

echo ""
echo "Para desinstalar:"
echo "  mimir-uninstall           # Interactivo"
echo "  mimir-uninstall --full    # Todo"
echo ""
echo "Para instalar:"
if [ -n "${MIMIR_DEB:-}" ]; then
    echo "  sudo apt install $MIMIR_DEB"
    if [ -n "${CAPTURE_DEB:-}" ]; then
        echo "  sudo apt install $CAPTURE_DEB   # Opcional: captura automatica"
    fi
else
    echo "  $DIST_DIR/install-daemon.sh"
fi

#!/bin/bash
# Instala mimir-capture como servicio systemd y mimir-server en ~/.local/bin.
#
# Uso:
#   bash install-daemon.sh                    # Busca binarios en dist/daemon/
#   bash install-daemon.sh /ruta/al/dir       # Busca binarios en el directorio dado
#
# Desinstalar:
#   systemctl --user stop mimir-capture
#   systemctl --user disable mimir-capture
#   rm ~/.config/systemd/user/mimir-capture.service
#   rm -f ~/.local/bin/mimir-capture ~/.local/bin/mimir-server

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="$HOME/.local/bin"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/mimir-capture.service"
CONFIG_DIR="$HOME/.config/mimir"

echo "=== Mimir - Instalador ==="

# Determinar directorio de binarios
BIN_DIR="${1:-$SCRIPT_DIR}"
if [ ! -d "$BIN_DIR" ]; then
    BIN_DIR="$PROJECT_DIR/dist/daemon"
fi

CAPTURE_BIN=""
SERVER_BIN=""
CAPTURE_EXEC=""

# Buscar binarios
if [ -f "$BIN_DIR/mimir-capture" ]; then
    CAPTURE_BIN="$BIN_DIR/mimir-capture"
elif [ -f "$SCRIPT_DIR/mimir-capture" ]; then
    CAPTURE_BIN="$SCRIPT_DIR/mimir-capture"
fi

if [ -f "$BIN_DIR/mimir-server" ]; then
    SERVER_BIN="$BIN_DIR/mimir-server"
elif [ -f "$SCRIPT_DIR/mimir-server" ]; then
    SERVER_BIN="$SCRIPT_DIR/mimir-server"
fi

mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# Instalar capture
if [ -n "$CAPTURE_BIN" ]; then
    cp "$CAPTURE_BIN" "$INSTALL_DIR/mimir-capture"
    chmod +x "$INSTALL_DIR/mimir-capture"
    CAPTURE_EXEC="$INSTALL_DIR/mimir-capture"
    echo "Capture instalado: $INSTALL_DIR/mimir-capture"
else
    # Fallback: python
    VENV_DIR="$SCRIPT_DIR/.venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creando entorno virtual..."
        python3 -m venv "$VENV_DIR"
    fi
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet -e "$SCRIPT_DIR"
    CAPTURE_EXEC="$VENV_DIR/bin/python -m mimir_daemon"
    echo "Capture (Python fallback): $CAPTURE_EXEC"
fi

# Instalar server
if [ -n "$SERVER_BIN" ]; then
    cp "$SERVER_BIN" "$INSTALL_DIR/mimir-server"
    chmod +x "$INSTALL_DIR/mimir-server"
    echo "Server instalado: $INSTALL_DIR/mimir-server"
else
    echo "AVISO: mimir-server no encontrado. La app Tauri usara Python como fallback."
fi

# Parar servicio viejo si existe
systemctl --user stop mimir-daemon 2>/dev/null || true
systemctl --user disable mimir-daemon 2>/dev/null || true
systemctl --user stop mimir-capture 2>/dev/null || true

# Crear directorio systemd
mkdir -p "$SERVICE_DIR"

# Generar service file para capture
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Mimir Activity Capture
After=graphical-session.target

[Service]
Type=simple
ExecStart=$CAPTURE_EXEC
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
systemctl --user enable mimir-capture
systemctl --user restart mimir-capture

echo ""
echo "=== Instalacion completada ==="
echo "Capture: $(systemctl --user is-active mimir-capture)"
echo ""
echo "Comandos utiles:"
echo "  systemctl --user status mimir-capture     # Estado de captura"
echo "  systemctl --user restart mimir-capture    # Reiniciar captura"
echo "  journalctl --user -u mimir-capture -f     # Logs de captura"
echo "  curl http://127.0.0.1:9476/health         # Health check captura"
echo "  curl http://127.0.0.1:9477/health         # Health check servidor (cuando la app esta abierta)"

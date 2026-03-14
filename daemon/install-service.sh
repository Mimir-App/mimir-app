#!/bin/bash
# Instala el daemon Mimir como servicio de usuario systemd.
#
# Uso:
#   bash install-service.sh [ruta-al-binario]
#
# Si no se pasa ruta, busca el binario en dist/mimir-daemon o usa python como fallback.
#
# Desinstalar:
#   systemctl --user stop mimir-daemon
#   systemctl --user disable mimir-daemon
#   rm ~/.config/systemd/user/mimir-daemon.service
#   rm -f ~/.local/bin/mimir-daemon

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
EXEC_START=""

if [ -n "$BINARY_ARG" ] && [ -f "$BINARY_ARG" ]; then
    echo "Usando binario proporcionado: $BINARY_ARG"
    mkdir -p "$INSTALL_DIR"
    cp "$BINARY_ARG" "$INSTALL_DIR/mimir-daemon"
    chmod +x "$INSTALL_DIR/mimir-daemon"
    EXEC_START="$INSTALL_DIR/mimir-daemon"
elif [ -f "$PROJECT_DIR/dist/mimir-daemon" ]; then
    echo "Usando binario PyInstaller: $PROJECT_DIR/dist/mimir-daemon"
    mkdir -p "$INSTALL_DIR"
    cp "$PROJECT_DIR/dist/mimir-daemon" "$INSTALL_DIR/mimir-daemon"
    chmod +x "$INSTALL_DIR/mimir-daemon"
    EXEC_START="$INSTALL_DIR/mimir-daemon"
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
    EXEC_START="$VENV_DIR/bin/python -m mimir_daemon"
    echo "Usando Python (fallback): $EXEC_START"
fi

echo "Ejecutable: $EXEC_START"

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

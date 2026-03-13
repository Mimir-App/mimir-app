#!/bin/bash
# Instala el daemon Mimir como servicio de usuario systemd.
#
# Uso:
#   cd mimir/daemon
#   bash install-service.sh
#
# Desinstalar:
#   systemctl --user stop mimir-daemon
#   systemctl --user disable mimir-daemon
#   rm ~/.config/systemd/user/mimir-daemon.service

set -euo pipefail

DAEMON_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$DAEMON_DIR/.venv"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/mimir-daemon.service"

echo "=== Mimir Daemon - Instalador ==="
echo "Directorio: $DAEMON_DIR"

# Crear venv si no existe
if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv "$VENV_DIR"
fi

# Instalar dependencias
echo "Instalando dependencias..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$DAEMON_DIR"

# Verificar que arranca
echo "Verificando daemon..."
"$VENV_DIR/bin/python" -c "from mimir_daemon.config import DaemonConfig; print('OK')"

# Crear directorio systemd
mkdir -p "$SERVICE_DIR"

# Generar service file con rutas absolutas
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Mimir Activity Capture Daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=$VENV_DIR/bin/python -m mimir_daemon
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0
Environment=XAUTHORITY=$HOME/.Xauthority
WorkingDirectory=$DAEMON_DIR

[Install]
WantedBy=default.target
EOF

echo "Service file creado: $SERVICE_FILE"

# Recargar y habilitar
systemctl --user daemon-reload
systemctl --user enable mimir-daemon
systemctl --user start mimir-daemon

echo ""
echo "=== Instalacion completada ==="
echo "Estado: $(systemctl --user is-active mimir-daemon)"
echo ""
echo "Comandos utiles:"
echo "  systemctl --user status mimir-daemon    # Ver estado"
echo "  systemctl --user restart mimir-daemon   # Reiniciar"
echo "  journalctl --user -u mimir-daemon -f    # Ver logs"
echo "  curl http://127.0.0.1:9477/health       # Health check"
echo "  curl http://127.0.0.1:9477/blocks       # Ver bloques de hoy"

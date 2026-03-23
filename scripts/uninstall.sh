#!/bin/bash
# =============================================================================
# Mimir — Script de desinstalación
# Uso:
#   ./uninstall.sh          → Desinstalación selectiva (interactivo)
#   ./uninstall.sh --app    → Solo la app (mantiene datos y capture)
#   ./uninstall.sh --full   → Desinstalación completa
#   ./uninstall.sh --dry-run  → Muestra qué se haría sin ejecutar nada
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

DRY_RUN=false
MODE=""

# --- Argumentos ---
for arg in "$@"; do
    case "$arg" in
        --app)    MODE="app" ;;
        --full)   MODE="full" ;;
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            echo "Uso: $0 [--app | --full] [--dry-run]"
            echo ""
            echo "  --app      Desinstalar la app (mantiene base de datos y config)"
            echo "  --full     Desinstalación completa (todo)"
            echo "  --dry-run  Simular sin ejecutar nada"
            echo "  (sin args) Modo interactivo"
            exit 0
            ;;
        *)
            echo "Argumento desconocido: $arg"
            echo "Usa --help para ver opciones."
            exit 1
            ;;
    esac
done

# --- Helpers ---
info()    { echo -e "${CYAN}→${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}!${NC} $1"; }
error()   { echo -e "${RED}✗${NC} $1"; }

run() {
    if $DRY_RUN; then
        echo -e "  ${YELLOW}[dry-run]${NC} $1"
    else
        eval "$2"
        success "$1"
    fi
}

skip() {
    echo -e "  ${CYAN}[skip]${NC} $1 (no encontrado)"
}

confirm() {
    if $DRY_RUN; then return 0; fi
    echo ""
    echo -e "${BOLD}$1${NC}"
    read -rp "¿Continuar? [s/N] " resp
    [[ "$resp" =~ ^[sS]$ ]]
}

# --- Detección de qué hay instalado ---
HAS_DEB_APP=false
HAS_DEB_CAPTURE=false
HAS_LOCAL_CAPTURE=false
HAS_LOCAL_SERVER=false
HAS_SYSTEMD=false
HAS_GNOME_EXT=false
HAS_USER_DATA=false
HAS_KEYRING=false

dpkg -l mimir &>/dev/null 2>&1 && HAS_DEB_APP=true
dpkg -l mimir-capture &>/dev/null 2>&1 && HAS_DEB_CAPTURE=true
[ -f "$HOME/.local/bin/mimir-capture" ] && HAS_LOCAL_CAPTURE=true
[ -f "$HOME/.local/bin/mimir-server" ] && HAS_LOCAL_SERVER=true
[ -f "$HOME/.config/systemd/user/mimir-capture.service" ] && HAS_SYSTEMD=true
[ -d "/usr/share/gnome-shell/extensions/mimir-window-tracker@mimir.app" ] && HAS_GNOME_EXT=true
[ -d "$HOME/.config/mimir" ] && HAS_USER_DATA=true

# --- Mostrar estado ---
echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║     Mimir — Desinstalación           ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Estado actual:${NC}"
$HAS_DEB_APP       && info "Paquete .deb mimir instalado"         || skip "Paquete .deb mimir"
$HAS_DEB_CAPTURE   && info "Paquete .deb mimir-capture instalado" || skip "Paquete .deb mimir-capture"
$HAS_LOCAL_CAPTURE && info "mimir-capture en ~/.local/bin/"       || skip "mimir-capture local"
$HAS_LOCAL_SERVER  && info "mimir-server en ~/.local/bin/"        || skip "mimir-server local"
$HAS_SYSTEMD       && info "Servicio systemd usuario"             || skip "Servicio systemd"
$HAS_GNOME_EXT     && info "Extensión GNOME Shell"                || skip "Extensión GNOME"
$HAS_USER_DATA     && info "Datos de usuario en ~/.config/mimir/" || skip "Datos de usuario"

# --- Modo interactivo ---
if [ -z "$MODE" ]; then
    echo ""
    echo -e "${BOLD}¿Qué deseas hacer?${NC}"
    echo ""
    echo "  1) Desinstalar la app (mantiene base de datos y config)"
    echo "  2) Desinstalación completa (elimina todo)"
    echo "  3) Cancelar"
    echo ""
    read -rp "Opción [1/2/3]: " choice
    case "$choice" in
        1) MODE="app" ;;
        2) MODE="full" ;;
        *) echo "Cancelado."; exit 0 ;;
    esac
fi

$DRY_RUN && echo -e "\n${YELLOW}=== MODO DRY-RUN: no se ejecutará nada ===${NC}"

# =============================================================================
# PASO 1: Parar procesos activos
# =============================================================================
echo ""
echo -e "${BOLD}── Paso 1: Parar procesos ──${NC}"

# Parar mimir-server (child de Tauri, o suelto)
if pgrep -f "mimir-server" &>/dev/null; then
    run "Parar mimir-server" "pkill -f 'mimir-server' || true"
else
    skip "mimir-server (no está corriendo)"
fi

# Parar app Tauri
if pgrep -x "mimir" &>/dev/null; then
    run "Parar app mimir" "pkill -x 'mimir' || true"
fi

# Parar y deshabilitar capture (siempre, porque mimir-capture depende de mimir)
if systemctl --user is-active mimir-capture &>/dev/null 2>&1; then
    run "Parar servicio mimir-capture" "systemctl --user stop mimir-capture"
fi
if systemctl --user is-enabled mimir-capture &>/dev/null 2>&1; then
    run "Deshabilitar servicio mimir-capture" "systemctl --user disable mimir-capture"
fi
if pgrep -f "mimir-capture" &>/dev/null; then
    run "Parar proceso mimir-capture" "pkill -f 'mimir-capture' || true"
fi

# =============================================================================
# PASO 2: Desinstalar paquetes .deb
# =============================================================================
echo ""
echo -e "${BOLD}── Paso 2: Paquetes .deb ──${NC}"

# Desinstalar capture ANTES que app (mimir-capture depende de mimir)
if $HAS_DEB_CAPTURE; then
    run "Desinstalar paquete mimir-capture" "sudo dpkg --purge mimir-capture"
else
    skip "Paquete mimir-capture"
fi

if $HAS_DEB_APP; then
    run "Desinstalar paquete mimir" "sudo dpkg --purge mimir"
else
    skip "Paquete mimir"
fi

# =============================================================================
# PASO 3: Binarios locales (~/.local/bin)
# =============================================================================
echo ""
echo -e "${BOLD}── Paso 3: Binarios locales ──${NC}"

if $HAS_LOCAL_SERVER; then
    run "Eliminar ~/.local/bin/mimir-server" "rm -f '$HOME/.local/bin/mimir-server'"
else
    skip "mimir-server local"
fi

if $HAS_LOCAL_CAPTURE; then
    run "Eliminar ~/.local/bin/mimir-capture" "rm -f '$HOME/.local/bin/mimir-capture'"
else
    skip "mimir-capture local"
fi

# =============================================================================
# PASO 4: Servicio systemd y extensión GNOME (solo full)
# =============================================================================
echo ""
echo -e "${BOLD}── Paso 4: Servicios del sistema ──${NC}"

if $HAS_SYSTEMD; then
    run "Eliminar servicio systemd" "rm -f '$HOME/.config/systemd/user/mimir-capture.service' && systemctl --user daemon-reload"
else
    skip "Servicio systemd"
fi

if $HAS_GNOME_EXT; then
    # Deshabilitar antes de eliminar
    if gnome-extensions list 2>/dev/null | grep -q "mimir-window-tracker@mimir.app"; then
        run "Deshabilitar extensión GNOME" "gnome-extensions disable mimir-window-tracker@mimir.app 2>/dev/null || true"
    fi
    run "Eliminar extensión GNOME" "sudo rm -rf /usr/share/gnome-shell/extensions/mimir-window-tracker@mimir.app"
else
    skip "Extensión GNOME"
fi

# =============================================================================
# PASO 5: Datos de usuario (solo full)
# =============================================================================
if [ "$MODE" = "full" ] && $HAS_USER_DATA; then
    echo ""
    echo -e "${BOLD}── Paso 5: Datos de usuario ──${NC}"

    # Mostrar qué hay
    echo ""
    warn "Se eliminará TODO en ~/.config/mimir/:"
    ls -lah "$HOME/.config/mimir/" 2>/dev/null | tail -n +2

    DB_FILE="$HOME/.config/mimir/daemon.db"
    if [ -f "$DB_FILE" ]; then
        DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
        BLOCK_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM blocks;" 2>/dev/null || echo "?")
        SIGNAL_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM signals;" 2>/dev/null || echo "?")
        echo ""
        warn "Base de datos: $DB_SIZE — $BLOCK_COUNT bloques, $SIGNAL_COUNT señales"
    fi

    if confirm "⚠  ¿ELIMINAR todos los datos de usuario? (base de datos, config, tokens)"; then
        run "Eliminar ~/.config/mimir/" "rm -rf '$HOME/.config/mimir'"
    else
        warn "Datos de usuario conservados en ~/.config/mimir/"
    fi
elif [ "$MODE" = "app" ] && $HAS_USER_DATA; then
    echo ""
    echo -e "${BOLD}── Paso 5: Datos de usuario ──${NC}"
    info "Datos conservados en ~/.config/mimir/ (modo app)"
fi

# =============================================================================
# PASO 6: Credenciales del keyring (solo full)
# =============================================================================
if [ "$MODE" = "full" ]; then
    echo ""
    echo -e "${BOLD}── Paso 6: Keyring ──${NC}"
    warn "Las credenciales almacenadas en el keyring del sistema NO se eliminan automáticamente."
    warn "Si deseas eliminarlas manualmente, usa Seahorse (Contraseñas y claves)"
    warn "o ejecuta: secret-tool search service mimir"
fi

# =============================================================================
# Resumen
# =============================================================================
echo ""
echo -e "${BOLD}══════════════════════════════════════${NC}"
if [ "$MODE" = "full" ]; then
    success "Desinstalación completa finalizada."
else
    success "App desinstalada. Datos de usuario conservados en ~/.config/mimir/"
    echo ""
    info "Para desinstalación completa en el futuro:"
    echo "  $0 --full"
fi

if $DRY_RUN; then
    echo ""
    echo -e "${YELLOW}(Esto fue una simulación. Ejecuta sin --dry-run para aplicar.)${NC}"
fi
echo ""

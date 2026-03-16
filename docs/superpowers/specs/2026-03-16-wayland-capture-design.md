# Mimir — Soporte Wayland para captura de ventana activa

## Contexto

`mimir-capture` usa `xdotool` para obtener la ventana activa. xdotool solo funciona en X11. En escritorios con Wayland (Ubuntu 22.04+ por defecto), `get_active_window()` devuelve `None` y no se crean bloques.

## Objetivo

Que la captura funcione en GNOME Wayland sin romper el soporte X11 existente.

Fuera de alcance: KDE Plasma Wayland y wlroots (Sway/Hyprland). Se implementaran en iteraciones futuras.

## Deteccion de entorno

Al arrancar, `LinuxProvider.setup()` lee `$XDG_SESSION_TYPE`:
- `x11` → backend xdotool (actual)
- `wayland` → backend GNOME D-Bus (nuevo)
- Otro / no definido → intenta xdotool como fallback, loguea warning si no esta disponible

No requiere configuracion manual del usuario.

El endpoint `/status` incluira un campo `"backend": "x11"` o `"backend": "wayland"` para facilitar diagnostico.

## Extension GNOME Shell: mimir-window-tracker

Extension minima que expone la ventana activa por D-Bus.

### Metadata

- UUID: `mimir-window-tracker@mimir.app`
- Nombre: Mimir Window Tracker
- Compatible: GNOME Shell 45, 46 (formato ESM requerido desde GNOME 45)
- Instalacion: `/usr/share/gnome-shell/extensions/mimir-window-tracker@mimir.app/`

Nota: GNOME 42-44 usa un formato de extension diferente (no ESM). Ubuntu 22.04 (GNOME 42) usa X11 por defecto, asi que no necesita esta extension. Se cubre solo GNOME 45+ que es donde Wayland es el default.

### metadata.json

```json
{
    "uuid": "mimir-window-tracker@mimir.app",
    "name": "Mimir Window Tracker",
    "description": "Exposes active window info over D-Bus for Mimir capture",
    "shell-version": ["45", "46"],
    "version": 1
}
```

### extension.js (ESM, GNOME 45+)

```javascript
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const IFACE_XML = `
<node>
  <interface name="org.mimir.WindowTracker">
    <method name="GetActiveWindow">
      <arg type="u" direction="out" name="pid"/>
      <arg type="s" direction="out" name="wm_class"/>
      <arg type="s" direction="out" name="title"/>
    </method>
  </interface>
</node>`;

export default class MimirWindowTracker {
    enable() {
        this._dbusImpl = Gio.DBusExportedObject.wrapJSObject(IFACE_XML, this);
        this._dbusImpl.export(Gio.DBus.session, '/org/mimir/WindowTracker');
        this._ownerId = Gio.bus_own_name(
            Gio.BusType.SESSION,
            'org.mimir.WindowTracker',
            Gio.BusNameOwnerFlags.NONE,
            null, null, null
        );
    }

    disable() {
        if (this._dbusImpl) this._dbusImpl.unexport();
        if (this._ownerId) Gio.bus_unown_name(this._ownerId);
        this._dbusImpl = null;
        this._ownerId = null;
    }

    GetActiveWindow() {
        const focusWindow = global.display.get_focus_window();
        if (!focusWindow) return [0, '', ''];
        const pid = focusWindow.get_pid() || 0;
        const wmClass = focusWindow.get_wm_class() || '';
        const title = focusWindow.get_title() || '';
        return [pid, wmClass, title];
    }
}
```

Notas:
- Cuando no hay ventana enfocada (pantalla bloqueada, overview, sin ventanas) devuelve `(0, '', '')`.
- Funciona tanto con ventanas nativas Wayland como XWayland (GNOME expone ambas via `Meta.Window`).

### D-Bus Interface

```xml
<interface name="org.mimir.WindowTracker">
  <method name="GetActiveWindow">
    <arg type="u" direction="out" name="pid"/>
    <arg type="s" direction="out" name="wm_class"/>
    <arg type="s" direction="out" name="title"/>
  </method>
</interface>
```

## Cambios en platform/linux.py

### Atributos nuevos en __init__()

```python
self._use_wayland: bool = False
self._wayland_bus: MessageBus | None = None
self._wayland_iface = None
self._wayland_warning_shown: bool = False
```

### Metodo setup()

```python
async def setup(self):
    session_type = os.environ.get("XDG_SESSION_TYPE", "")
    self._use_wayland = session_type == "wayland"
    if self._use_wayland:
        logger.info("Sesion Wayland detectada, usando backend D-Bus")
        await self._connect_wayland_bus()
    elif session_type:
        logger.info("Sesion %s detectada, usando backend xdotool", session_type)
    else:
        logger.warning("XDG_SESSION_TYPE no definido, usando xdotool como fallback")
    # ... resto del setup existente (D-Bus logind listener)
```

### Conexion D-Bus persistente

```python
async def _connect_wayland_bus(self):
    """Establece conexion persistente al D-Bus de la extension."""
    try:
        from dbus_next.aio import MessageBus
        self._wayland_bus = await MessageBus().connect()
        introspection = await self._wayland_bus.introspect(
            "org.mimir.WindowTracker", "/org/mimir/WindowTracker"
        )
        proxy = self._wayland_bus.get_proxy_object(
            "org.mimir.WindowTracker", "/org/mimir/WindowTracker", introspection
        )
        self._wayland_iface = proxy.get_interface("org.mimir.WindowTracker")
        logger.info("Conexion D-Bus con mimir-window-tracker establecida")
    except Exception as e:
        self._wayland_bus = None
        self._wayland_iface = None
        if not self._wayland_warning_shown:
            logger.warning("Extension mimir-window-tracker no disponible: %s", e)
            logger.warning("Activa la extension: gnome-extensions enable mimir-window-tracker@mimir.app")
            self._wayland_warning_shown = True
```

### Metodo get_active_window()

```python
async def get_active_window(self) -> WindowInfo | None:
    if self._use_wayland:
        return await self._get_active_window_wayland()
    return await self._get_active_window_x11()
```

### _get_active_window_x11()

El codigo actual de `get_active_window()` se mueve aqui sin cambios.

### _get_active_window_wayland()

```python
async def _get_active_window_wayland(self) -> WindowInfo | None:
    if not self._wayland_iface:
        await self._connect_wayland_bus()
        if not self._wayland_iface:
            return None
    try:
        pid, wm_class, title = await self._wayland_iface.call_get_active_window()
        if pid == 0:
            return None
        # Usar /proc/pid/comm para app_name (consistente con X11)
        app_name = self._get_app_name_sync(pid)
        return WindowInfo(pid=pid, app_name=app_name, window_title=title or "")
    except Exception:
        # Conexion perdida (extension reiniciada, sesion cambiada)
        self._wayland_bus = None
        self._wayland_iface = None
        return None
```

Notas:
- Se usa `_get_app_name_sync(pid)` (lectura de `/proc/pid/comm`) para `app_name`, igual que en X11. Esto garantiza nombres de app consistentes entre backends.
- `wm_class` se obtiene pero no se usa para `app_name` — queda disponible si se necesita en el futuro.
- La conexion D-Bus se reutiliza entre polls. Si se pierde, se reconecta en el siguiente poll.

### teardown()

Actualizar para desconectar el bus Wayland:

```python
async def teardown(self):
    # ... existente: cancelar logind listener
    if self._wayland_bus:
        self._wayland_bus.disconnect()
        self._wayland_bus = None
        self._wayland_iface = None
```

## Cambios en el .deb mimir-capture

### Estructura de packaging

```
packaging/mimir-capture/
  usr/
    bin/
      mimir-capture              (copiado por build.sh)
    lib/
      systemd/
        user/
          mimir-capture.service
    share/
      gnome-shell/
        extensions/
          mimir-window-tracker@mimir.app/
            metadata.json        (644)
            extension.js         (644)
```

### postinst actualizado

```bash
#!/bin/bash
if [ "$1" = "configure" ]; then
    echo ""
    echo "=== mimir-capture instalado ==="
    echo "Para activar la captura automatica, ejecuta como tu usuario:"
    echo "  systemctl --user daemon-reload"
    echo "  systemctl --user enable --now mimir-capture"
    echo ""
    echo "Si usas Wayland (GNOME), activa la extension:"
    echo "  gnome-extensions enable mimir-window-tracker@mimir.app"
    echo "  (Requiere cerrar sesion y volver a entrar)"
    echo ""
fi
```

### prerm actualizado

```bash
#!/bin/bash
if [ "$1" = "remove" ]; then
    echo ""
    echo "=== Desinstalando mimir-capture ==="
    echo "Si el servicio esta activo, desactivalo:"
    echo "  systemctl --user disable --now mimir-capture"
    echo ""
    echo "Si activaste la extension de GNOME, desactivala:"
    echo "  gnome-extensions disable mimir-window-tracker@mimir.app"
    echo ""
fi
```

### Dependencia xdotool

`xdotool` se mantiene en `Depends` por ahora (necesario para X11 fallback). En el futuro, cuando se soporte KDE/wlroots, podria pasar a `Recommends`.

## Testing

Archivo: `daemon/tests/test_platform_linux.py`

### Test deteccion de entorno

```python
async def test_setup_wayland_detection():
    """Detecta Wayland via XDG_SESSION_TYPE."""
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
        provider = LinuxProvider()
        # Mock _connect_wayland_bus para no necesitar D-Bus real
        provider._connect_wayland_bus = AsyncMock()
        await provider.setup()
        assert provider._use_wayland is True

async def test_setup_x11_detection():
    """Detecta X11 via XDG_SESSION_TYPE."""
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
        provider = LinuxProvider()
        await provider.setup()
        assert provider._use_wayland is False

async def test_setup_missing_session_type():
    """Sin XDG_SESSION_TYPE, usa X11 como fallback."""
    with patch.dict(os.environ, {}, clear=True):
        provider = LinuxProvider()
        await provider.setup()
        assert provider._use_wayland is False
```

### Test backend Wayland con mock D-Bus

```python
async def test_wayland_get_active_window():
    """Devuelve WindowInfo cuando la extension responde."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = AsyncMock()
    provider._wayland_iface.call_get_active_window.return_value = (1234, "org.gnome.Terminal", "~/projects")
    provider._get_app_name_sync = Mock(return_value="gnome-terminal")

    result = await provider.get_active_window()
    assert result is not None
    assert result.pid == 1234
    assert result.app_name == "gnome-terminal"  # de /proc, no de wm_class
    assert result.window_title == "~/projects"

async def test_wayland_no_focused_window():
    """Devuelve None cuando pid=0 (sin ventana activa)."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = AsyncMock()
    provider._wayland_iface.call_get_active_window.return_value = (0, "", "")

    result = await provider.get_active_window()
    assert result is None
```

### Test extension no disponible

```python
async def test_wayland_extension_not_available():
    """Devuelve None y loguea warning cuando la extension no esta."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = None
    provider._connect_wayland_bus = AsyncMock()  # no conecta

    result = await provider.get_active_window()
    assert result is None

async def test_wayland_connection_lost():
    """Reconecta si la conexion D-Bus se pierde."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = AsyncMock()
    provider._wayland_iface.call_get_active_window.side_effect = Exception("connection lost")

    result = await provider.get_active_window()
    assert result is None
    assert provider._wayland_iface is None  # reseteado para reconexion
```

### Test X11 sin cambios

Los tests existentes del poller y block_manager que mockean `get_active_window()` siguen pasando sin cambios.

### Test manual de la extension

Checklist para verificar en GNOME Wayland:
1. Instalar extension: `gnome-extensions install mimir-window-tracker@mimir.app`
2. Activar: `gnome-extensions enable mimir-window-tracker@mimir.app`
3. Verificar D-Bus: `gdbus call --session --dest org.mimir.WindowTracker --object-path /org/mimir/WindowTracker --method org.mimir.WindowTracker.GetActiveWindow`
4. Verificar con ventana activa: debe devolver `(pid, 'wm_class', 'title')`
5. Verificar sin ventana (overview): debe devolver `(0, '', '')`
6. Verificar con app XWayland (ej: VS Code): debe devolver pid y titulo correctos

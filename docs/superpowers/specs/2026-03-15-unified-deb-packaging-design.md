# Mimir — Empaquetado .deb unificado

## Contexto

Actualmente Mimir produce artefactos separados: un .deb de Tauri (solo la app) y binarios PyInstaller sueltos para el daemon. La instalacion requiere dos pasos manuales. El objetivo es que un companero pueda instalar Mimir con un solo `apt install`.

## Paquetes

### `mimir` (paquete principal)

Contenido:
- `/usr/bin/mimir` — App Tauri (frontend + backend Rust)
- `/usr/bin/mimir-server` — Servidor FastAPI (binario PyInstaller)
- Iconos, .desktop file y metadatos (generados por Tauri)

Dependencias apt: `libwebkit2gtk-4.1-0`, `libgtk-3-0`, `xdotool`

Comportamiento:
- El usuario abre Mimir desde el menu de aplicaciones o terminal
- La app Tauri lanza `mimir-server` como child process automaticamente
- Al cerrar la app, mata mimir-server

### `mimir-capture` (paquete opcional)

Contenido:
- `/usr/bin/mimir-capture` — Daemon de captura (binario PyInstaller)
- `/usr/lib/systemd/user/mimir-capture.service` — Servicio systemd user

Dependencias apt: `mimir`, `xdotool`

Conflicts/Replaces: `mimir-daemon` (limpieza de instalaciones manuales antiguas)

Comportamiento:
- `postinst`: muestra instrucciones al usuario para activar el servicio (no puede ejecutar `systemctl --user` como root durante la instalacion apt)
- `prerm`: muestra instrucciones para desactivar el servicio
- La captura corre en background independientemente de la app
- Escribe a la misma SQLite compartida (WAL mode)

## Cambios necesarios

### 1. build.sh — Nuevo target `deb`

Anadir un target `deb` al script de build que:
1. Construye los binarios del daemon (capture + server) via PyInstaller
2. Construye la app Tauri (que genera su propio .deb base)
3. Reempaqueta el .deb de Tauri inyectando `mimir-server` en `/usr/bin/`
   - Recalcular `Installed-Size` en el control file
   - Regenerar `md5sums` con el nuevo binario
   - Deduplicar dependencias en el campo `Depends`
   - Usar `dpkg-deb --build` para reempaquetar (gestiona formato de compresion automaticamente)
4. Genera un segundo .deb `mimir-capture` con `dpkg-deb --build`

La version se extrae dinamicamente de `tauri.conf.json` (via jq) para evitar hardcodear.

Actualizar el case statement y el usage string: `build.sh [capture|server|daemon|app|deb|all]`

### 2. Estructura de packaging

```
packaging/
  mimir-capture/
    DEBIAN/
      control          — metadatos del paquete (644)
      postinst         — muestra instrucciones de activacion (755)
      prerm            — muestra instrucciones de desactivacion (755)
    usr/
      bin/
        mimir-capture  — binario (copiado del build, 755)
      lib/
        systemd/
          user/
            mimir-capture.service
```

El .deb principal (`mimir`) se obtiene reempaquetando el .deb de Tauri con mimir-server inyectado.

#### DEBIAN/control (mimir-capture)

```
Package: mimir-capture
Version: ${VERSION}
Architecture: amd64
Depends: mimir, xdotool
Conflicts: mimir-daemon
Replaces: mimir-daemon
Maintainer: Jesus Lorenzo Limon
Section: utils
Priority: optional
Description: Mimir Activity Capture daemon
 Background daemon that captures window activity for Mimir time tracking.
 Runs as a systemd user service polling every 30 seconds.
```

#### DEBIAN/postinst (mimir-capture)

```bash
#!/bin/bash
if [ "$1" = "configure" ]; then
    echo ""
    echo "=== mimir-capture instalado ==="
    echo "Para activar la captura automatica, ejecuta como tu usuario:"
    echo "  systemctl --user daemon-reload"
    echo "  systemctl --user enable --now mimir-capture"
    echo ""
fi
```

#### DEBIAN/prerm (mimir-capture)

```bash
#!/bin/bash
if [ "$1" = "remove" ]; then
    echo ""
    echo "=== Desinstalando mimir-capture ==="
    echo "Si el servicio esta activo, desactivalo:"
    echo "  systemctl --user disable --now mimir-capture"
    echo ""
fi
```

### 3. server_process.rs — Actualizar busqueda de binario

Anadir `/usr/bin/mimir-server` como primera opcion en `find_server_binary()`, preservando el fallback existente que busca junto al ejecutable actual (necesario para AppImage y dev):

```rust
fn find_server_binary() -> Option<String> {
    let home = std::env::var("HOME").unwrap_or_default();
    let candidates = [
        "/usr/bin/mimir-server".to_string(),
        format!("{}/.local/bin/mimir-server", home),
        "dist/daemon/mimir-server".to_string(),
    ];

    for path in &candidates {
        if std::path::Path::new(path).exists() {
            return Some(path.clone());
        }
    }

    // Fallback: buscar junto al ejecutable actual (AppImage, dev)
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let candidate = dir.join("mimir-server");
            if candidate.exists() {
                return Some(candidate.to_string_lossy().to_string());
            }
        }
    }

    None
}
```

### 4. tauri.conf.json — Sin cambios en resources

Los binarios del daemon NO se empaquetan como Tauri resources/externalBin. Se inyectan directamente en el .deb como archivos adicionales. Esto mantiene la separacion limpia.

### 5. Servicio systemd (mimir-capture.service)

No hardcodear variables de entorno (DISPLAY, XAUTHORITY, DBUS). El session manager (GNOME, KDE, etc.) ya importa estas variables al entorno del systemd --user. `After=graphical-session.target` garantiza que el entorno grafico esta disponible.

```ini
[Unit]
Description=Mimir Activity Capture
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/mimir-capture
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

## Flujo de build

```
bash scripts/build.sh deb
  |
  +-- build_daemon()
  |     +-- PyInstaller -> dist/daemon/mimir-capture
  |     +-- PyInstaller -> dist/daemon/mimir-server
  |
  +-- build_app()
  |     +-- npm run tauri build -> .deb base
  |
  +-- package_deb()
        +-- Extraer version de tauri.conf.json
        +-- Desempaquetar .deb de Tauri
        +-- Inyectar mimir-server en usr/bin/
        +-- Recalcular Installed-Size y md5sums
        +-- Deduplicar Depends
        +-- Reempaquetar -> dist/mimir_${VERSION}_amd64.deb
        +-- Construir mimir-capture con dpkg-deb -> dist/mimir-capture_${VERSION}_amd64.deb
```

## Flujo de instalacion (usuario final)

```bash
# Instalar app (incluye mimir-server)
sudo apt install ./mimir_0.2.0_amd64.deb

# Opcional: instalar captura automatica
sudo apt install ./mimir-capture_0.2.0_amd64.deb

# Activar captura (instrucciones mostradas por postinst)
systemctl --user daemon-reload
systemctl --user enable --now mimir-capture

# Verificar
mimir                                          # Abre la app
systemctl --user status mimir-capture          # Estado de captura
curl http://127.0.0.1:9476/health              # Health capture
curl http://127.0.0.1:9477/health              # Health server (con app abierta)
```

## Desinstalacion

```bash
# Desactivar captura primero
systemctl --user disable --now mimir-capture

sudo apt remove mimir-capture   # Quita captura
sudo apt remove mimir            # Quita la app
```

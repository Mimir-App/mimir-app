# Unified .deb Packaging Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create two .deb packages — `mimir` (app + server) and `mimir-capture` (capture daemon + systemd service) — so a user can install Mimir with `sudo apt install ./mimir*.deb`.

**Architecture:** Repackage the Tauri-generated .deb to inject `mimir-server` into `/usr/bin/`, then build a separate `mimir-capture` .deb with `dpkg-deb`. The build script orchestrates PyInstaller builds, Tauri build, and .deb assembly.

**Tech Stack:** Bash (build script), dpkg-deb (packaging), PyInstaller (daemon binaries), Tauri 2 (app), systemd (capture service)

**Spec:** `docs/superpowers/specs/2026-03-15-unified-deb-packaging-design.md`

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| Modify | `scripts/build.sh` | Add `deb` target with `package_deb()` function |
| Modify | `src-tauri/src/server_process.rs:7-29` | Add `/usr/bin/mimir-server` as first candidate |
| Create | `packaging/mimir-capture/DEBIAN/control` | Package metadata for mimir-capture |
| Create | `packaging/mimir-capture/DEBIAN/postinst` | Post-install instructions for user |
| Create | `packaging/mimir-capture/DEBIAN/prerm` | Pre-remove instructions for user |
| Create | `packaging/mimir-capture/usr/lib/systemd/user/mimir-capture.service` | Systemd user service unit |

---

## Chunk 1: Packaging Templates

### Task 1: Create mimir-capture packaging structure

**Files:**
- Create: `packaging/mimir-capture/DEBIAN/control`
- Create: `packaging/mimir-capture/DEBIAN/postinst`
- Create: `packaging/mimir-capture/DEBIAN/prerm`
- Create: `packaging/mimir-capture/usr/lib/systemd/user/mimir-capture.service`

- [ ] **Step 1: Create DEBIAN/control**

```
Package: mimir-capture
Version: 0.2.0
Architecture: amd64
Depends: mimir, xdotool
Conflicts: mimir-daemon
Replaces: mimir-daemon
Maintainer: Jesus Lorenzo Limon
Section: utils
Priority: optional
Installed-Size: 0
Description: Mimir Activity Capture daemon
 Background daemon that captures window activity for Mimir time tracking.
 Runs as a systemd user service polling every 30 seconds.
```

Note: `Installed-Size` and `Version` will be overwritten dynamically by build.sh.

- [ ] **Step 2: Create DEBIAN/postinst**

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

- [ ] **Step 3: Create DEBIAN/prerm**

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

- [ ] **Step 4: Create systemd service file**

File: `packaging/mimir-capture/usr/lib/systemd/user/mimir-capture.service`

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

- [ ] **Step 5: Set correct permissions**

Run: `chmod 755 packaging/mimir-capture/DEBIAN/postinst packaging/mimir-capture/DEBIAN/prerm`

- [ ] **Step 6: Commit**

```bash
git add packaging/
git commit -m "feat: add mimir-capture .deb packaging templates"
```

---

## Chunk 2: Update server_process.rs

### Task 2: Add /usr/bin/mimir-server to binary search path

**Files:**
- Modify: `src-tauri/src/server_process.rs:7-29`

- [ ] **Step 1: Add /usr/bin/mimir-server as first candidate**

In `find_server_binary()`, change the candidates array from:

```rust
let candidates = [
    format!("{}/.local/bin/mimir-server", home),
    "dist/daemon/mimir-server".to_string(),
];
```

To:

```rust
let candidates = [
    "/usr/bin/mimir-server".to_string(),
    format!("{}/.local/bin/mimir-server", home),
    "dist/daemon/mimir-server".to_string(),
];
```

The rest of the function (exe parent fallback + python3 fallback) stays unchanged.

- [ ] **Step 2: Verify Rust compiles**

Run: `cd src-tauri && cargo check 2>&1 | tail -5`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/server_process.rs
git commit -m "feat: add /usr/bin/mimir-server to binary search path for .deb installs"
```

---

## Chunk 3: Update build.sh with deb target

### Task 3: Add package_deb() function and deb target to build.sh

**Files:**
- Modify: `scripts/build.sh`

- [ ] **Step 1: Add package_deb() function after build_app()**

This function does three things:
1. Repackages the Tauri .deb to inject mimir-server
2. Builds the mimir-capture .deb from the packaging/ templates
3. Outputs both to `dist/packages/`

```bash
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

    # Regenerar md5sums
    (cd "$REPACK_DIR" && find usr -type f -exec md5sum {} \;) > "$REPACK_DIR/DEBIAN/md5sums"

    # Recalcular Installed-Size (en KB)
    INSTALLED_SIZE=$(du -sk "$REPACK_DIR" --exclude=DEBIAN | cut -f1)
    sed -i "s/^Installed-Size:.*/Installed-Size: $INSTALLED_SIZE/" "$REPACK_DIR/DEBIAN/control"

    # Deduplicar Depends
    DEPS=$(grep "^Depends:" "$REPACK_DIR/DEBIAN/control" | sed 's/^Depends: //' | tr ',' '\n' | sed 's/^ *//' | sort -u | paste -sd', ')
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
```

- [ ] **Step 2: Add `deb` target to the case statement**

After the `all)` case, add `deb)` before `*)`:

```bash
    deb)
        build_daemon
        build_app
        package_deb
        ;;
```

- [ ] **Step 3: Update usage string**

Change:
```bash
        echo "Uso: build.sh [capture|server|daemon|app|all]"
```
To:
```bash
        echo "Uso: build.sh [capture|server|daemon|app|deb|all]"
```

- [ ] **Step 4: Update artefacts section at the end of the script**

After the AppImage check, add:

```bash
MIMIR_DEB=$(ls "$PROJECT_DIR/dist/packages/mimir_"*.deb 2>/dev/null | head -1)
if [ -n "$MIMIR_DEB" ]; then
    echo "  Mimir .deb: $MIMIR_DEB ($(du -h "$MIMIR_DEB" | cut -f1))"
fi
CAPTURE_DEB=$(ls "$PROJECT_DIR/dist/packages/mimir-capture_"*.deb 2>/dev/null | head -1)
if [ -n "$CAPTURE_DEB" ]; then
    echo "  Capture .deb: $CAPTURE_DEB ($(du -h "$CAPTURE_DEB" | cut -f1))"
fi
```

- [ ] **Step 5: Test the build script syntax**

Run: `bash -n scripts/build.sh`
Expected: No output (no syntax errors)

- [ ] **Step 6: Commit**

```bash
git add scripts/build.sh
git commit -m "feat: add 'deb' target to build.sh for unified .deb packaging"
```

---

## Chunk 4: Build and Verify

### Task 4: Run full build and verify packages

- [ ] **Step 1: Run the full deb build**

Run: `bash scripts/build.sh deb`
Expected: Three phases complete — daemon binaries, Tauri app, .deb packages

- [ ] **Step 2: Verify output files**

Run: `ls -lh dist/packages/*.deb`
Expected: Two .deb files:
- `dist/packages/mimir_0.2.0_amd64.deb` (~75 MB — Tauri app + mimir-server)
- `dist/packages/mimir-capture_0.2.0_amd64.deb` (~25 MB — capture binary + service)

- [ ] **Step 3: Inspect mimir .deb contents**

Run: `dpkg-deb -c dist/packages/mimir_0.2.0_amd64.deb | grep usr/bin`
Expected: Both `/usr/bin/mimir` and `/usr/bin/mimir-server` present

- [ ] **Step 4: Inspect mimir .deb control**

Run: `dpkg-deb -I dist/packages/mimir_0.2.0_amd64.deb`
Expected: No duplicate dependencies, reasonable Installed-Size

- [ ] **Step 5: Inspect mimir-capture .deb contents**

Run: `dpkg-deb -c dist/packages/mimir-capture_0.2.0_amd64.deb`
Expected:
- `usr/bin/mimir-capture`
- `usr/lib/systemd/user/mimir-capture.service`

- [ ] **Step 6: Inspect mimir-capture control**

Run: `dpkg-deb -I dist/packages/mimir-capture_0.2.0_amd64.deb`
Expected: Depends includes `mimir` and `xdotool`

- [ ] **Step 7: Test install mimir .deb**

Run: `sudo apt install ./dist/packages/mimir_0.2.0_amd64.deb`
Verify: `which mimir && which mimir-server`

- [ ] **Step 8: Test install mimir-capture .deb**

Run: `sudo apt install ./dist/packages/mimir-capture_0.2.0_amd64.deb`
Verify: `which mimir-capture && cat /usr/lib/systemd/user/mimir-capture.service`

- [ ] **Step 9: Test uninstall**

Run: `sudo apt remove mimir-capture mimir`
Verify: `which mimir-capture && which mimir && which mimir-server` all return "not found"

- [ ] **Step 10: Final commit**

```bash
git add -A
git commit -m "feat: unified .deb packaging for mimir and mimir-capture"
```

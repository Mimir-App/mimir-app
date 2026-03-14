# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para mimir-daemon."""

from pathlib import Path

block_cipher = None
daemon_dir = Path(SPECPATH)

a = Analysis(
    [str(daemon_dir / "mimir_daemon" / "_pyinstaller_entry.py")],
    pathex=[str(daemon_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "mimir_daemon.platform.linux",
        "mimir_daemon.integrations.odoo_v11",
        "mimir_daemon.integrations.odoo_v16",
        "mimir_daemon.integrations.mock",
        "mimir_daemon.ai.gemini",
        "mimir_daemon.ai.claude_provider",
        "mimir_daemon.ai.openai_provider",
        "mimir_daemon.sources.gitlab",
        "aiosqlite",
        "pystray",
        "PIL",
        "dbus_next",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="mimir-daemon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

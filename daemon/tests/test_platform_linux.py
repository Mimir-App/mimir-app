"""Tests para el platform layer Linux (X11 + Wayland)."""

import os
import subprocess
import pytest
from unittest.mock import patch, AsyncMock, Mock, MagicMock

from mimir_daemon.platform.linux import LinuxProvider
from mimir_daemon.platform.base import WindowInfo


@pytest.mark.asyncio
async def test_setup_detects_wayland():
    """Detecta Wayland via XDG_SESSION_TYPE."""
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
        provider = LinuxProvider()
        provider._connect_wayland_bus = AsyncMock()
        provider._dbus_task = None
        with patch.object(provider, '_listen_dbus', new_callable=AsyncMock):
            await provider.setup()
        assert provider._use_wayland is True
        provider._connect_wayland_bus.assert_called_once()


@pytest.mark.asyncio
async def test_setup_detects_x11():
    """Detecta X11 via XDG_SESSION_TYPE."""
    mock_result = MagicMock(returncode=0, stdout="12345\n", stderr="")
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}), \
         patch("subprocess.run", return_value=mock_result):
        provider = LinuxProvider()
        provider._dbus_task = None
        with patch.object(provider, '_listen_dbus', new_callable=AsyncMock):
            await provider.setup()
        assert provider._use_wayland is False


@pytest.mark.asyncio
async def test_setup_missing_session_type_defaults_x11():
    """Sin XDG_SESSION_TYPE usa X11 como fallback."""
    env = {k: v for k, v in os.environ.items() if k != "XDG_SESSION_TYPE"}
    mock_result = MagicMock(returncode=0, stdout="12345\n", stderr="")
    with patch.dict(os.environ, env, clear=True), \
         patch("subprocess.run", return_value=mock_result):
        provider = LinuxProvider()
        provider._dbus_task = None
        with patch.object(provider, '_listen_dbus', new_callable=AsyncMock):
            await provider.setup()
        assert provider._use_wayland is False


@pytest.mark.asyncio
async def test_wayland_get_active_window_returns_window_info():
    """Backend Wayland devuelve WindowInfo cuando la extension responde."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = AsyncMock()
    provider._wayland_iface.call_get_active_window = AsyncMock(
        return_value=(1234, "org.gnome.Terminal", "~/projects")
    )
    with patch.object(LinuxProvider, '_get_app_name_sync', return_value="gnome-terminal"):
        result = await provider.get_active_window()

    assert result is not None
    assert result.pid == 1234
    assert result.app_name == "gnome-terminal"
    assert result.window_title == "~/projects"


@pytest.mark.asyncio
async def test_wayland_no_focused_window_returns_none():
    """Backend Wayland devuelve None cuando pid=0."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = AsyncMock()
    provider._wayland_iface.call_get_active_window = AsyncMock(
        return_value=(0, "", "")
    )
    result = await provider.get_active_window()
    assert result is None


@pytest.mark.asyncio
async def test_wayland_extension_not_available():
    """Sin extension devuelve None y no crashea."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = None
    provider._connect_wayland_bus = AsyncMock()

    result = await provider.get_active_window()
    assert result is None


@pytest.mark.asyncio
async def test_wayland_connection_lost_resets_iface():
    """Si la conexion D-Bus se pierde, resetea iface para reconectar."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = AsyncMock()
    provider._wayland_iface.call_get_active_window = AsyncMock(
        side_effect=Exception("connection lost")
    )
    provider._wayland_bus = Mock()

    result = await provider.get_active_window()
    assert result is None
    assert provider._wayland_iface is None
    assert provider._wayland_bus is None


@pytest.mark.asyncio
async def test_x11_backend_used_when_not_wayland():
    """En X11, usa el backend xdotool."""
    provider = LinuxProvider()
    provider._use_wayland = False
    provider._get_active_window_x11 = AsyncMock(
        return_value=WindowInfo(pid=1, app_name="code", window_title="test.py")
    )

    result = await provider.get_active_window()
    assert result is not None
    assert result.app_name == "code"
    provider._get_active_window_x11.assert_called_once()


@pytest.mark.asyncio
async def test_setup_x11_xdotool_diagnostic_success():
    """Setup en X11 logea verificacion exitosa de xdotool."""
    mock_result = MagicMock(returncode=0, stdout="12345\n", stderr="")
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        provider = LinuxProvider()
        provider._dbus_task = None
        with patch.object(provider, '_listen_dbus', new_callable=AsyncMock):
            await provider.setup()
        mock_run.assert_called_once_with(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, timeout=3
        )


@pytest.mark.asyncio
async def test_setup_x11_xdotool_not_installed():
    """Setup en X11 logea error si xdotool no esta instalado."""
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}), \
         patch("subprocess.run", side_effect=FileNotFoundError):
        provider = LinuxProvider()
        provider._dbus_task = None
        with patch.object(provider, '_listen_dbus', new_callable=AsyncMock):
            await provider.setup()
        # No debe crashear
        assert provider._use_wayland is False


@pytest.mark.asyncio
async def test_setup_x11_xdotool_fails():
    """Setup en X11 logea error si xdotool falla."""
    mock_result = MagicMock(returncode=1, stdout="", stderr="No window found")
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}), \
         patch("subprocess.run", return_value=mock_result):
        provider = LinuxProvider()
        provider._dbus_task = None
        with patch.object(provider, '_listen_dbus', new_callable=AsyncMock):
            await provider.setup()
        assert provider._use_wayland is False


@pytest.mark.asyncio
async def test_backend_property():
    """La propiedad backend devuelve el tipo correcto."""
    provider = LinuxProvider()
    assert provider.backend == "x11"
    provider._use_wayland = True
    assert provider.backend == "wayland"

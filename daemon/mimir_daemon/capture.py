"""Entry point del proceso de captura de actividad.

Proceso ligero que corre siempre como servicio systemd.
Solo captura actividad y escribe bloques en SQLite.
Expone un endpoint HTTP mínimo (/health, /status) en puerto 9476.
"""

import argparse
import asyncio
import logging
import sys

import uvicorn
from fastapi import FastAPI

from .config import DaemonConfig
from .db import Database
from .platform import get_platform_provider
from .signal_aggregator import SignalAggregator
from .poller import Poller
from .tray import TrayIcon

logger = logging.getLogger("mimir_capture")

from . import __version__ as VERSION  # noqa: E402
CAPTURE_PORT = 9476


def create_capture_app(poller: Poller, platform: object | None = None, version: str = VERSION) -> FastAPI:
    """Crea la app FastAPI mínima del capture."""
    from datetime import datetime, timezone

    app = FastAPI(title="Mimir Capture", version=version)
    start_time = datetime.now(timezone.utc)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "service": "capture", "version": version}

    @app.get("/status")
    async def status() -> dict:
        now = datetime.now(timezone.utc)
        uptime = int((now - start_time).total_seconds())
        return {
            "running": poller.is_running,
            "mode": "paused" if poller._paused else "active",
            "uptime_seconds": uptime,
            "last_poll": poller.last_poll.isoformat() if poller.last_poll else None,
            "backend": getattr(platform, 'backend', 'unknown') if platform else "unknown",
            "version": version,
        }

    return app


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Mimir Capture Daemon")
    parser.add_argument(
        "--port", type=int, default=CAPTURE_PORT,
        help=f"Puerto HTTP (por defecto: {CAPTURE_PORT})",
    )
    return parser.parse_args()


async def run_capture(args: argparse.Namespace) -> None:
    """Arranca el proceso de captura."""
    config = DaemonConfig.load()
    config.save()

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Iniciando Mimir Capture v%s", VERSION)

    db = Database(config.db_path)
    await db.connect()

    platform = get_platform_provider()
    await platform.setup()

    aggregator = SignalAggregator(
        db=db,
        inactivity_threshold=config.inactivity_threshold,
        browser_apps=set(config.browser_apps) if config.browser_apps else None,
        transient_apps=set(config.transient_apps) if config.transient_apps else None,
    )

    await aggregator.recover_open_blocks()

    poller = Poller(
        config=config,
        db=db,
        platform=platform,
        aggregator=aggregator,
    )

    app = create_capture_app(poller=poller, platform=platform, version=VERSION)

    tray = TrayIcon(
        on_mode_change=lambda mode: (
            poller.pause() if mode == "paused" else poller.resume()
        ),
        on_quit=lambda: poller.stop(),
    )
    tray.start()

    poller_task = asyncio.create_task(poller.run())

    uvicorn_config = uvicorn.Config(
        app,
        host=config.host,
        port=args.port,
        log_level=config.log_level.lower(),
    )
    server = uvicorn.Server(uvicorn_config)

    logger.info("Capture HTTP en http://%s:%d", config.host, args.port)

    try:
        await server.serve()
    except asyncio.CancelledError:
        pass
    finally:
        poller.stop()
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass
        tray.stop()
        await platform.teardown()
        await db.close()
        logger.info("Capture detenido")


def main() -> None:
    """Entry point CLI."""
    args = parse_args()
    try:
        asyncio.run(run_capture(args))
    except KeyboardInterrupt:
        logger.info("Capture interrumpido por usuario")
        sys.exit(0)


if __name__ == "__main__":
    main()

"""Entry point del daemon Mimir."""

import argparse
import asyncio
import logging
import sys

import uvicorn

from .config import DaemonConfig
from .db import Database
from .platform import get_platform_provider
from .block_manager import BlockManager
from .integrations.registry import IntegrationRegistry
from .poller import Poller
from .server import create_app
from .ai.service import AIService
from .tray import TrayIcon

logger = logging.getLogger("mimir_daemon")

VERSION = "0.1.0"


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Mimir Activity Capture Daemon")
    parser.add_argument(
        "--mock", action="store_true",
        help="Usar datos mock en lugar de conectar con Odoo/GitLab reales",
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="Puerto HTTP (por defecto: 9477)",
    )
    return parser.parse_args()


def setup_integrations(registry: IntegrationRegistry, *, mock: bool) -> None:
    """Configura las integraciones de timesheet."""
    if mock:
        from .integrations.mock import MockTimesheetClient
        client = MockTimesheetClient()
        registry.set_timesheet_client(client)
        logger.info("Usando cliente mock de timesheet")
    else:
        logger.info("Sin cliente de timesheet configurado (conectar via config)")


async def run_daemon(args: argparse.Namespace) -> None:
    """Arranca el daemon completo."""
    # Cargar configuracion
    config = DaemonConfig.load()
    if args.port:
        config.port = args.port
    config.save()  # Persiste defaults si no existia

    # Configurar logging
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Iniciando Mimir Daemon v%s", VERSION)
    if args.mock:
        logger.info("Modo mock activado")

    # Inicializar componentes
    db = Database(config.db_path)
    await db.connect()

    platform = get_platform_provider()
    await platform.setup()

    ai_service = AIService(db=db, provider=None)

    block_manager = BlockManager(
        db=db,
        inherit_threshold=config.inherit_threshold,
        ai_service=ai_service,
    )

    # Recuperar bloques abiertos de sesion anterior
    await block_manager.recover_open_blocks()

    # Integraciones
    registry = IntegrationRegistry()
    setup_integrations(registry, mock=args.mock)

    poller = Poller(
        config=config,
        db=db,
        platform=platform,
        block_manager=block_manager,
    )

    # Crear servidor HTTP
    app = create_app(db=db, poller=poller, registry=registry, ai_service=ai_service, version=VERSION)

    # Tray icon
    tray = TrayIcon(
        on_mode_change=lambda mode: (
            poller.pause() if mode == "paused" else poller.resume()
        ),
        on_quit=lambda: poller.stop(),
    )
    tray.start()

    # Arrancar poller y servidor
    poller_task = asyncio.create_task(poller.run())

    uvicorn_config = uvicorn.Config(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
    )
    server = uvicorn.Server(uvicorn_config)

    logger.info("Servidor HTTP en http://%s:%d", config.host, config.port)

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
        logger.info("Daemon detenido")


def main() -> None:
    """Entry point CLI."""
    args = parse_args()
    try:
        asyncio.run(run_daemon(args))
    except KeyboardInterrupt:
        logger.info("Daemon interrumpido por usuario")
        sys.exit(0)


if __name__ == "__main__":
    main()

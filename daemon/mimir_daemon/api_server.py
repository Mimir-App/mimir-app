"""Entry point del servidor API.

Proceso lanzado por la app Tauri cuando se abre.
Provee la API completa: bloques CRUD, Odoo, GitLab, IA, config.
Se cierra cuando la app Tauri se cierra.
"""

import argparse
import asyncio
import logging
import sys

import uvicorn

from .config import DaemonConfig
from .db import Database
from .integrations.registry import IntegrationRegistry
from .sources.registry import SourceRegistry
from .ai.service import AIService
from . import __version__
from .server import create_server_app

logger = logging.getLogger("mimir_server")

VERSION = __version__
SERVER_PORT = 9477


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Mimir API Server")
    parser.add_argument(
        "--port", type=int, default=SERVER_PORT,
        help=f"Puerto HTTP (por defecto: {SERVER_PORT})",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Usar datos mock en lugar de conectar con Odoo/GitLab reales",
    )
    return parser.parse_args()


async def run_server(args: argparse.Namespace) -> None:
    """Arranca el servidor API."""
    config = DaemonConfig.load()

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Iniciando Mimir Server v%s", VERSION)

    db = Database(config.db_path)
    await db.connect()

    registry = IntegrationRegistry()
    if args.mock:
        from .integrations.mock import MockTimesheetClient
        registry.set_timesheet_client(MockTimesheetClient())
        logger.info("Usando cliente mock de timesheet")

    source_registry = SourceRegistry()
    ai_service = AIService(db=db, provider=None)

    app = create_server_app(
        db=db,
        registry=registry,
        ai_service=ai_service,
        source_registry=source_registry,
        version=VERSION,
    )

    uvicorn_config = uvicorn.Config(
        app,
        host=config.host,
        port=args.port,
        log_level=config.log_level.lower(),
    )
    server = uvicorn.Server(uvicorn_config)

    logger.info("Server HTTP en http://%s:%d", config.host, args.port)

    try:
        await server.serve()
    except asyncio.CancelledError:
        pass
    finally:
        await db.close()
        logger.info("Server detenido")


def main() -> None:
    """Entry point CLI."""
    args = parse_args()
    try:
        asyncio.run(run_server(args))
    except KeyboardInterrupt:
        logger.info("Server interrumpido por usuario")
        sys.exit(0)


if __name__ == "__main__":
    main()

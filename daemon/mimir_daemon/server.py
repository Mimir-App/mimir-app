"""Servidor HTTP local (FastAPI) para comunicacion con la app Tauri."""

# NOTA: NO usar 'from __future__ import annotations' aquí.
# Rompe la inspección de tipos de FastAPI/Pydantic para body params.

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .db import Database
from .integrations.registry import IntegrationRegistry
from .notifications import NotificationService
from .routers import (
    blocks,
    config_router,
    context_mappings,
    github_oauth,
    google,
    items,
    notifications,
    odoo,
    signals,
    vcs,
)
from .sources.registry import SourceRegistry

logger = logging.getLogger(__name__)


def create_server_app(
    db: Database,
    registry: IntegrationRegistry | None = None,
    ai_service: "AIService | None" = None,
    source_registry: SourceRegistry | None = None,
    calendar_client: "GoogleCalendarClient | None" = None,
    notification_service: NotificationService | None = None,
    version: str = __version__,
) -> FastAPI:
    """Crea la aplicacion FastAPI."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifecycle: arranca servicios en background."""
        task = None
        if notification_service:
            task = asyncio.create_task(notification_service.run())
        yield
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="Mimir Server", version=version, lifespan=lifespan)
    start_time = datetime.now(timezone.utc)

    # Shared state accesible desde routers via request.app.state
    app.state.db = db
    app.state.registry = registry or IntegrationRegistry()
    app.state.source_registry = source_registry or SourceRegistry()
    app.state.ai_service = ai_service
    app.state.calendar_client = calendar_client
    app.state.app_config = {}  # mutable dict, actualizado por config_router

    # CORS para que Tauri pueda conectarse
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Health & Status (usan start_time local) ---

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": version}

    @app.get("/status")
    async def status() -> dict:
        now = datetime.now(timezone.utc)
        uptime = int((now - start_time).total_seconds())
        blocks_today = await db.count_blocks_today()
        return {
            "running": True,
            "mode": "active",
            "uptime_seconds": uptime,
            "last_poll": None,
            "blocks_today": blocks_today,
            "version": version,
        }

    # --- Routers ---
    app.include_router(blocks.router)
    app.include_router(signals.router)
    app.include_router(context_mappings.router)
    app.include_router(notifications.router)
    app.include_router(items.router)
    app.include_router(odoo.router)
    app.include_router(google.router)
    app.include_router(config_router.router)
    app.include_router(vcs.router)
    app.include_router(github_oauth.router)

    return app

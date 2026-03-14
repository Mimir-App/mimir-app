"""Servidor HTTP local (FastAPI) para comunicacion con la app Tauri."""

# NOTA: NO usar 'from __future__ import annotations' aquí.
# Rompe la inspección de tipos de FastAPI/Pydantic para body params.

import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .db import Database
from .integrations.base import TimesheetEntryData
from .integrations.registry import IntegrationRegistry
from .poller import Poller

logger = logging.getLogger(__name__)


def create_app(
    db: Database,
    poller: Poller,
    registry: IntegrationRegistry | None = None,
    ai_service: "AIService | None" = None,
    version: str = "0.1.0",
) -> FastAPI:
    """Crea la aplicacion FastAPI."""

    app = FastAPI(title="Mimir Daemon", version=version)
    start_time = datetime.now(timezone.utc)
    _registry = registry or IntegrationRegistry()

    # Almacena la configuracion recibida desde Tauri
    _app_config: dict = {}

    # CORS para que Tauri pueda conectarse
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Health & Status ---

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": version}

    @app.get("/status")
    async def status() -> dict:
        now = datetime.now(timezone.utc)
        uptime = int((now - start_time).total_seconds())
        blocks_today = await db.count_blocks_today()
        return {
            "running": poller.is_running,
            "mode": "paused" if poller._paused else "active",
            "uptime_seconds": uptime,
            "last_poll": poller.last_poll.isoformat() if poller.last_poll else None,
            "blocks_today": blocks_today,
            "version": version,
        }

    # --- Mode ---

    class ModeRequest(BaseModel):
        mode: str

    @app.post("/mode")
    async def set_mode(req: ModeRequest) -> dict:
        if req.mode == "paused":
            poller.pause()
        elif req.mode in ("active", "silent"):
            poller.resume()
        else:
            raise HTTPException(400, f"Modo no valido: {req.mode}")
        return {"mode": req.mode}

    # --- Blocks ---

    @app.get("/blocks")
    async def get_blocks(date: str = Query(default=None)) -> list[dict]:
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return await db.get_blocks_by_date(date)

    @app.get("/blocks/summary")
    async def get_blocks_summary(date: str = Query(default=None)) -> dict:
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return await db.get_blocks_summary(date)

    @app.get("/blocks/{block_id}")
    async def get_block(block_id: int) -> dict:
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        return block

    @app.post("/blocks/{block_id}/confirm")
    async def confirm_block(block_id: int) -> dict:
        """Confirma un bloque para envio a Odoo."""
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        if block.get("status") == "synced":
            raise HTTPException(400, "El bloque ya fue enviado a Odoo")
        await db.update_block(block_id, status="confirmed")
        logger.info("Bloque %d confirmado", block_id)
        return {"status": "confirmed"}

    class BlockUpdateRequest(BaseModel):
        user_description: str | None = None
        odoo_project_id: int | None = None
        odoo_task_id: int | None = None
        odoo_project_name: str | None = None
        odoo_task_name: str | None = None

    @app.put("/blocks/{block_id}")
    async def update_block(block_id: int, req: BlockUpdateRequest) -> dict:
        """Actualiza campos de un bloque.

        Si el bloque ya fue enviado a Odoo (synced), se marca como
        pending para permitir reenvio con la actualizacion.
        """
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if updates:
            # Si el bloque ya fue sincronizado, marcarlo como pending para reenvio
            if block.get("status") == "synced":
                updates["status"] = "confirmed"
                logger.info("Bloque %d editado tras sincronizar, marcado como confirmed para reenvio", block_id)
            await db.update_block(block_id, **updates)
        return {"status": "updated"}

    class SyncRequest(BaseModel):
        block_ids: list[int]

    @app.post("/blocks/sync")
    async def sync_blocks(req: SyncRequest) -> dict:
        """Sincroniza bloques confirmados con Odoo.

        Para cada bloque:
        - Si no tiene remote_id -> create_entry
        - Si ya tiene remote_id (fue editado tras sync) -> update_entry
        - sync_status: pending -> sent (con remote_id) o error (con sync_error)
        """
        client = _registry.timesheet
        if not client:
            raise HTTPException(503, "No hay cliente de timesheet configurado")

        synced = 0
        errors = []
        for block_id in req.block_ids:
            block = await db.get_block_by_id(block_id)
            if not block:
                errors.append({"block_id": block_id, "error": "No encontrado"})
                continue

            if not block.get("odoo_project_id"):
                errors.append({"block_id": block_id, "error": "Sin proyecto Odoo asignado"})
                await db.update_block(block_id, status="error", sync_error="Sin proyecto Odoo asignado")
                continue

            description = (
                block.get("user_description")
                or block.get("ai_description")
                or f"{block.get('app_name', '')} — {block.get('window_title', '')}"
            )

            entry = TimesheetEntryData(
                date=block["start_time"][:10],
                project_id=block["odoo_project_id"],
                task_id=block.get("odoo_task_id"),
                description=description,
                hours=round(block["duration_minutes"] / 60, 2),
            )

            try:
                existing_remote_id = block.get("odoo_entry_id")
                if existing_remote_id:
                    # Update: el bloque ya fue enviado previamente
                    await client.update_entry(existing_remote_id, entry)
                    await db.update_block(
                        block_id,
                        status="synced",
                        sync_error=None,
                    )
                    synced += 1
                    logger.info("Bloque %d re-sincronizado -> Odoo entry %d (update)",
                                block_id, existing_remote_id)
                else:
                    # Create: primer envio
                    remote_id = await client.create_entry(entry)
                    await db.update_block(
                        block_id,
                        status="synced",
                        odoo_entry_id=remote_id,
                        sync_error=None,
                    )
                    synced += 1
                    logger.info("Bloque %d sincronizado -> Odoo entry %d (create)",
                                block_id, remote_id)
            except Exception as e:
                error_msg = str(e)
                errors.append({"block_id": block_id, "error": error_msg})
                await db.update_block(block_id, status="error", sync_error=error_msg)
                logger.error("Error sincronizando bloque %d: %s", block_id, error_msg)

        return {"synced": synced, "errors": errors}

    @app.post("/blocks/{block_id}/retry")
    async def retry_sync_block(block_id: int) -> dict:
        """Reintenta la sincronizacion de un bloque con error."""
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        if block.get("status") != "error":
            raise HTTPException(400, "Solo se pueden reintentar bloques con error")

        client = _registry.timesheet
        if not client:
            raise HTTPException(503, "No hay cliente de timesheet configurado")

        if not block.get("odoo_project_id"):
            raise HTTPException(400, "Sin proyecto Odoo asignado")

        description = (
            block.get("user_description")
            or block.get("ai_description")
            or f"{block.get('app_name', '')} — {block.get('window_title', '')}"
        )

        entry = TimesheetEntryData(
            date=block["start_time"][:10],
            project_id=block["odoo_project_id"],
            task_id=block.get("odoo_task_id"),
            description=description,
            hours=round(block["duration_minutes"] / 60, 2),
        )

        try:
            existing_remote_id = block.get("odoo_entry_id")
            if existing_remote_id:
                await client.update_entry(existing_remote_id, entry)
                await db.update_block(
                    block_id,
                    status="synced",
                    sync_error=None,
                )
                logger.info("Reintento exitoso bloque %d -> Odoo entry %d (update)",
                            block_id, existing_remote_id)
            else:
                remote_id = await client.create_entry(entry)
                await db.update_block(
                    block_id,
                    status="synced",
                    odoo_entry_id=remote_id,
                    sync_error=None,
                )
                logger.info("Reintento exitoso bloque %d -> Odoo entry %d (create)",
                            block_id, remote_id)
            return {"status": "synced"}
        except Exception as e:
            error_msg = str(e)
            await db.update_block(block_id, sync_error=error_msg)
            logger.error("Error en reintento de bloque %d: %s", block_id, error_msg)
            raise HTTPException(502, f"Error sincronizando: {error_msg}")

    @app.delete("/blocks/{block_id}")
    async def delete_block(block_id: int) -> dict:
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        await db.delete_block(block_id)
        return {"status": "deleted"}

    @app.post("/blocks/{block_id}/generate-description")
    async def generate_description(block_id: int) -> dict:
        """Genera o regenera descripción IA para un bloque."""
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")

        from .ai.base import DescriptionRequest
        _ai = ai_service
        if not _ai:
            from .ai.service import AIService as _AIS
            _ai = _AIS(db=db, provider=None)

        request = DescriptionRequest(
            app_name=block.get("app_name", ""),
            window_title=block.get("window_title", ""),
            project_path=block.get("project_path"),
            git_branch=block.get("git_branch"),
            git_remote=block.get("git_remote"),
            duration_minutes=block.get("duration_minutes", 0),
            window_titles=json.loads(block["window_titles_json"])
            if block.get("window_titles_json") else None,
            user_role=_app_config.get("ai_user_role", "technical"),
            user_context=_app_config.get("ai_custom_context", ""),
        )

        result = await _ai.generate(request)
        await db.update_block(
            block_id,
            ai_description=result.description,
            ai_confidence=result.confidence,
        )

        return {
            "description": result.description,
            "confidence": result.confidence,
            "cached": result.cached,
        }

    # --- Odoo ---

    @app.get("/odoo/projects")
    async def get_odoo_projects() -> list:
        """Obtiene proyectos de Odoo. Devuelve lista vacia si no hay cliente."""
        client = _registry.timesheet
        if not client:
            return []
        try:
            return await client.get_projects()
        except Exception as e:
            logger.error("Error obteniendo proyectos de Odoo: %s", e)
            return []

    @app.get("/odoo/tasks/{project_id}")
    async def get_odoo_tasks(project_id: int) -> list:
        """Obtiene tareas de un proyecto en Odoo."""
        client = _registry.timesheet
        if not client:
            return []
        try:
            return await client.get_tasks(project_id)
        except Exception as e:
            logger.error("Error obteniendo tareas de Odoo (proyecto %d): %s", project_id, e)
            return []

    @app.get("/odoo/entries")
    async def get_odoo_entries(
        date_from: str = Query(alias="from"),
        date_to: str = Query(alias="to"),
    ) -> list:
        """Obtiene entradas de timesheet de Odoo en un rango."""
        client = _registry.timesheet
        if not client:
            return []
        try:
            return await client.get_entries(date_from, date_to)
        except Exception as e:
            logger.error("Error obteniendo entradas de Odoo: %s", e)
            return []

    # --- Config (recibe configuracion desde Tauri) ---

    class AppConfigRequest(BaseModel):
        """Configuracion de la app recibida desde Tauri."""
        odoo_url: str = ""
        odoo_version: str = "v16"
        odoo_db: str = ""
        odoo_username: str = ""
        odoo_token: str = ""
        gitlab_url: str = ""
        gitlab_token: str = ""
        ai_provider: str = "none"
        ai_api_key: str = ""
        ai_user_role: str = "technical"
        ai_custom_context: str = ""

    @app.get("/config")
    async def get_config() -> dict:
        """Devuelve la configuracion actual del daemon recibida desde Tauri."""
        # No devolvemos tokens por seguridad
        safe_config = {
            k: v for k, v in _app_config.items()
            if "token" not in k and "password" not in k and k != "ai_api_key"
        }
        safe_config["odoo_configured"] = bool(
            _app_config.get("odoo_url") and _app_config.get("odoo_token")
        )
        safe_config["gitlab_configured"] = bool(
            _app_config.get("gitlab_url") and _app_config.get("gitlab_token")
        )
        safe_config["ai_configured"] = bool(
            _app_config.get("ai_provider", "none") != "none"
            and _app_config.get("ai_api_key")
        )
        return safe_config

    @app.put("/config")
    async def update_config(req: AppConfigRequest) -> dict:
        """Recibe configuracion desde Tauri y configura integraciones."""
        config_data = req.model_dump()
        _app_config.update(config_data)
        logger.info("Configuracion actualizada desde Tauri")

        # Configurar integracion Odoo si hay datos suficientes
        if req.odoo_url and req.odoo_token:
            try:
                if req.odoo_version == "v11":
                    from .integrations.odoo_v11 import OdooV11Client
                    client = OdooV11Client(
                        url=req.odoo_url,
                        db=req.odoo_db,
                        username=req.odoo_username,
                        password=req.odoo_token,
                    )
                    auth_ok = await client.authenticate()
                    if auth_ok:
                        _registry.set_timesheet_client(client)
                        logger.info("Cliente Odoo v11 configurado: %s", req.odoo_url)
                    else:
                        logger.warning("Autenticacion fallida con Odoo v11")
                        return {
                            "status": "partial",
                            "odoo": "auth_failed",
                            "message": "No se pudo autenticar con Odoo v11",
                        }
                else:
                    from .integrations.odoo_v16 import OdooV16Client
                    client = OdooV16Client(
                        url=req.odoo_url,
                        db=req.odoo_db,
                        token=req.odoo_token,
                    )
                    auth_ok = await client.authenticate()
                    if auth_ok:
                        _registry.set_timesheet_client(client)
                        logger.info("Cliente Odoo v16 configurado: %s", req.odoo_url)
                    else:
                        logger.warning("Autenticacion fallida con Odoo v16")
                        return {
                            "status": "partial",
                            "odoo": "auth_failed",
                            "message": "No se pudo autenticar con Odoo v16",
                        }
            except Exception as e:
                logger.error("Error configurando Odoo: %s", e)
                return {
                    "status": "partial",
                    "odoo": "error",
                    "message": f"Error configurando Odoo: {e}",
                }

        # Configurar provider IA
        if ai_service and req.ai_provider != "none" and req.ai_api_key:
            try:
                if req.ai_provider == "gemini":
                    from .ai.gemini import GeminiProvider
                    ai_service.provider = GeminiProvider(api_key=req.ai_api_key)
                elif req.ai_provider == "claude":
                    from .ai.claude_provider import ClaudeProvider
                    ai_service.provider = ClaudeProvider(api_key=req.ai_api_key)
                elif req.ai_provider == "openai":
                    from .ai.openai_provider import OpenAIProvider
                    ai_service.provider = OpenAIProvider(api_key=req.ai_api_key)
                logger.info("Provider IA configurado: %s", req.ai_provider)
            except Exception as e:
                logger.error("Error configurando provider IA: %s", e)
        elif ai_service and req.ai_provider == "none":
            ai_service.provider = None
            logger.info("Provider IA desactivado")

        # Actualizar contexto de usuario en AIService
        if ai_service:
            ai_service.user_role = req.ai_user_role
            ai_service.user_context = req.ai_custom_context

        # Guardar configuracion en preferences cache de la DB
        try:
            safe = {k: v for k, v in config_data.items() if "token" not in k and "password" not in k}
            await db.set_preference("app_config", json.dumps(safe, ensure_ascii=False))
        except Exception as e:
            logger.error("Error guardando config en cache: %s", e)

        return {"status": "ok"}

    @app.get("/config/integration-status")
    async def get_integration_status() -> dict:
        """Devuelve el estado de las integraciones configuradas."""
        return {
            "odoo": {
                "configured": _registry.timesheet is not None,
                "client_type": type(_registry.timesheet).__name__ if _registry.timesheet else None,
            },
        }

    # --- GitLab (stubs) ---

    @app.get("/gitlab/issues")
    async def get_gitlab_issues() -> list:
        # TODO: implementar con integracion GitLab (Fase 5)
        return []

    @app.get("/gitlab/merge_requests")
    async def get_gitlab_merge_requests() -> list:
        # TODO: implementar con integracion GitLab (Fase 5)
        return []

    return app

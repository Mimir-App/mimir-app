"""Servidor HTTP local (FastAPI) para comunicacion con la app Tauri."""

# NOTA: NO usar 'from __future__ import annotations' aquí.
# Rompe la inspección de tipos de FastAPI/Pydantic para body params.

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import __version__
from .db import Database
from .integrations.base import TimesheetEntryData
from .integrations.registry import IntegrationRegistry
from .notifications import NotificationService
from .sources.registry import SourceRegistry

logger = logging.getLogger(__name__)


def _calc_duration(start_str: str, end_str: str) -> float:
    """Calcula duracion en minutos entre dos timestamps ISO."""
    try:
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        return round((end - start).total_seconds() / 60, 1)
    except (ValueError, AttributeError):
        return 0.0


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
    _registry = registry or IntegrationRegistry()
    _source_registry = source_registry or SourceRegistry()

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
            "running": True,
            "mode": "active",
            "uptime_seconds": uptime,
            "last_poll": None,
            "blocks_today": blocks_today,
            "version": version,
        }

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
        """Confirma un bloque para envio a Odoo.

        Si el bloque tiene context_key y proyecto Odoo, aprende el mapeo
        para auto-asignar bloques futuros con el mismo contexto.
        """
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        if block.get("status") == "synced":
            raise HTTPException(400, "El bloque ya fue enviado a Odoo")
        await db.update_block(block_id, status="confirmed")

        # Aprender mapeo context_key -> Odoo
        ctx = block.get("context_key")
        proj = block.get("odoo_project_id")
        if ctx and proj:
            await db.set_context_mapping(
                ctx,
                proj,
                block.get("odoo_project_name"),
                block.get("odoo_task_id"),
                block.get("odoo_task_name"),
            )
            logger.info("Mapping aprendido: %s -> %s", ctx, block.get("odoo_project_name"))

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

    # --- Signals ---

    @app.get("/signals")
    async def get_signals(date: str = Query(default=None), block_id: int = Query(default=None)) -> list[dict]:
        """Obtiene senales por fecha o por bloque."""
        if block_id:
            return await db.get_signals_by_block(block_id)
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return await db.get_signals_by_date(date)

    @app.post("/blocks/{block_id}/split")
    async def split_block(block_id: int, signal_id: int = Query(...)) -> dict:
        """Divide un bloque en dos en el punto de una senal."""
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        if block["status"] in ("confirmed", "synced"):
            raise HTTPException(400, "No se puede partir un bloque confirmado")

        signals = await db.get_signals_by_block(block_id)
        if not signals:
            raise HTTPException(400, "Bloque sin senales")

        before = [s for s in signals if s["id"] < signal_id]
        after = [s for s in signals if s["id"] >= signal_id]
        if not before or not after:
            raise HTTPException(400, "Punto de corte invalido")

        last_before = before[-1]
        await db.update_block(block_id,
            end_time=last_before["timestamp"],
            duration_minutes=_calc_duration(block["start_time"], last_before["timestamp"]),
            status="closed",
        )

        first_after = after[0]
        last_after = after[-1]
        new_id = await db.create_block(
            start_time=first_after["timestamp"],
            end_time=last_after["timestamp"],
            duration_minutes=_calc_duration(first_after["timestamp"], last_after["timestamp"]),
            app_name=first_after.get("app_name", block["app_name"]),
            window_title=first_after.get("window_title", ""),
            project_path=first_after.get("project_path"),
            git_branch=first_after.get("git_branch"),
            git_remote=first_after.get("git_remote"),
            status="closed",
        )

        for s in after:
            await db.db.execute(
                "UPDATE block_signals SET block_id = ? WHERE signal_id = ?",
                [new_id, s["id"]],
            )
        await db.db.commit()

        return {"original_block_id": block_id, "new_block_id": new_id}

    class MergeRequest(BaseModel):
        block_ids: list[int]

    @app.post("/blocks/merge")
    async def merge_blocks(req: MergeRequest) -> dict:
        """Fusiona bloques en uno."""
        if len(req.block_ids) < 2:
            raise HTTPException(400, "Se necesitan al menos 2 bloques")

        blocks = []
        for bid in req.block_ids:
            b = await db.get_block_by_id(bid)
            if not b:
                raise HTTPException(404, f"Bloque {bid} no encontrado")
            if b["status"] in ("confirmed", "synced"):
                raise HTTPException(400, f"Bloque {bid} esta confirmado, no se puede fusionar")
            blocks.append(b)

        blocks.sort(key=lambda b: b["start_time"])
        primary = blocks[0]
        last = blocks[-1]

        await db.update_block(primary["id"],
            end_time=last["end_time"],
            duration_minutes=_calc_duration(primary["start_time"], last["end_time"]),
            status="closed",
        )

        for b in blocks[1:]:
            await db.db.execute(
                "UPDATE block_signals SET block_id = ? WHERE block_id = ?",
                [primary["id"], b["id"]],
            )
            await db.delete_block(b["id"])
        await db.db.commit()

        return {"merged_block_id": primary["id"]}

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

    # --- Context Mappings ---

    @app.get("/context-mappings")
    async def get_context_mappings() -> list[dict]:
        """Obtiene todos los mapeos context_key -> Odoo."""
        return await db.get_all_context_mappings()

    @app.get("/context-mappings/suggest")
    async def suggest_context_mapping(context_key: str = Query()) -> dict:
        """Sugiere un mapeo Odoo para un context_key.

        Busca: exacto -> parcial -> historial de bloques.
        Retorna el mapeo con campo 'match' (exact|partial|history) o 404.
        """
        suggestion = await db.suggest_mapping(context_key)
        if not suggestion:
            raise HTTPException(404, "Sin sugerencia para este contexto")
        return suggestion

    class ContextMappingRequest(BaseModel):
        context_key: str
        odoo_project_id: int | None = None
        odoo_project_name: str | None = None
        odoo_task_id: int | None = None
        odoo_task_name: str | None = None

    @app.put("/context-mappings")
    async def upsert_context_mapping(req: ContextMappingRequest) -> dict:
        """Crea o actualiza un mapeo context_key -> Odoo."""
        await db.set_context_mapping(
            req.context_key,
            req.odoo_project_id, req.odoo_project_name,
            req.odoo_task_id, req.odoo_task_name,
        )
        return {"status": "saved"}

    @app.delete("/context-mappings/{context_key:path}")
    async def delete_context_mapping(context_key: str) -> dict:
        """Elimina un mapeo context_key -> Odoo."""
        await db.delete_context_mapping(context_key)
        return {"status": "deleted"}

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
        task_id: int | None = Query(default=None),
    ) -> list:
        """Obtiene entradas de timesheet de Odoo en un rango."""
        client = _registry.timesheet
        if not client:
            return []
        try:
            entries = await client.get_entries(date_from, date_to)
            if task_id is not None:
                entries = [e for e in entries if e.get("task_id") == task_id]
            return entries
        except Exception as e:
            logger.error("Error obteniendo entradas de Odoo: %s", e)
            return []

    # --- Attendance ---

    @app.get("/odoo/attendance/today")
    async def get_today_attendance() -> dict:
        """Obtiene el fichaje de hoy."""
        client = _registry.timesheet
        if not client:
            return {"attendance": None}
        try:
            att = await client.get_today_attendance()
            return {"attendance": att}
        except Exception as e:
            logger.error("Error obteniendo attendance: %s", e)
            return {"attendance": None}

    @app.post("/odoo/attendance/checkin")
    async def attendance_checkin() -> dict:
        """Fichar entrada."""
        client = _registry.timesheet
        if not client:
            raise HTTPException(503, "No hay cliente de timesheet configurado")
        try:
            att_id = await client.check_in()
            return {"id": att_id, "status": "checked_in"}
        except Exception as e:
            raise HTTPException(502, f"Error fichando entrada: {e}")

    @app.post("/odoo/attendance/{attendance_id}/checkout")
    async def attendance_checkout(attendance_id: int) -> dict:
        """Fichar salida."""
        client = _registry.timesheet
        if not client:
            raise HTTPException(503, "No hay cliente de timesheet configurado")
        try:
            await client.check_out(attendance_id)
            return {"status": "checked_out"}
        except Exception as e:
            raise HTTPException(502, f"Error fichando salida: {e}")

    # --- Google Calendar ---

    @app.get("/google/calendar/auth-url")
    async def get_google_auth_url() -> dict:
        """Devuelve la URL de autorizacion OAuth2 de Google."""
        if not calendar_client:
            raise HTTPException(400, "Google Calendar no configurado. Configura client_id y client_secret.")
        url = calendar_client.get_auth_url()
        return {"url": url}

    @app.get("/oauth/google/callback")
    async def google_oauth_callback(code: str = Query(...)) -> dict:
        """Callback OAuth2 — intercambia el codigo por tokens."""
        if not calendar_client:
            raise HTTPException(400, "Google Calendar no configurado")
        success = await calendar_client.exchange_code(code)
        if not success:
            raise HTTPException(502, "Error al autorizar con Google")
        return {"status": "authorized", "message": "Google Calendar conectado. Puedes cerrar esta ventana."}

    @app.get("/google/calendar/status")
    async def google_calendar_status() -> dict:
        """Estado de la conexion con Google Calendar."""
        if not calendar_client:
            return {"configured": False, "connected": False}
        return {
            "configured": True,
            "connected": calendar_client.is_configured,
        }

    @app.get("/google/calendar/current-event")
    async def get_current_event() -> dict:
        """Obtiene el evento actual del calendario (si hay uno)."""
        if not calendar_client or not calendar_client.is_configured:
            return {"event": None}
        event = await calendar_client.get_current_event()
        return {"event": event}

    @app.post("/google/calendar/disconnect")
    async def disconnect_google_calendar() -> dict:
        """Desconecta Google Calendar eliminando tokens."""
        if calendar_client:
            await calendar_client.disconnect()
        return {"status": "disconnected"}

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
        github_token: str = ""
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
        safe_config["github_configured"] = bool(
            _app_config.get("github_token")
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
                        timezone=config_data.get("timezone", "Europe/Madrid"),
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
                        timezone=config_data.get("timezone", "Europe/Madrid"),
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

        # Configurar GitLab source
        if req.gitlab_url and req.gitlab_token:
            try:
                from .sources.gitlab import GitLabSource
                gitlab_source = GitLabSource(url=req.gitlab_url, token=req.gitlab_token)
                _source_registry.register_vcs("gitlab", gitlab_source)
                logger.info("GitLab source configurado: %s", req.gitlab_url)
            except Exception as e:
                logger.error("Error configurando GitLab: %s", e)

        # Configurar GitHub source
        if req.github_token:
            try:
                from .sources.github import GitHubSource
                github_source = GitHubSource(token=req.github_token)
                _source_registry.register_vcs("github", github_source)
                logger.info("GitHub source configurado")
            except Exception as e:
                logger.error("Error configurando GitHub: %s", e)

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
            "gitlab": {
                "configured": "gitlab" in _source_registry._vcs_sources,
            },
            "github": {
                "configured": "github" in _source_registry._vcs_sources,
            },
        }

    # --- GitLab ---

    @app.get("/gitlab/issues")
    async def get_gitlab_issues() -> list:
        """Obtiene issues de GitLab."""
        try:
            return await _source_registry.get_all_issues()
        except Exception as e:
            logger.error("Error obteniendo issues de GitLab: %s", e)
            return []

    @app.get("/gitlab/merge_requests")
    async def get_gitlab_merge_requests() -> list:
        """Obtiene merge requests de GitLab."""
        try:
            return await _source_registry.get_all_merge_requests()
        except Exception as e:
            logger.error("Error obteniendo MRs de GitLab: %s", e)
            return []

    @app.get("/items/preferences")
    async def get_item_preferences(type: str = Query(...)) -> list:
        """Obtiene todas las preferencias de un tipo de item."""
        try:
            return await db.get_item_preferences(type)
        except Exception as e:
            logger.error("Error obteniendo preferencias de items (%s): %s", type, e)
            return []

    @app.put("/items/{item_type}/{item_id}/preferences")
    async def update_item_preferences(
        item_type: str, item_id: int, body: dict = Body(...)
    ) -> dict:
        """Crea o actualiza preferencia de un item (issue o mr)."""
        await db.upsert_item_preference(
            item_id=item_id,
            item_type=item_type,
            manual_score=body.get("manual_score"),
            followed=body.get("followed"),
            source=body.get("source"),
            project_path=body.get("project_path"),
            iid=body.get("iid"),
            title=body.get("title"),
        )
        return {"status": "updated", "item_id": item_id, "item_type": item_type}

    @app.get("/gitlab/issues/followed")
    async def get_gitlab_followed_issues() -> list:
        """Obtiene issues seguidas con datos frescos de todas las fuentes."""
        try:
            followed = await db.get_followed_items_with_meta("issue")
            if not followed:
                return []
            results = []
            # GitLab items
            gitlab_ids = [f["item_id"] for f in followed if f.get("source") != "github"]
            if gitlab_ids:
                gitlab = _source_registry._vcs_sources.get("gitlab")
                if gitlab:
                    from .sources.gitlab import GitLabSource
                    if isinstance(gitlab, GitLabSource):
                        results.extend(await gitlab.get_issues_by_ids(gitlab_ids))
            # GitHub items — buscar individualmente por owner/repo/number
            github = _source_registry._vcs_sources.get("github")
            if github:
                from .sources.github import GitHubSource
                if isinstance(github, GitHubSource):
                    for f in followed:
                        if f.get("source") != "github":
                            continue
                        pp = f.get("project_path", "")
                        iid = f.get("iid")
                        if pp and iid and "/" in pp:
                            owner, repo_name = pp.split("/", 1)
                            try:
                                # Buscar la issue via API individual
                                resp = await github._client.get(f"/repos/{owner}/{repo_name}/issues/{iid}")
                                if resp.status_code == 200:
                                    item = resp.json()
                                    from .sources.github import _normalize_issue
                                    _normalize_issue(item)
                                    results.append(item)
                            except Exception:
                                continue
            return results
        except Exception as e:
            logger.error("Error obteniendo issues seguidas: %s", e)
            return []

    @app.get("/gitlab/issues/search")
    async def search_gitlab_issues(q: str = Query(..., min_length=2)) -> list:
        """Busca issues en GitLab por texto."""
        try:
            gitlab = _source_registry._vcs_sources.get("gitlab")
            if not gitlab:
                return []
            from .sources.gitlab import GitLabSource
            if not isinstance(gitlab, GitLabSource):
                return []
            return await gitlab.search_issues(q)
        except Exception as e:
            logger.error("Error buscando issues en GitLab: %s", e)
            return []

    @app.get("/gitlab/labels")
    async def get_gitlab_labels() -> list:
        """Obtiene labels unicas de los proyectos del usuario."""
        try:
            gitlab = _source_registry._vcs_sources.get("gitlab")
            if not gitlab:
                return []
            from .sources.gitlab import GitLabSource
            if not isinstance(gitlab, GitLabSource):
                return []
            return await gitlab.get_labels()
        except Exception as e:
            logger.error("Error obteniendo labels de GitLab: %s", e)
            return []

    @app.get("/gitlab/issues/{project_id}/{issue_iid}/notes")
    async def get_gitlab_issue_notes(project_id: str, issue_iid: int) -> list:
        """Obtiene notas de usuario de una issue de GitLab."""
        try:
            gitlab = _source_registry._vcs_sources.get("gitlab")
            if not gitlab:
                return []
            from .sources.gitlab import GitLabSource
            if not isinstance(gitlab, GitLabSource):
                return []
            return await gitlab.get_issue_notes(project_id, issue_iid)
        except Exception as e:
            logger.error("Error obteniendo notas de issue %s#%d: %s", project_id, issue_iid, e)
            return []

    @app.get("/gitlab/merge_requests/search")
    async def search_gitlab_merge_requests(q: str = Query(..., min_length=2)) -> list:
        """Busca merge requests en GitLab por texto."""
        try:
            gitlab = _source_registry._vcs_sources.get("gitlab")
            if not gitlab:
                return []
            from .sources.gitlab import GitLabSource
            if not isinstance(gitlab, GitLabSource):
                return []
            return await gitlab.search_merge_requests(q)
        except Exception as e:
            logger.error("Error buscando MRs en GitLab: %s", e)
            return []

    @app.get("/gitlab/merge_requests/followed")
    async def get_gitlab_followed_merge_requests() -> list:
        """Obtiene MRs seguidas con datos frescos de todas las fuentes."""
        try:
            followed = await db.get_followed_items_with_meta("mr")
            if not followed:
                return []
            results = []
            # GitLab
            gitlab_ids = [f["item_id"] for f in followed if f.get("source") != "github"]
            if gitlab_ids:
                gitlab = _source_registry._vcs_sources.get("gitlab")
                if gitlab:
                    from .sources.gitlab import GitLabSource
                    if isinstance(gitlab, GitLabSource):
                        results.extend(await gitlab.get_merge_requests_by_ids(gitlab_ids))
            # GitHub — buscar individualmente
            github = _source_registry._vcs_sources.get("github")
            if github:
                from .sources.github import GitHubSource
                if isinstance(github, GitHubSource):
                    for f in followed:
                        if f.get("source") != "github":
                            continue
                        pp = f.get("project_path", "")
                        iid = f.get("iid")
                        if pp and iid and "/" in pp:
                            owner, repo_name = pp.split("/", 1)
                            try:
                                resp = await github._client.get(f"/repos/{owner}/{repo_name}/pulls/{iid}")
                                if resp.status_code == 200:
                                    item = resp.json()
                                    from .sources.github import _normalize_pr
                                    _normalize_pr(item)
                                    results.append(item)
                            except Exception:
                                continue
            return results
        except Exception as e:
            logger.error("Error obteniendo MRs seguidas: %s", e)
            return []

    @app.get("/gitlab/merge_requests/{project_id}/{mr_iid}/notes")
    async def get_gitlab_mr_notes(project_id: str, mr_iid: int) -> list:
        """Obtiene notas de usuario de un MR de GitLab."""
        try:
            gitlab = _source_registry._vcs_sources.get("gitlab")
            if not gitlab:
                return []
            from .sources.gitlab import GitLabSource
            if not isinstance(gitlab, GitLabSource):
                return []
            return await gitlab.get_mr_notes(project_id, mr_iid)
        except Exception as e:
            logger.error("Error obteniendo notas de MR %s!%d: %s", project_id, mr_iid, e)
            return []

    @app.get("/gitlab/merge_requests/{project_id}/{mr_iid}/conflicts")
    async def get_gitlab_mr_conflicts(project_id: str, mr_iid: int) -> list:
        """Obtiene archivos en conflicto de un MR."""
        try:
            gitlab = _source_registry._vcs_sources.get("gitlab")
            if not gitlab:
                return []
            from .sources.gitlab import GitLabSource
            if not isinstance(gitlab, GitLabSource):
                return []
            return await gitlab.get_mr_conflicts(project_id, mr_iid)
        except Exception as e:
            logger.error("Error obteniendo conflictos de MR %s!%d: %s", project_id, mr_iid, e)
            return []

    @app.get("/gitlab/todos")
    async def get_gitlab_todos() -> list:
        """Obtiene TODOs pendientes del usuario en GitLab."""
        try:
            gitlab = _source_registry._vcs_sources.get("gitlab")
            if not gitlab:
                return []
            from .sources.gitlab import GitLabSource
            if not isinstance(gitlab, GitLabSource):
                return []
            return await gitlab.get_todos()
        except Exception as e:
            logger.error("Error obteniendo TODOs de GitLab: %s", e)
            return []

    @app.get("/gitlab/user")
    async def get_gitlab_user() -> dict:
        """Obtiene info del usuario actual de GitLab."""
        try:
            gitlab = _source_registry._vcs_sources.get("gitlab")
            if not gitlab:
                return {}
            from .sources.gitlab import GitLabSource
            if not isinstance(gitlab, GitLabSource):
                return {}
            return await gitlab.get_current_user()
        except Exception as e:
            logger.error("Error obteniendo usuario de GitLab: %s", e)
            return {}

    # --- GitHub ---

    def _get_github():
        """Helper para obtener el source de GitHub."""
        gh = _source_registry._vcs_sources.get("github")
        if not gh:
            return None
        from .sources.github import GitHubSource
        return gh if isinstance(gh, GitHubSource) else None

    @app.get("/github/issues")
    async def get_github_issues() -> list:
        """Obtiene issues de GitHub."""
        try:
            gh = _get_github()
            return await gh.get_issues() if gh else []
        except Exception as e:
            logger.error("Error obteniendo issues de GitHub: %s", e)
            return []

    @app.get("/github/pull_requests")
    async def get_github_pull_requests() -> list:
        """Obtiene pull requests de GitHub."""
        try:
            gh = _get_github()
            return await gh.get_merge_requests() if gh else []
        except Exception as e:
            logger.error("Error obteniendo PRs de GitHub: %s", e)
            return []

    @app.get("/github/issues/search")
    async def search_github_issues(q: str = Query(), per_page: int = Query(default=20)) -> list:
        """Busca issues en GitHub."""
        try:
            gh = _get_github()
            return await gh.search_issues(q, per_page) if gh else []
        except Exception as e:
            logger.error("Error buscando issues en GitHub: %s", e)
            return []

    @app.get("/github/pull_requests/search")
    async def search_github_pull_requests(q: str = Query(), per_page: int = Query(default=20)) -> list:
        """Busca pull requests en GitHub."""
        try:
            gh = _get_github()
            return await gh.search_pull_requests(q, per_page) if gh else []
        except Exception as e:
            logger.error("Error buscando PRs en GitHub: %s", e)
            return []

    @app.get("/github/issues/{owner}/{repo}/{issue_number}/comments")
    async def get_github_issue_comments(owner: str, repo: str, issue_number: int) -> list:
        """Obtiene comentarios de una issue de GitHub."""
        try:
            gh = _get_github()
            return await gh.get_issue_notes(owner, repo, issue_number) if gh else []
        except Exception as e:
            logger.error("Error obteniendo comentarios de issue GitHub: %s", e)
            return []

    @app.get("/github/pull_requests/{owner}/{repo}/{pr_number}/comments")
    async def get_github_pr_comments(owner: str, repo: str, pr_number: int) -> list:
        """Obtiene comentarios de un PR de GitHub."""
        try:
            gh = _get_github()
            return await gh.get_pr_notes(owner, repo, pr_number) if gh else []
        except Exception as e:
            logger.error("Error obteniendo comentarios de PR GitHub: %s", e)
            return []

    @app.get("/github/pull_requests/{owner}/{repo}/{pr_number}/reviews")
    async def get_github_pr_reviews(owner: str, repo: str, pr_number: int) -> list:
        """Obtiene reviews de un PR de GitHub."""
        try:
            gh = _get_github()
            return await gh.get_pr_reviews(owner, repo, pr_number) if gh else []
        except Exception as e:
            logger.error("Error obteniendo reviews de PR GitHub: %s", e)
            return []

    @app.get("/github/pull_requests/{owner}/{repo}/{pr_number}/files")
    async def get_github_pr_files(owner: str, repo: str, pr_number: int) -> list:
        """Obtiene archivos cambiados de un PR de GitHub."""
        try:
            gh = _get_github()
            return await gh.get_pr_files(owner, repo, pr_number) if gh else []
        except Exception as e:
            logger.error("Error obteniendo archivos de PR GitHub: %s", e)
            return []

    @app.get("/github/notifications")
    async def get_github_notifications() -> list:
        """Obtiene notificaciones pendientes de GitHub."""
        try:
            gh = _get_github()
            return await gh.get_todos() if gh else []
        except Exception as e:
            logger.error("Error obteniendo notificaciones de GitHub: %s", e)
            return []

    @app.get("/github/user")
    async def get_github_user() -> dict:
        """Obtiene info del usuario actual de GitHub."""
        try:
            gh = _get_github()
            return await gh.get_current_user() if gh else {}
        except Exception as e:
            logger.error("Error obteniendo usuario de GitHub: %s", e)
            return {}

    # --- Notifications ---

    @app.get("/notifications")
    async def get_notifications(unread_only: bool = Query(default=True)) -> list:
        """Obtiene notificaciones."""
        try:
            return await db.get_notifications(unread_only=unread_only)
        except Exception as e:
            logger.error("Error obteniendo notificaciones: %s", e)
            return []

    @app.get("/notifications/count")
    async def get_notification_count() -> dict:
        """Obtiene el numero de notificaciones no leidas."""
        try:
            count = await db.get_notification_count()
            return {"count": count}
        except Exception as e:
            logger.error("Error obteniendo count de notificaciones: %s", e)
            return {"count": 0}

    @app.put("/notifications/{notification_id}/read")
    async def mark_notification_read(notification_id: int) -> dict:
        """Marca una notificacion como leida."""
        await db.mark_notification_read(notification_id)
        return {"status": "read", "id": notification_id}

    @app.put("/notifications/read-all")
    async def mark_all_notifications_read() -> dict:
        """Marca todas las notificaciones como leidas."""
        await db.mark_all_notifications_read()
        return {"status": "all_read"}

    # --- Odoo entry update ---

    class OdooEntryUpdateRequest(BaseModel):
        project_id: int | None = None
        task_id: int | None = None
        description: str | None = None
        hours: float | None = None
        date: str | None = None

    @app.put("/odoo/entries/{entry_id}")
    async def update_odoo_entry(entry_id: int, req: OdooEntryUpdateRequest) -> dict:
        """Actualiza una entrada de timesheet en Odoo."""
        client = _registry.timesheet
        if not client:
            raise HTTPException(503, "No hay cliente de timesheet configurado")
        try:
            entry = TimesheetEntryData(
                date=req.date or "",
                project_id=req.project_id or 0,
                task_id=req.task_id,
                description=req.description or "",
                hours=req.hours or 0.0,
            )
            await client.update_entry(entry_id, entry)
            return {"status": "updated", "entry_id": entry_id}
        except Exception as e:
            logger.error("Error actualizando entrada Odoo %d: %s", entry_id, e)
            raise HTTPException(502, f"Error actualizando entrada: {e}")

    return app

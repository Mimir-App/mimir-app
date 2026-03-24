"""Router de bloques de actividad (CRUD, split, merge, sync, confirm, IA)."""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request

from ..integrations.base import TimesheetEntryData
from ..server_models import (
    BlockUpdateRequest,
    MergeRequest,
    SyncRequest,
    calc_duration,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/blocks")
async def get_blocks(request: Request, date: str = Query(default=None)) -> list[dict]:
    db = request.app.state.db
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return await db.get_blocks_by_date(date)


@router.get("/blocks/summary")
async def get_blocks_summary(request: Request, date: str = Query(default=None)) -> dict:
    db = request.app.state.db
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return await db.get_blocks_summary(date)


@router.get("/blocks/{block_id}")
async def get_block(request: Request, block_id: int) -> dict:
    db = request.app.state.db
    block = await db.get_block_by_id(block_id)
    if not block:
        raise HTTPException(404, "Bloque no encontrado")
    return block


@router.post("/blocks/{block_id}/confirm")
async def confirm_block(request: Request, block_id: int) -> dict:
    """Confirma un bloque para envio a Odoo.

    Si el bloque tiene context_key y proyecto Odoo, aprende el mapeo
    para auto-asignar bloques futuros con el mismo contexto.
    """
    db = request.app.state.db
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


@router.put("/blocks/{block_id}")
async def update_block(request: Request, block_id: int, req: BlockUpdateRequest) -> dict:
    """Actualiza campos de un bloque.

    Si el bloque ya fue enviado a Odoo (synced), se marca como
    pending para permitir reenvio con la actualizacion.
    """
    db = request.app.state.db
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


@router.post("/blocks/sync")
async def sync_blocks(request: Request, req: SyncRequest) -> dict:
    """Sincroniza bloques confirmados con Odoo.

    Para cada bloque:
    - Si no tiene remote_id -> create_entry
    - Si ya tiene remote_id (fue editado tras sync) -> update_entry
    - sync_status: pending -> sent (con remote_id) o error (con sync_error)
    """
    db = request.app.state.db
    registry = request.app.state.registry
    client = registry.timesheet
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


@router.post("/blocks/{block_id}/retry")
async def retry_sync_block(request: Request, block_id: int) -> dict:
    """Reintenta la sincronizacion de un bloque con error."""
    db = request.app.state.db
    registry = request.app.state.registry
    block = await db.get_block_by_id(block_id)
    if not block:
        raise HTTPException(404, "Bloque no encontrado")
    if block.get("status") != "error":
        raise HTTPException(400, "Solo se pueden reintentar bloques con error")

    client = registry.timesheet
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


@router.delete("/blocks/{block_id}")
async def delete_block(request: Request, block_id: int) -> dict:
    db = request.app.state.db
    block = await db.get_block_by_id(block_id)
    if not block:
        raise HTTPException(404, "Bloque no encontrado")
    await db.delete_block(block_id)
    return {"status": "deleted"}


@router.post("/blocks/{block_id}/split")
async def split_block(request: Request, block_id: int, signal_id: int = Query(...)) -> dict:
    """Divide un bloque en dos en el punto de una senal."""
    db = request.app.state.db
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
        duration_minutes=calc_duration(block["start_time"], last_before["timestamp"]),
        status="closed",
    )

    first_after = after[0]
    last_after = after[-1]
    new_id = await db.create_block(
        start_time=first_after["timestamp"],
        end_time=last_after["timestamp"],
        duration_minutes=calc_duration(first_after["timestamp"], last_after["timestamp"]),
        app_name=first_after.get("app_name", block["app_name"]),
        window_title=first_after.get("window_title", ""),
        project_path=first_after.get("project_path"),
        git_branch=first_after.get("git_branch"),
        git_remote=first_after.get("git_remote"),
        status="closed",
    )

    await db.move_signals_to_block([s["id"] for s in after], new_id)

    return {"original_block_id": block_id, "new_block_id": new_id}


@router.post("/blocks/merge")
async def merge_blocks(request: Request, req: MergeRequest) -> dict:
    """Fusiona bloques en uno."""
    db = request.app.state.db
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
        duration_minutes=calc_duration(primary["start_time"], last["end_time"]),
        status="closed",
    )

    for b in blocks[1:]:
        await db.move_block_signals(b["id"], primary["id"])
        await db.delete_block(b["id"])

    # Registrar afinidad de contextos para aprendizaje
    context_keys = [b.get("context_key", "") for b in blocks]
    await db.record_context_affinity(context_keys)

    return {"merged_block_id": primary["id"]}


@router.post("/blocks/{block_id}/generate-description")
async def generate_description(request: Request, block_id: int) -> dict:
    """Genera o regenera descripcion IA para un bloque."""
    db = request.app.state.db
    app_config = request.app.state.app_config
    block = await db.get_block_by_id(block_id)
    if not block:
        raise HTTPException(404, "Bloque no encontrado")

    from ..ai.base import DescriptionRequest
    _ai = request.app.state.ai_service
    if not _ai:
        from ..ai.service import AIService as _AIS
        _ai = _AIS(db=db, provider=None)

    desc_request = DescriptionRequest(
        app_name=block.get("app_name", ""),
        window_title=block.get("window_title", ""),
        project_path=block.get("project_path"),
        git_branch=block.get("git_branch"),
        git_remote=block.get("git_remote"),
        duration_minutes=block.get("duration_minutes", 0),
        window_titles=json.loads(block["window_titles_json"])
        if block.get("window_titles_json") else None,
        user_role=app_config.get("ai_user_role", "technical"),
        user_context=app_config.get("ai_custom_context", ""),
    )

    result = await _ai.generate(desc_request)
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

"""Router de bloques de actividad (CRUD, split, merge, sync, confirm, IA)."""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request

from ..integrations.base import TimesheetEntryData
from ..mappings_toml import load_mappings, resolve_all
from ..server_models import (
    BlockUpdateRequest,
    GenerateBlocksRequest,
    MergeRequest,
    SyncRequest,
    calc_duration,
)

logger = logging.getLogger(__name__)


def _strip_empty(d: dict) -> dict:
    """Elimina campos con valor falsy (vacío, 0, None) de un dict."""
    return {k: v for k, v in d.items() if v}

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


async def _build_generation_data(
    db, source_registry, registry, calendar_client, date: str,
    app_config: dict | None = None,
) -> dict:
    """Recopila y compacta todos los datos necesarios para generar bloques.

    Reutilizable por generation-data y review-data endpoints.
    Incluye señales, actividad VCS, calendario, proyectos Odoo,
    tareas de proyectos relevantes, bloques existentes, context mappings,
    resolución de mapeos TOML y opcionalmente historial de navegador.
    """
    # 1. Recopilar datos base en paralelo
    signals_task = db.get_signals_by_date(date)
    blocks_task = db.get_blocks_by_date(date)
    mappings_task = db.get_all_context_mappings()

    # VCS events
    async def get_gitlab_events():
        gitlab = source_registry.get_gitlab()
        if not gitlab:
            return []
        try:
            return await gitlab.get_user_events(date)
        except Exception as e:
            logger.error("Error GitLab events: %s", e)
            return []

    async def get_github_events():
        gh = source_registry.get_github()
        if not gh:
            return []
        try:
            return await gh.get_user_events(date)
        except Exception as e:
            logger.error("Error GitHub events: %s", e)
            return []

    async def get_calendar_events():
        if not calendar_client or not calendar_client.is_configured:
            return []
        try:
            return await calendar_client.get_events_by_date(date)
        except Exception as e:
            logger.error("Error Calendar events: %s", e)
            return []

    async def get_projects():
        client = registry.timesheet if registry else None
        if not client:
            return []
        try:
            return await client.get_projects()
        except Exception as e:
            logger.error("Error Odoo projects: %s", e)
            return []

    async def get_browser_history():
        if not (app_config or {}).get("capture_browser_history", False):
            return []
        try:
            from ..browser_history import get_history_for_date
            only = (app_config or {}).get("browser_history_browsers") or None
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, get_history_for_date, date, only,
            )
        except Exception as e:
            logger.error("Error browser history: %s", e)
            return []

    (signals, blocks, mappings, gitlab_events, github_events,
     calendar_events, projects, browser_history) = (
        await asyncio.gather(
            signals_task, blocks_task, mappings_task,
            get_gitlab_events(), get_github_events(),
            get_calendar_events(), get_projects(),
            get_browser_history(),
        )
    )

    # 2. Extraer nombres de ramas de la actividad VCS
    branch_names = set()
    for event in gitlab_events:
        push_data = event.get("push_data")
        if push_data and push_data.get("ref"):
            branch_names.add(push_data["ref"])
    for event in github_events:
        if event.get("target_type") == "push":
            branch_names.add(event.get("target_title", ""))

    # Extraer prefijos de ramas (patron: <proyecto>_<tarea>)
    branch_prefixes = set()
    branch_task_hints = {}
    for branch in branch_names:
        if branch in ("master", "main", "develop"):
            continue
        match = re.search(r"([a-zA-Z][a-zA-Z0-9-]*)_(\d{2,})(?:$|[^a-zA-Z0-9])", branch)
        if match:
            prefix = match.group(1).lower()
            task_num = match.group(2)
            branch_prefixes.add(prefix)
            branch_task_hints.setdefault(prefix, []).append(task_num)
        else:
            clean = re.sub(r"^(add|feat|fix|feature|hotfix|bugfix|chore|refactor)/", "", branch)
            if clean and clean != branch:
                branch_prefixes.add(clean.split("_")[0].split("/")[0].lower())

    # Calcular nombre del mes en español para filtrar tareas mensuales
    _MESES = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
    }
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        target_month = _MESES[target_date.month]
        target_year = str(target_date.year)
    except (ValueError, KeyError):
        target_month = ""
        target_year = ""

    # --- Filtro web: si browser_history activo, excluir señales web (redundantes) ---
    if (app_config or {}).get("capture_browser_history", False):
        original_count = len(signals)
        signals = [s for s in signals if not (s.get("context_key", "").startswith("web:"))]
        if original_count != len(signals):
            logger.info(
                "Filtro web: %d -> %d señales (-%d%%)",
                original_count, len(signals),
                round(100 * (original_count - len(signals)) / max(original_count, 1)),
            )

    # --- Señales compactadas (necesarias para resolución TOML) ---
    spans: list[dict] = []
    for s in signals:
        t = s["timestamp"][11:16]  # HH:MM
        app = s.get("app_name", "")
        ctx = s.get("context_key", "")
        branch = s.get("git_branch", "")
        meet = s.get("is_meeting", 0)
        cal = s.get("calendar_event", "")
        title = (s.get("window_title") or "")[:80]

        parts = t.split(":")
        t_min = int(parts[0]) * 60 + int(parts[1])

        if spans:
            cur = spans[-1]
            cur_end_parts = cur["to"].split(":")
            cur_end_min = int(cur_end_parts[0]) * 60 + int(cur_end_parts[1])
            same_group = (
                cur.get("app") == app
                and cur.get("ctx") == ctx
                and cur.get("branch") == branch
                and cur.get("meet") == meet
                and (t_min - cur_end_min) <= 5
            )
            if same_group:
                cur["to"] = t
                cur["n"] += 1
                if title and title not in cur["_titles_set"]:
                    cur["_titles_set"].add(title)
                    cur["titles"].append(title)
                if cal and not cur.get("cal"):
                    cur["cal"] = cal
                continue

        span: dict = {
            "from": t, "to": t, "app": app, "n": 1,
            "ctx": ctx, "branch": branch, "meet": meet, "cal": cal,
            "titles": [title] if title else [],
            "_titles_set": {title} if title else set(),
        }
        spans.append(span)

    compact_signals = []
    for sp in spans:
        del sp["_titles_set"]
        sp["titles"] = sp["titles"][:5]
        compact_signals.append(_strip_empty(sp))

    # --- Segunda pasada: compactación agresiva por ctx+branch ---
    agg: dict[str, dict] = {}
    for sp in compact_signals:
        ctx = sp.get("ctx", "")
        branch = sp.get("branch", "")
        key = f"{ctx}|{branch}"

        if key not in agg:
            agg[key] = {
                "ctx": ctx, "branch": branch,
                "n": 0, "from": sp.get("from", ""), "to": sp.get("to", ""),
                "intervals": [], "apps": {},
                "titles": [], "_titles_set": set(),
                "meet": 0, "cal": "",
            }

        g = agg[key]
        g["n"] += sp.get("n", 1)
        fr, to = sp.get("from", ""), sp.get("to", "")
        g["intervals"].append((fr, to))
        if fr < g["from"]:
            g["from"] = fr
        if to > g["to"]:
            g["to"] = to

        app = sp.get("app", "")
        if app:
            g["apps"][app] = g["apps"].get(app, 0) + sp.get("n", 1)

        for t in sp.get("titles", []):
            if t not in g["_titles_set"] and len(g["titles"]) < 5:
                g["_titles_set"].add(t)
                g["titles"].append(t)

        if sp.get("meet"):
            g["meet"] = 1
        if sp.get("cal") and not g["cal"]:
            g["cal"] = sp["cal"]

    # Fusionar intervalos adyacentes y construir resultado
    compact_signals = []
    for g in sorted(agg.values(), key=lambda x: x.get("from", "")):
        intervals = sorted(g["intervals"])
        merged: list[tuple[str, str]] = []
        for start, end in intervals:
            s_min = int(start[:2]) * 60 + int(start[3:5]) if len(start) >= 5 else 0
            if merged:
                prev_end = merged[-1][1]
                pe_min = int(prev_end[:2]) * 60 + int(prev_end[3:5]) if len(prev_end) >= 5 else 0
                if s_min - pe_min <= 30:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                    continue
            merged.append((start, end))

        ranges = [f"{s}-{e}" if s != e else s for s, e in merged]

        entry: dict = {"ctx": g["ctx"], "n": g["n"], "from": g["from"], "to": g["to"], "ranges": ranges}
        if g["branch"]:
            entry["branch"] = g["branch"]
        if len(g["apps"]) > 1:
            entry["apps"] = g["apps"]
        elif g["apps"]:
            entry["app"] = next(iter(g["apps"]))
        if g["titles"]:
            entry["titles"] = g["titles"]
        if g["meet"]:
            entry["meet"] = 1
        if g["cal"]:
            entry["cal"] = g["cal"]
        compact_signals.append(_strip_empty(entry))

    logger.info("Compactación: %d señales -> %d spans -> %d grupos", len(signals), len(spans), len(compact_signals))

    # --- Calendar events: compactar ---
    compact_calendar = [
        _strip_empty({
            "name": e.get("summary", ""),
            "from": (e.get("start") or "")[11:16],
            "to": (e.get("end") or "")[11:16],
            "meet": 1 if e.get("is_meeting") else 0,
        })
        for e in calendar_events
    ]

    # --- Resolución TOML (si existe ~/.config/mimir/mappings.toml) ---
    toml_data = load_mappings()
    toml_result = None
    if toml_data:
        toml_result = resolve_all(
            toml_data, compact_signals, compact_calendar,
            mappings, branch_task_hints, target_month, target_year,
        )
        logger.info(
            "TOML mappings resueltos: %d extra_mappings, %d project_ids",
            len(toml_result.get("extra_mappings", [])),
            len(toml_result.get("matched_project_ids", set())),
        )

    # 3. Filtrar solo proyectos Odoo relevantes (no enviar los 167)
    matched_projects = []
    matched_project_ids: set[int] = set()
    for proj in projects:
        proj_name = (proj.get("name") or "").lower()
        matched = False
        for prefix in branch_prefixes:
            if prefix in proj_name:
                matched = True
                break
        if not matched:
            for m in mappings:
                if m.get("odoo_project_id") == proj["id"]:
                    matched = True
                    break
        if not matched and "temas internos" in proj_name:
            matched = True
        if matched:
            matched_projects.append(proj)
            matched_project_ids.add(proj["id"])

    # Añadir proyectos referenciados por TOML
    if toml_result:
        for pid in toml_result.get("matched_project_ids", set()):
            if pid not in matched_project_ids:
                for proj in projects:
                    if proj["id"] == pid:
                        matched_projects.append(proj)
                        matched_project_ids.add(pid)
                        break

    # Si no hay matches, enviar solo los 20 primeros como fallback
    if not matched_projects:
        matched_projects = projects[:20]
        matched_project_ids = {p["id"] for p in matched_projects}

    # 4. Obtener tareas SOLO de proyectos relevantes
    tasks_by_project: dict = {}
    odoo_client = registry.timesheet if registry else None

    if odoo_client and matched_project_ids:
        sem = asyncio.Semaphore(5)

        async def fetch_tasks(pid):
            async with sem:
                try:
                    tasks = await odoo_client.get_tasks(pid)
                    if len(tasks) > 100 and target_month:
                        monthly = [
                            t for t in tasks
                            if target_month.lower() in (t.get("name") or "").lower()
                            and target_year in (t.get("name") or "")
                        ]
                        if monthly:
                            return pid, monthly
                    return pid, tasks[:50]
                except Exception:
                    return pid, []

        results = await asyncio.gather(*[fetch_tasks(pid) for pid in matched_project_ids])
        for pid, tasks in results:
            if tasks:
                tasks_by_project[str(pid)] = tasks

    # Filtrar bloques existentes que no se deben tocar
    preserved_blocks = [b for b in blocks if b.get("status") in ("confirmed", "synced", "error")]

    logger.info(
        "Generation data para %s: %d señales, %d gitlab, %d github, %d calendar, "
        "%d proyectos (de %d), %d con tareas, %d bloques preservados, "
        "branch_hints=%s",
        date, len(signals), len(gitlab_events), len(github_events),
        len(calendar_events), len(matched_projects), len(projects),
        len(tasks_by_project), len(preserved_blocks), branch_task_hints,
    )

    # --- Compactar datos restantes ---

    compact_gitlab = [
        _strip_empty({
            "t": (e.get("created_at") or "")[11:16],
            "type": e.get("type", ""),
            "target": e.get("target_type", ""),
            "title": (e.get("target_title") or "")[:120],
            "iid": e.get("target_iid"),
            "pid": e.get("project_id"),
            "push": _strip_empty({
                "ref": e["push_data"]["ref"],
                "action": e["push_data"].get("action", ""),
                "commits": e["push_data"].get("commit_count", 0),
            }) if e.get("push_data") else None,
        })
        for e in gitlab_events
    ]

    compact_github = [
        _strip_empty({
            "t": (e.get("created_at") or "")[11:16],
            "type": e.get("target_type", e.get("type", "")),
            "title": (e.get("target_title") or "")[:120],
            "repo": e.get("repo", ""),
            "id": e.get("target_id"),
        })
        for e in github_events
    ]

    # Calendar: usar eventos enriquecidos por TOML si existen
    if toml_result and toml_result.get("enriched_calendar"):
        compact_calendar = toml_result["enriched_calendar"]

    compact_projects = [{"id": p["id"], "name": p["name"]} for p in matched_projects]

    compact_tasks = {
        pid: [{"id": t["id"], "name": t["name"]} for t in tasks]
        for pid, tasks in tasks_by_project.items()
    }

    compact_preserved = [
        _strip_empty({
            "start": b["start_time"][:16],
            "end": b["end_time"][:16],
            "project": b.get("odoo_project_name", ""),
            "task": b.get("odoo_task_name", ""),
        })
        for b in preserved_blocks
    ]

    # Context mappings: DB compactados
    compact_mappings = [
        _strip_empty({
            "ctx": m.get("context_key", ""),
            "pid": m.get("odoo_project_id"),
            "tid": m.get("odoo_task_id"),
        })
        for m in mappings
    ]

    # Mergear TOML extra_mappings (TOML overrides DB para mismo ctx)
    if toml_result:
        toml_ctx_set = {m["ctx"] for m in toml_result.get("extra_mappings", [])}
        compact_mappings = [m for m in compact_mappings if m.get("ctx") not in toml_ctx_set]
        compact_mappings.extend(toml_result["extra_mappings"])

    result = {
        "date": date,
        "signals": compact_signals,
        "gitlab_events": compact_gitlab,
        "github_events": compact_github,
        "calendar_events": compact_calendar,
        "projects": compact_projects,
        "tasks_by_project": compact_tasks,
        "preserved_blocks": compact_preserved,
        "context_mappings": compact_mappings,
        "branch_task_hints": branch_task_hints,
    }

    # Añadir defaults del TOML si existen
    if toml_result and toml_result.get("defaults"):
        result["defaults"] = toml_result["defaults"]

    if browser_history:
        # Limitar a top 5 dominios para reducir tokens del prompt
        result["browser_history"] = browser_history[:5]
        logger.info(
            "Browser history: %d dominios (de %d) para %s",
            min(5, len(browser_history)), len(browser_history), date,
        )

    return result


@router.get("/blocks/generation-data")
async def get_generation_data(request: Request, date: str = Query(...)) -> dict:
    """Recopila todos los datos necesarios para generar bloques."""
    return await _build_generation_data(
        db=request.app.state.db,
        source_registry=request.app.state.source_registry,
        registry=request.app.state.registry,
        calendar_client=getattr(request.app.state, "calendar_client", None),
        date=date,
        app_config=request.app.state.app_config,
    )


@router.get("/blocks/review-data")
async def get_review_data(request: Request, date: str = Query(...)) -> dict:
    """Devuelve generation-data + bloques actuales para el agente reviewer."""
    db = request.app.state.db

    gen_data = await _build_generation_data(
        db=db,
        source_registry=request.app.state.source_registry,
        registry=request.app.state.registry,
        calendar_client=getattr(request.app.state, "calendar_client", None),
        date=date,
        app_config=request.app.state.app_config,
    )

    blocks = await db.get_blocks_by_date(date)
    compact_blocks = [
        _strip_empty({
            "start": b["start_time"][:16],
            "end": b["end_time"][:16],
            "dur": b.get("duration_minutes", 0),
            "type": b.get("app_name", ""),
            "desc": b.get("ai_description") or b.get("user_description") or "",
            "pid": b.get("odoo_project_id"),
            "pname": b.get("odoo_project_name", ""),
            "tid": b.get("odoo_task_id"),
            "tname": b.get("odoo_task_name", ""),
            "conf": b.get("ai_confidence"),
            "ctx": b.get("context_key", ""),
            "status": b.get("status", ""),
        })
        for b in blocks
    ]

    return {
        "blocks": compact_blocks,
        "generation_data": gen_data,
    }


@router.get("/blocks/{block_id}")
async def get_block(request: Request, block_id: int) -> dict:
    db = request.app.state.db
    block = await db.get_block_by_id(block_id)
    if not block:
        raise HTTPException(404, "Bloque no encontrado")
    return block


@router.post("/blocks/generate")
async def generate_blocks(request: Request, req: GenerateBlocksRequest) -> dict:
    """Genera bloques a partir del resultado del agente Claude Code CLI.

    Estrategia incremental:
    - Bloques con status confirmed/synced/error se preservan
    - Bloques con status auto/closed se eliminan y reemplazan
    - Los nuevos bloques se crean con status 'auto'
    """
    db = request.app.state.db
    date = req.date

    # Obtener bloques existentes del día
    existing = await db.get_blocks_by_date(date)

    # Separar: los que se preservan vs los que se reemplazan
    preserved_ids = []
    replaceable_ids = []
    for block in existing:
        if block["status"] in ("confirmed", "synced", "error"):
            preserved_ids.append(block["id"])
        else:
            replaceable_ids.append(block["id"])

    # Eliminar bloques reemplazables
    for block_id in replaceable_ids:
        await db.delete_block(block_id)

    # Crear nuevos bloques
    created_ids = []
    for gen_block in req.blocks:
        sources_json = json.dumps(gen_block.sources, ensure_ascii=False) if gen_block.sources else None
        new_id = await db.create_block(
            start_time=gen_block.start_time,
            end_time=gen_block.end_time,
            duration_minutes=gen_block.duration_minutes,
            app_name=gen_block.type,
            window_title="",
            ai_description=gen_block.description,
            ai_confidence=gen_block.confidence,
            odoo_project_id=gen_block.odoo_project_id,
            odoo_project_name=gen_block.odoo_project_name,
            odoo_task_id=gen_block.odoo_task_id,
            odoo_task_name=gen_block.odoo_task_name,
            context_key=gen_block.context_key,
            status="auto",
            window_titles_json=sources_json,
        )
        created_ids.append(new_id)

    logger.info(
        "Bloques generados para %s: %d creados, %d preservados, %d reemplazados",
        date, len(created_ids), len(preserved_ids), len(replaceable_ids),
    )
    return {
        "created": len(created_ids),
        "preserved": len(preserved_ids),
        "replaced": len(replaceable_ids),
        "block_ids": created_ids,
    }


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
        # Recalcular duración si cambian los timestamps
        if "start_time" in updates or "end_time" in updates:
            st = updates.get("start_time", block["start_time"])
            et = updates.get("end_time", block["end_time"])
            updates["duration_minutes"] = calc_duration(st, et)
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

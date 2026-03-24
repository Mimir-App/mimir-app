"""Router de preferencias de items (issues, MRs) y seguimiento."""

import logging

from fastapi import APIRouter, Body, HTTPException, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/items/preferences")
async def get_item_preferences(request: Request, type: str = Query(...)) -> list:
    """Obtiene todas las preferencias de un tipo de item."""
    db = request.app.state.db
    try:
        return await db.get_item_preferences(type)
    except Exception as e:
        logger.error("Error obteniendo preferencias de items (%s): %s", type, e)
        return []


@router.put("/items/{item_type}/{item_id}/preferences")
async def update_item_preferences(
    request: Request, item_type: str, item_id: int, body: dict = Body(...)
) -> dict:
    """Crea o actualiza preferencia de un item (issue o mr)."""
    db = request.app.state.db
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


@router.get("/gitlab/issues/followed")
async def get_gitlab_followed_issues(request: Request) -> list:
    """Obtiene issues seguidas con datos frescos de todas las fuentes."""
    db = request.app.state.db
    source_registry = request.app.state.source_registry
    try:
        followed = await db.get_followed_items_with_meta("issue")
        if not followed:
            return []
        results = []
        fetched_ids: set[int] = set()
        # GitLab items
        gitlab_ids = [f["item_id"] for f in followed if f.get("source") != "github"]
        if gitlab_ids:
            gitlab = source_registry.get_gitlab()
            if gitlab:
                fresh = await gitlab.get_issues_by_ids(gitlab_ids)
                results.extend(fresh)
                fetched_ids.update(i.get("id", 0) for i in fresh)
        # GitHub items — buscar individualmente por owner/repo/number
        github = source_registry.get_github()
        if github:
            from ..sources.github import _normalize_issue
            for f in followed:
                if f.get("source") != "github":
                    continue
                pp = f.get("project_path", "")
                iid = f.get("iid")
                if pp and iid and "/" in pp:
                    owner, repo_name = pp.split("/", 1)
                    try:
                        resp = await github._client.get(f"/repos/{owner}/{repo_name}/issues/{iid}")
                        if resp.status_code == 200:
                            item = resp.json()
                            _normalize_issue(item)
                            results.append(item)
                            fetched_ids.add(item.get("id", 0))
                    except Exception:
                        continue
        # Fallback: si no se pudo obtener datos frescos, usar metadatos de la DB
        for f in followed:
            if f["item_id"] not in fetched_ids:
                results.append({
                    "id": f["item_id"],
                    "iid": f.get("iid", 0),
                    "title": f.get("title", ""),
                    "project_path": f.get("project_path", ""),
                    "_source": f.get("source", "gitlab"),
                    "_type": "issue",
                    "state": "opened",
                    "web_url": "",
                    "labels": [],
                    "assignees": [],
                    "user_notes_count": 0,
                    "created_at": "",
                    "updated_at": f.get("updated_at", ""),
                })
        return results
    except Exception as e:
        logger.error("Error obteniendo issues seguidas: %s", e)
        return []


@router.get("/gitlab/merge_requests/followed")
async def get_gitlab_followed_merge_requests(request: Request) -> list:
    """Obtiene MRs seguidas con datos frescos de todas las fuentes."""
    db = request.app.state.db
    source_registry = request.app.state.source_registry
    try:
        followed = await db.get_followed_items_with_meta("mr")
        if not followed:
            return []
        results = []
        # GitLab
        gitlab_ids = [f["item_id"] for f in followed if f.get("source") != "github"]
        if gitlab_ids:
            gitlab = source_registry.get_gitlab()
            if gitlab:
                results.extend(await gitlab.get_merge_requests_by_ids(gitlab_ids))
        # GitHub — buscar individualmente
        github = source_registry.get_github()
        if github:
            from ..sources.github import _normalize_pr
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
                            _normalize_pr(item)
                            results.append(item)
                    except Exception:
                        continue
        return results
    except Exception as e:
        logger.error("Error obteniendo MRs seguidas: %s", e)
        return []

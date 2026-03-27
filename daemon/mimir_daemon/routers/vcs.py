"""Router de integraciones VCS (GitLab y GitHub) — excepto OAuth."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter()


# --- GitLab ---

@router.get("/gitlab/issues")
async def get_gitlab_issues(request: Request) -> list:
    """Obtiene issues de GitLab."""
    source_registry = request.app.state.source_registry
    try:
        return await source_registry.get_all_issues()
    except Exception as e:
        logger.error("Error obteniendo issues de GitLab: %s", e)
        return []


@router.get("/gitlab/merge_requests")
async def get_gitlab_merge_requests(request: Request) -> list:
    """Obtiene merge requests de GitLab."""
    source_registry = request.app.state.source_registry
    try:
        return await source_registry.get_all_merge_requests()
    except Exception as e:
        logger.error("Error obteniendo MRs de GitLab: %s", e)
        return []


@router.get("/gitlab/issues/search")
async def search_gitlab_issues(request: Request, q: str = Query(..., min_length=2)) -> list:
    """Busca issues en GitLab por texto."""
    source_registry = request.app.state.source_registry
    try:
        gitlab = source_registry.get_gitlab()
        if not gitlab:
            return []
        return await gitlab.search_issues(q)
    except Exception as e:
        logger.error("Error buscando issues en GitLab: %s", e)
        return []


@router.get("/gitlab/labels")
async def get_gitlab_labels(request: Request) -> list:
    """Obtiene labels unicas de los proyectos del usuario."""
    source_registry = request.app.state.source_registry
    try:
        gitlab = source_registry.get_gitlab()
        if not gitlab:
            return []
        return await gitlab.get_labels()
    except Exception as e:
        logger.error("Error obteniendo labels de GitLab: %s", e)
        return []


@router.get("/gitlab/issues/{project_id}/{issue_iid}/notes")
async def get_gitlab_issue_notes(request: Request, project_id: str, issue_iid: int) -> list:
    """Obtiene notas de usuario de una issue de GitLab."""
    source_registry = request.app.state.source_registry
    try:
        gitlab = source_registry.get_gitlab()
        if not gitlab:
            return []
        return await gitlab.get_issue_notes(project_id, issue_iid)
    except Exception as e:
        logger.error("Error obteniendo notas de issue %s#%d: %s", project_id, issue_iid, e)
        return []


@router.get("/gitlab/merge_requests/search")
async def search_gitlab_merge_requests(request: Request, q: str = Query(..., min_length=2)) -> list:
    """Busca merge requests en GitLab por texto."""
    source_registry = request.app.state.source_registry
    try:
        gitlab = source_registry.get_gitlab()
        if not gitlab:
            return []
        return await gitlab.search_merge_requests(q)
    except Exception as e:
        logger.error("Error buscando MRs en GitLab: %s", e)
        return []


@router.get("/gitlab/merge_requests/{project_id}/{mr_iid}/notes")
async def get_gitlab_mr_notes(request: Request, project_id: str, mr_iid: int) -> list:
    """Obtiene notas de usuario de un MR de GitLab."""
    source_registry = request.app.state.source_registry
    try:
        gitlab = source_registry.get_gitlab()
        if not gitlab:
            return []
        return await gitlab.get_mr_notes(project_id, mr_iid)
    except Exception as e:
        logger.error("Error obteniendo notas de MR %s!%d: %s", project_id, mr_iid, e)
        return []


@router.get("/gitlab/merge_requests/{project_id}/{mr_iid}/conflicts")
async def get_gitlab_mr_conflicts(request: Request, project_id: str, mr_iid: int) -> list:
    """Obtiene archivos en conflicto de un MR."""
    source_registry = request.app.state.source_registry
    try:
        gitlab = source_registry.get_gitlab()
        if not gitlab:
            return []
        return await gitlab.get_mr_conflicts(project_id, mr_iid)
    except Exception as e:
        logger.error("Error obteniendo conflictos de MR %s!%d: %s", project_id, mr_iid, e)
        return []


@router.get("/gitlab/todos")
async def get_gitlab_todos(request: Request) -> list:
    """Obtiene TODOs pendientes del usuario en GitLab."""
    source_registry = request.app.state.source_registry
    try:
        gitlab = source_registry.get_gitlab()
        if not gitlab:
            return []
        return await gitlab.get_todos()
    except Exception as e:
        logger.error("Error obteniendo TODOs de GitLab: %s", e)
        return []


@router.get("/gitlab/user/events")
async def get_gitlab_user_events(request: Request, date: str = Query(default=None)) -> list:
    """Obtiene actividad del usuario en GitLab para una fecha."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    source_registry = request.app.state.source_registry
    try:
        gitlab = source_registry.get_gitlab()
        if not gitlab:
            return []
        return await gitlab.get_user_events(date)
    except Exception as e:
        logger.error("Error obteniendo eventos de usuario GitLab: %s", e)
        return []


@router.get("/gitlab/user")
async def get_gitlab_user(request: Request) -> dict:
    """Obtiene info del usuario actual de GitLab."""
    source_registry = request.app.state.source_registry
    try:
        gitlab = source_registry.get_gitlab()
        if not gitlab:
            return {}
        return await gitlab.get_current_user()
    except Exception as e:
        logger.error("Error obteniendo usuario de GitLab: %s", e)
        return {}


# --- GitHub ---

@router.get("/github/issues")
async def get_github_issues(request: Request) -> list:
    """Obtiene issues de GitHub."""
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.get_issues() if gh else []
    except Exception as e:
        logger.error("Error obteniendo issues de GitHub: %s", e)
        return []


@router.get("/github/pull_requests")
async def get_github_pull_requests(request: Request) -> list:
    """Obtiene pull requests de GitHub."""
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.get_merge_requests() if gh else []
    except Exception as e:
        logger.error("Error obteniendo PRs de GitHub: %s", e)
        return []


@router.get("/github/issues/search")
async def search_github_issues(request: Request, q: str = Query(), per_page: int = Query(default=20)) -> list:
    """Busca issues en GitHub."""
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.search_issues(q, per_page) if gh else []
    except Exception as e:
        logger.error("Error buscando issues en GitHub: %s", e)
        return []


@router.get("/github/pull_requests/search")
async def search_github_pull_requests(request: Request, q: str = Query(), per_page: int = Query(default=20)) -> list:
    """Busca pull requests en GitHub."""
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.search_pull_requests(q, per_page) if gh else []
    except Exception as e:
        logger.error("Error buscando PRs en GitHub: %s", e)
        return []


@router.get("/github/issues/{owner}/{repo}/{issue_number}/comments")
async def get_github_issue_comments(request: Request, owner: str, repo: str, issue_number: int) -> list:
    """Obtiene comentarios de una issue de GitHub."""
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.get_issue_notes(owner, repo, issue_number) if gh else []
    except Exception as e:
        logger.error("Error obteniendo comentarios de issue GitHub: %s", e)
        return []


@router.get("/github/pull_requests/{owner}/{repo}/{pr_number}/comments")
async def get_github_pr_comments(request: Request, owner: str, repo: str, pr_number: int) -> list:
    """Obtiene comentarios de un PR de GitHub."""
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.get_pr_notes(owner, repo, pr_number) if gh else []
    except Exception as e:
        logger.error("Error obteniendo comentarios de PR GitHub: %s", e)
        return []


@router.get("/github/pull_requests/{owner}/{repo}/{pr_number}/reviews")
async def get_github_pr_reviews(request: Request, owner: str, repo: str, pr_number: int) -> list:
    """Obtiene reviews de un PR de GitHub."""
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.get_pr_reviews(owner, repo, pr_number) if gh else []
    except Exception as e:
        logger.error("Error obteniendo reviews de PR GitHub: %s", e)
        return []


@router.get("/github/pull_requests/{owner}/{repo}/{pr_number}/files")
async def get_github_pr_files(request: Request, owner: str, repo: str, pr_number: int) -> list:
    """Obtiene archivos cambiados de un PR de GitHub."""
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.get_pr_files(owner, repo, pr_number) if gh else []
    except Exception as e:
        logger.error("Error obteniendo archivos de PR GitHub: %s", e)
        return []


@router.get("/github/notifications")
async def get_github_notifications(request: Request) -> list:
    """Obtiene notificaciones pendientes de GitHub."""
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.get_todos() if gh else []
    except Exception as e:
        logger.error("Error obteniendo notificaciones de GitHub: %s", e)
        return []


@router.get("/github/user/events")
async def get_github_user_events(request: Request, date: str = Query(default=None)) -> list:
    """Obtiene actividad del usuario en GitHub para una fecha."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.get_user_events(date) if gh else []
    except Exception as e:
        logger.error("Error obteniendo eventos de usuario GitHub: %s", e)
        return []


@router.get("/github/user")
async def get_github_user(request: Request) -> dict:
    """Obtiene info del usuario actual de GitHub."""
    source_registry = request.app.state.source_registry
    try:
        gh = source_registry.get_github()
        return await gh.get_current_user() if gh else {}
    except Exception as e:
        logger.error("Error obteniendo usuario de GitHub: %s", e)
        return {}

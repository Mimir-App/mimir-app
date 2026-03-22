"""Fuente de datos GitHub."""

import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from .base import VCSSource

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"


def _project_path_from_repo_url(repository_url: str) -> str:
    """Extrae 'owner/repo' a partir de la URL de repositorio de la API de GitHub.

    La API devuelve URLs del tipo https://api.github.com/repos/owner/repo.
    """
    try:
        path = urlparse(repository_url).path  # /repos/owner/repo
        parts = [p for p in path.split("/") if p]
        # parts: ["repos", "owner", "repo"]
        if len(parts) >= 3 and parts[0] == "repos":
            return f"{parts[1]}/{parts[2]}"
        # Fallback: últimos dos segmentos
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
    except Exception:
        pass
    return ""


def _normalize_author(user: dict | None) -> dict:
    """Normaliza un objeto de usuario de GitHub al formato compartido."""
    if not user:
        return {}
    return {
        "name": user.get("name") or user.get("login", ""),
        "username": user.get("login", ""),
        "avatar_url": user.get("avatar_url", ""),
    }


def _normalize_note(comment: dict) -> dict:
    """Normaliza un comentario de GitHub al formato de nota compartido."""
    return {
        "id": comment.get("id"),
        "body": comment.get("body", ""),
        "author": _normalize_author(comment.get("user")),
        "created_at": comment.get("created_at", ""),
        "updated_at": comment.get("updated_at", ""),
        "web_url": comment.get("html_url", ""),
    }


def _normalize_issue(item: dict) -> None:
    """Normaliza una issue de GitHub para que tenga los mismos campos que GitLab."""
    item["_type"] = "issue"
    item["_source"] = "github"
    item["iid"] = item.get("number")
    item["web_url"] = item.get("html_url", "")
    item["project_path"] = _project_path_from_repo_url(item.get("repository_url", ""))
    item["author"] = _normalize_author(item.get("user"))
    item["user_notes_count"] = item.get("comments", 0)
    item["due_date"] = None
    item["has_conflicts"] = False
    item["manual_priority"] = None
    item["description"] = item.get("body") or ""
    # Milestone: GitHub devuelve objeto, normalizar a string
    ms = item.get("milestone")
    item["milestone"] = ms.get("title") if isinstance(ms, dict) else ms
    # Labels: mantener nombres + guardar objetos con color
    raw_labels = item.get("labels", [])
    item["label_objects"] = [
        {"name": l["name"], "color": f"#{l.get('color', '')}" if l.get("color") else ""}
        for l in raw_labels if isinstance(l, dict)
    ]
    item["labels"] = [l["name"] if isinstance(l, dict) else l for l in raw_labels]
    # Assignees: normalizar username
    for a in item.get("assignees", []):
        if "username" not in a:
            a["username"] = a.get("login", "")


def _normalize_pr(item: dict) -> None:
    """Normaliza un pull request de GitHub para que tenga los mismos campos que un MR de GitLab."""
    item["_type"] = "merge_request"
    item["_source"] = "github"
    item["iid"] = item.get("number")
    item["web_url"] = (
        item.get("pull_request", {}).get("html_url")
        or item.get("html_url", "")
    )
    item["project_path"] = _project_path_from_repo_url(item.get("repository_url", ""))
    item["author"] = _normalize_author(item.get("user"))
    item["user_notes_count"] = item.get("comments", 0)
    item["has_conflicts"] = False
    item["pipeline_status"] = None
    item["source_branch"] = ""
    item["target_branch"] = ""
    item["reviewers"] = []
    item["manual_priority"] = None
    item["description"] = item.get("body") or ""
    # Milestone
    ms = item.get("milestone")
    item["milestone"] = ms.get("title") if isinstance(ms, dict) else ms
    # Labels
    raw_labels = item.get("labels", [])
    item["label_objects"] = [
        {"name": l["name"], "color": f"#{l.get('color', '')}" if l.get("color") else ""}
        for l in raw_labels if isinstance(l, dict)
    ]
    item["labels"] = [l["name"] if isinstance(l, dict) else l for l in raw_labels]
    # Assignees
    for a in item.get("assignees", []):
        if "username" not in a:
            a["username"] = a.get("login", "")


class GitHubSource(VCSSource):
    """Fuente de datos de la API REST de GitHub (v2022-11-28)."""

    def __init__(self, token: str) -> None:
        """Inicializa el cliente HTTP con autenticación Bearer de GitHub.

        Args:
            token: Personal Access Token (PAT) o token OAuth de GitHub.
        """
        self._client = httpx.AsyncClient(
            base_url=_GITHUB_API,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        )

    # ------------------------------------------------------------------
    # Métodos de la interfaz VCSSource
    # ------------------------------------------------------------------

    async def get_issues(self) -> list[dict[str, Any]]:
        """Obtiene issues asignadas al usuario autenticado.

        Pagina hasta 5 páginas de 100 elementos. Normaliza la respuesta
        añadiendo los campos '_type', '_source' y 'project_path'.
        """
        issues: list[dict[str, Any]] = []
        try:
            page = 1
            while page <= 5:
                resp = await self._client.get(
                    "/issues",
                    params={
                        "filter": "assigned",
                        "state": "open",
                        "per_page": 100,
                        "page": page,
                    },
                )
                resp.raise_for_status()
                data: list[dict[str, Any]] = resp.json()
                if not data:
                    break
                for item in data:
                    if "pull_request" in item:
                        continue
                    _normalize_issue(item)
                    issues.append(item)
                page += 1
        except Exception as e:
            logger.error("Error obteniendo issues de GitHub: %s", e)
        logger.info("GitHub: %d issues obtenidas", len(issues))
        return issues

    async def get_merge_requests(self) -> list[dict[str, Any]]:
        """Obtiene pull requests asignadas al usuario y pendientes de revisión.

        Realiza dos búsquedas en la API de búsqueda de GitHub:
        - PRs asignadas: is:pr is:open assignee:@me
        - PRs para revisar: is:pr is:open review-requested:@me

        Pagina hasta 5 páginas por búsqueda y deduplica por ID.
        """
        queries = [
            "is:pr is:open assignee:@me",
            "is:pr is:open review-requested:@me",
        ]
        all_prs: list[dict[str, Any]] = []

        for query in queries:
            page = 1
            while page <= 5:
                try:
                    resp = await self._client.get(
                        "/search/issues",
                        params={
                            "q": query,
                            "per_page": 100,
                            "page": page,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    items: list[dict[str, Any]] = data.get("items", [])
                    if not items:
                        break
                    for item in items:
                        _normalize_pr(item)
                    all_prs.extend(items)
                    page += 1
                except Exception as e:
                    logger.error(
                        "Error obteniendo pull requests de GitHub (query=%r): %s",
                        query,
                        e,
                    )
                    break

        # Deduplicar por ID
        seen: set[int] = set()
        unique: list[dict[str, Any]] = []
        for pr in all_prs:
            pr_id = pr.get("id")
            if pr_id not in seen:
                seen.add(pr_id)
                unique.append(pr)

        logger.info("GitHub: %d pull requests obtenidas", len(unique))
        return unique

    # ------------------------------------------------------------------
    # Métodos adicionales
    # ------------------------------------------------------------------

    async def search_issues(
        self, query: str, per_page: int = 20
    ) -> list[dict[str, Any]]:
        """Busca issues en GitHub usando la API de búsqueda.

        Args:
            query: Texto de búsqueda libre.
            per_page: Número máximo de resultados a devolver.

        Returns:
            Lista de issues normalizadas.
        """
        try:
            resp = await self._client.get(
                "/search/issues",
                params={
                    "q": f"{query} is:issue is:open",
                    "per_page": per_page,
                },
            )
            resp.raise_for_status()
            items: list[dict[str, Any]] = resp.json().get("items", [])
            for item in items:
                _normalize_issue(item)
            return items
        except Exception as e:
            logger.error("Error buscando issues en GitHub: %s", e)
            return []

    async def get_issue_notes(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        per_page: int = 5,
    ) -> list[dict[str, Any]]:
        """Obtiene comentarios de una issue de GitHub.

        Args:
            owner: Propietario del repositorio.
            repo: Nombre del repositorio.
            issue_number: Número de la issue.
            per_page: Máximo de comentarios a devolver.

        Returns:
            Lista de comentarios normalizados con campos 'body', 'author' y 'created_at'.
        """
        try:
            resp = await self._client.get(
                f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                params={"per_page": per_page},
            )
            resp.raise_for_status()
            comments: list[dict[str, Any]] = resp.json()
            return [_normalize_note(c) for c in comments]
        except Exception as e:
            logger.error(
                "Error obteniendo notas de issue %s/%s#%d: %s",
                owner,
                repo,
                issue_number,
                e,
            )
            return []

    async def search_pull_requests(
        self, query: str, per_page: int = 20
    ) -> list[dict[str, Any]]:
        """Busca pull requests en GitHub usando la API de búsqueda.

        Args:
            query: Texto de búsqueda libre.
            per_page: Número máximo de resultados a devolver.

        Returns:
            Lista de pull requests normalizadas.
        """
        try:
            resp = await self._client.get(
                "/search/issues",
                params={
                    "q": f"{query} is:pr is:open",
                    "per_page": per_page,
                },
            )
            resp.raise_for_status()
            items: list[dict[str, Any]] = resp.json().get("items", [])
            for item in items:
                _normalize_pr(item)
            return items
        except Exception as e:
            logger.error("Error buscando pull requests en GitHub: %s", e)
            return []

    async def get_pr_notes(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        per_page: int = 5,
    ) -> list[dict[str, Any]]:
        """Obtiene comentarios de un pull request de GitHub.

        GitHub usa el mismo endpoint de comentarios de issues para PRs.

        Args:
            owner: Propietario del repositorio.
            repo: Nombre del repositorio.
            pr_number: Número del pull request.
            per_page: Máximo de comentarios a devolver.

        Returns:
            Lista de comentarios normalizados con campos 'body', 'author' y 'created_at'.
        """
        try:
            resp = await self._client.get(
                f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
                params={"per_page": per_page},
            )
            resp.raise_for_status()
            comments: list[dict[str, Any]] = resp.json()
            return [_normalize_note(c) for c in comments]
        except Exception as e:
            logger.error(
                "Error obteniendo notas de PR %s/%s#%d: %s",
                owner,
                repo,
                pr_number,
                e,
            )
            return []

    async def get_pr_reviews(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict[str, Any]]:
        """Obtiene las revisiones de un pull request de GitHub.

        Args:
            owner: Propietario del repositorio.
            repo: Nombre del repositorio.
            pr_number: Número del pull request.

        Returns:
            Lista de revisiones, cada una con 'state', 'body', 'author' y 'submitted_at'.
        """
        try:
            resp = await self._client.get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            )
            resp.raise_for_status()
            reviews: list[dict[str, Any]] = resp.json()
            normalized = []
            for review in reviews:
                normalized.append({
                    "id": review.get("id"),
                    "state": review.get("state", ""),
                    "body": review.get("body", ""),
                    "author": _normalize_author(review.get("user")),
                    "submitted_at": review.get("submitted_at", ""),
                    "web_url": review.get("html_url", ""),
                })
            return normalized
        except Exception as e:
            logger.error(
                "Error obteniendo revisiones de PR %s/%s#%d: %s",
                owner,
                repo,
                pr_number,
                e,
            )
            return []

    async def get_pr_files(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict[str, Any]]:
        """Obtiene los archivos modificados en un pull request de GitHub.

        Args:
            owner: Propietario del repositorio.
            repo: Nombre del repositorio.
            pr_number: Número del pull request.

        Returns:
            Lista de archivos modificados con campos 'filename', 'status',
            'additions', 'deletions' y 'changes'.
        """
        try:
            resp = await self._client.get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
            )
            resp.raise_for_status()
            files: list[dict[str, Any]] = resp.json()
            return [
                {
                    "filename": f.get("filename", ""),
                    "status": f.get("status", ""),
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                    "changes": f.get("changes", 0),
                    "blob_url": f.get("blob_url", ""),
                    "raw_url": f.get("raw_url", ""),
                }
                for f in files
            ]
        except Exception as e:
            logger.error(
                "Error obteniendo archivos de PR %s/%s#%d: %s",
                owner,
                repo,
                pr_number,
                e,
            )
            return []

    async def get_todos(self) -> list[dict[str, Any]]:
        """Obtiene notificaciones no leídas del usuario de GitHub.

        Mapea las notificaciones al formato de TODOs de GitLab:
        'id', 'action_name', 'target_type', 'target_url', 'body',
        'project_path' y 'created_at'.

        Returns:
            Lista de notificaciones normalizadas como TODOs.
        """
        try:
            resp = await self._client.get(
                "/notifications",
                params={"all": "false"},
            )
            resp.raise_for_status()
            notifications: list[dict[str, Any]] = resp.json()
            todos = []
            for notif in notifications:
                subject = notif.get("subject", {})
                repo = notif.get("repository", {})
                owner_info = repo.get("owner", {})
                owner_login = owner_info.get("login", "")
                repo_name = repo.get("name", "")
                project_path = f"{owner_login}/{repo_name}" if owner_login and repo_name else ""

                # Construir URL navegable a partir del subject_url de la API
                subject_url = subject.get("url", "")
                web_url = ""
                if subject_url:
                    # https://api.github.com/repos/owner/repo/issues/1
                    # -> https://github.com/owner/repo/issues/1
                    web_url = subject_url.replace(
                        "https://api.github.com/repos/", "https://github.com/"
                    )

                todos.append({
                    "id": notif.get("id"),
                    "action_name": notif.get("reason", "mentioned"),
                    "target_type": subject.get("type", ""),
                    "target_url": web_url,
                    "body": subject.get("title", ""),
                    "project_path": project_path,
                    "created_at": notif.get("updated_at", ""),
                    "_source": "github",
                })
            return todos
        except Exception as e:
            logger.error("Error obteniendo notificaciones de GitHub: %s", e)
            return []

    async def get_current_user(self) -> dict[str, Any]:
        """Obtiene información del usuario autenticado en GitHub.

        Returns:
            Datos del usuario (login, name, avatar_url, email, etc.) o dict vacío.
        """
        try:
            resp = await self._client.get("/user")
            resp.raise_for_status()
            user = resp.json()
            # Normalizar al mismo formato que GitLab
            user["username"] = user.get("login", "")
            user["avatar_url"] = user.get("avatar_url", "")
            user["web_url"] = user.get("html_url", "")
            return user
        except Exception as e:
            logger.error("Error obteniendo usuario actual de GitHub: %s", e)
            return {}

    async def get_labels(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Obtiene las etiquetas de un repositorio de GitHub.

        Args:
            owner: Propietario del repositorio.
            repo: Nombre del repositorio.

        Returns:
            Lista de etiquetas con campos 'name' y 'color'.
        """
        try:
            resp = await self._client.get(
                f"/repos/{owner}/{repo}/labels",
                params={"per_page": 100},
            )
            resp.raise_for_status()
            labels: list[dict[str, Any]] = resp.json()
            return [
                {
                    "name": lbl.get("name", ""),
                    "color": f"#{lbl.get('color', '')}" if lbl.get("color") else "",
                    "description": lbl.get("description", ""),
                }
                for lbl in labels
            ]
        except Exception as e:
            logger.error(
                "Error obteniendo labels de %s/%s en GitHub: %s", owner, repo, e
            )
            return []

    async def close(self) -> None:
        """Cierra el cliente HTTP subyacente."""
        await self._client.aclose()
